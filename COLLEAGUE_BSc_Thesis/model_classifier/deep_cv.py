#!/usr/bin/env python3
"""
Deep CV trainer for angle/distance from 8-ch audio CSVs.

Three architectures:
- resnet2d: log-Mel + IPD/ILD, ResNet18-like backbone, multi-task heads.
- crnn: shallow Conv2D front-end + BiGRU over time, multi-task heads.
- conv1d_sep: depthwise-separable 1D conv on waveform (optionally downsampled).

Runs stratified 9-fold CV (configurable via CLASSIFIER_FOLDS) and writes a
results_<timestamp>.txt with metrics for every config and the best picks.
"""

from __future__ import annotations

import math
import os
import sys
import time
import contextlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import confusion_matrix

try:
    import librosa
except Exception as exc:  # pragma: no cover - runtime guard
    raise RuntimeError("librosa is required for Mel/IPD features: pip install librosa") from exc

# Local imports (support module and script execution)
if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parent.parent))
    from model_classifier.discretization import (  # type: ignore
        ANGLE_LABELS,
        get_distance_labels,
        angle_deg_to_class,
        dist_to_class,
    )
else:
    from model_classifier.discretization import (
        ANGLE_LABELS,
        get_distance_labels,
        angle_deg_to_class,
        dist_to_class,
    )

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
AUDIO_DIR = BASE_DIR / "Data/csv/audio_loopback_csv"
LABEL_DIR = BASE_DIR / "Data/csv/labels_csv"
OVERRIDE_AUDIO = os.environ.get("CLASSIFIER_AUDIO_FILE")
OVERRIDE_LABEL = os.environ.get("CLASSIFIER_LABEL_FILE")
CHECKPOINT_DIR = BASE_DIR / "model_classifier" / "checkpoints"

# Constants / env
AUDIO_SR = 96_000
NUM_CHANNELS = 8
DESIRED_FOLDS = int(os.environ.get("CLASSIFIER_FOLDS", "9"))
DIST_NUM_BINS = int(os.environ.get("CLASSIFIER_DIST_BINS", "3"))
MAX_FILES_ENV = os.environ.get("CLASSIFIER_MAX_FILES")
MAX_FILES = int(MAX_FILES_ENV) if MAX_FILES_ENV and MAX_FILES_ENV.isdigit() else None
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
REQUIRE_CUDA = os.environ.get("CLASSIFIER_REQUIRE_CUDA", "0") == "1"
DIST_LOSS_SCALE = float(os.environ.get("CLASSIFIER_DIST_LOSS_SCALE", "1.3"))
DIST_THRESHOLDS_ENV = os.environ.get("CLASSIFIER_DIST_THRESHOLDS")  # comma-separated absolute thresholds
DIST_QUANTILES_ENV = os.environ.get("CLASSIFIER_DIST_QUANTILES")    # comma-separated quantiles (0-1) for thresholds
DEFAULT_DIST_QUANTILES = (0.3, 0.7)  # 30/70 fallback when no env is provided
MICRO_ANGLE_CLASSES = 12  # 30° bins
MICRO_DIST_CLASSES = 9    # finer-grained distance bins for confusion
SEED = int(os.environ.get("CLASSIFIER_SEED", "42"))
PENALTY_SCALE = float(os.environ.get("CLASSIFIER_ANGLE_PENALTY", "0.5"))
LOAD_WORKERS_ENV = os.environ.get("CLASSIFIER_LOAD_WORKERS")
LOAD_WORKERS = int(LOAD_WORKERS_ENV) if LOAD_WORKERS_ENV and LOAD_WORKERS_ENV.isdigit() else (os.cpu_count() or 4)


def set_seed(seed: int) -> None:
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def configure_runtime():
    threads = os.cpu_count() or 1
    torch.set_num_threads(threads)
    try:
        torch.set_num_interop_threads(threads)
    except Exception:
        pass
    if torch.cuda.is_available():
        torch.backends.cudnn.benchmark = True
        try:
            gpu_name = torch.cuda.get_device_name(0)
        except Exception:
            gpu_name = "unknown"
        print(f"[INFO] Runtime configured: threads={threads}, device={DEVICE}, gpu={gpu_name}, cudnn_benchmark={torch.backends.cudnn.benchmark}")
    else:
        print(f"[INFO] Runtime configured: threads={threads}, device={DEVICE}, cudnn_benchmark=False")


def make_grad_scaler(use_amp: bool):
    # Prefer torch.amp.GradScaler if available; fall back to torch.cuda.amp for older versions.
    if not use_amp or DEVICE.type != "cuda":
        return torch.cuda.amp.GradScaler(enabled=False)
    try:
        return torch.amp.GradScaler("cuda")
    except Exception:
        return torch.cuda.amp.GradScaler(enabled=True)


def autocast_ctx(use_amp: bool):
    if not use_amp or DEVICE.type != "cuda":
        return contextlib.nullcontext()
    try:
        return torch.amp.autocast("cuda")
    except Exception:
        return torch.cuda.amp.autocast()


def get_audio_uuid(path: Path) -> str:
    name = path.stem
    prefix = "audio_event_"
    if not name.startswith(prefix):
        raise ValueError(f"Audio filename {path.name} does not start with '{prefix}'")
    return name[len(prefix) :]


def angle_penalty_matrix(num_classes: int) -> torch.Tensor:
    """
    Build a penalty matrix based on angular distance between classes.
    Class order is n, w, s, e (angle centers: 0, 270, 180, 90 deg).
    Penalty grows linearly with angular distance and is scaled by PENALTY_SCALE.
    """
    centers = np.array([0.0, 270.0, 180.0, 90.0], dtype=np.float32)
    centers = centers[:num_classes]
    mat = np.zeros((num_classes, num_classes), dtype=np.float32)
    for i, ci in enumerate(centers):
        for j, cj in enumerate(centers):
            diff = abs((ci - cj + 180.0) % 360.0 - 180.0)
            mat[i, j] = 1.0 + PENALTY_SCALE * (diff / 180.0)
    return torch.from_numpy(mat)


def micro_angle_labels() -> List[str]:
    step = 360 // MICRO_ANGLE_CLASSES
    return [f"{i*step}-{(i+1)*step}" for i in range(MICRO_ANGLE_CLASSES)]


def micro_dist_labels() -> List[str]:
    return [f"d{i}" for i in range(MICRO_DIST_CLASSES)]


def parse_thresholds(env_val: str, expected: int, kind: str) -> Tuple[float, ...]:
    parts = [p.strip() for p in env_val.split(",") if p.strip()]
    vals = tuple(float(p) for p in parts)
    if len(vals) != expected:
        raise ValueError(f"{kind} expects {expected} values (got {len(vals)})")
    return vals


def load_pairs() -> List[Tuple[Path, Path]]:
    # Explicit override: use provided audio/label paths (can be absolute or relative to repo)
    if OVERRIDE_AUDIO and OVERRIDE_LABEL:
        a_path = Path(OVERRIDE_AUDIO)
        l_path = Path(OVERRIDE_LABEL)
        if not a_path.is_absolute():
            a_path = BASE_DIR / a_path
        if not l_path.is_absolute():
            l_path = BASE_DIR / l_path
        if not a_path.exists():
            raise RuntimeError(f"Override audio file not found: {a_path}")
        if not l_path.exists():
            raise RuntimeError(f"Override label file not found: {l_path}")
        print(f"[INFO] Using override files: audio={a_path}, label={l_path}")
        return [(a_path, l_path)]

    audio_files = sorted(AUDIO_DIR.glob("audio_event_*.csv"))
    if MAX_FILES:
        audio_files = audio_files[:MAX_FILES]
    pairs: List[Tuple[Path, Path]] = []
    for a in audio_files:
        uid = get_audio_uuid(a)
        # Accept both <uuid>.csv and labels_<uuid>.csv
        label_path_plain = LABEL_DIR / f"{uid}.csv"
        label_path_pref = LABEL_DIR / f"labels_{uid}.csv"
        if label_path_plain.exists():
            label_path = label_path_plain
        elif label_path_pref.exists():
            label_path = label_path_pref
        else:
            label_path = None
        if label_path:
            pairs.append((a, label_path))
    if not pairs:
        raise RuntimeError(f"No (audio,label) pairs found under {AUDIO_DIR} and {LABEL_DIR} (accepted label names: <uuid>.csv or labels_<uuid>.csv)")
    return pairs


def load_labels(label_path: Path) -> Tuple[float, float]:
    df = pd.read_csv(label_path)
    if df.empty:
        raise ValueError(f"Empty label file {label_path}")

    def first_numeric(names: List[str]) -> float:
        for name in names:
            if name in df.columns:
                val = pd.to_numeric(df[name], errors="coerce").iloc[0]
                if not np.isnan(val):
                    return float(val)
        # fallback: first numeric column
        for col in df.columns:
            val = pd.to_numeric(df[col], errors="coerce").iloc[0]
            if not np.isnan(val):
                return float(val)
        raise ValueError(f"No numeric columns found in {label_path}")

    angle_deg = first_numeric(["angle_deg", "angle"])
    dist_val = first_numeric(["distance_rel", "distance_px", "distance_macro", "distance_micro"])
    return angle_deg, dist_val


def compute_mel_ipd_ild(
    audio: np.ndarray,
    sr: int,
    n_mels: int,
    n_fft: int,
    hop_length: int,
    ref_ch: int = 0,
    ild_gain: float = 1.5,
) -> np.ndarray:
    """Compute log-Mel + IPD + ILD maps stacked on channel dimension."""
    def _resample_spec(spec: np.ndarray, target_bins: int) -> np.ndarray:
        """
        Resample a spectrogram-like tensor (C, F, T) along the frequency axis to target_bins.
        """
        c, f, t = spec.shape
        if f == target_bins:
            return spec
        x_old = np.linspace(0.0, 1.0, num=f, dtype=np.float32)
        x_new = np.linspace(0.0, 1.0, num=target_bins, dtype=np.float32)
        out = np.empty((c, target_bins, t), dtype=np.float32)
        for ci in range(c):
            for ti in range(t):
                out[ci, :, ti] = np.interp(x_new, x_old, spec[ci, :, ti], left=0.0, right=0.0)
        return out

    num_ch = min(audio.shape[1], NUM_CHANNELS)
    mel_list = []
    stft_list = []
    for ch in range(num_ch):
        y = audio[:, ch].astype(np.float32)
        mel = librosa.feature.melspectrogram(
            y=y, sr=sr, n_fft=n_fft, hop_length=hop_length, n_mels=n_mels, center=True
        )
        mel_db = librosa.power_to_db(mel, ref=np.max).astype(np.float32)
        mel_list.append(mel_db)
        stft = librosa.stft(y=y, n_fft=n_fft, hop_length=hop_length, center=True)
        stft_list.append(stft)

    # Pad missing channels with zeros
    while len(mel_list) < NUM_CHANNELS:
        mel_list.append(np.zeros_like(mel_list[0]))
        stft_list.append(np.zeros_like(stft_list[0]))

    mel_stack = np.stack(mel_list, axis=0)  # (C, M, T)

    # IPD/ILD relative to reference channel
    ref_spec = stft_list[ref_ch]
    ref_mag = np.abs(ref_spec) + 1e-8
    ref_phase = np.angle(ref_spec)
    ipd_maps = []
    ild_maps = []
    for ch in range(NUM_CHANNELS):
        if ch == ref_ch:
            ipd_maps.append(np.zeros_like(ref_phase, dtype=np.float32))
            ild_maps.append(np.zeros_like(ref_mag, dtype=np.float32))
            continue
        cur_spec = stft_list[ch]
        cur_mag = np.abs(cur_spec) + 1e-8
        cur_phase = np.angle(cur_spec)
        ipd = np.sin(cur_phase - ref_phase).astype(np.float32)
        ild = (np.log((cur_mag / ref_mag))).astype(np.float32) * ild_gain
        ipd_maps.append(ipd)
        ild_maps.append(ild)

    ipd_stack = np.stack(ipd_maps, axis=0)
    ild_stack = np.stack(ild_maps, axis=0)

    # Align time dimension
    T = mel_stack.shape[2]
    ipd_stack = ipd_stack[:, :, :T]
    ild_stack = ild_stack[:, :, :T]

    # Resample IPD/ILD freq axis to n_mels to allow concatenation
    ipd_stack = _resample_spec(ipd_stack, n_mels)
    ild_stack = _resample_spec(ild_stack, n_mels)

    feats = np.concatenate([mel_stack, ipd_stack, ild_stack], axis=0)
    return feats.astype(np.float32)


def downsample_wave(audio: np.ndarray, target_sr: int) -> np.ndarray:
    if target_sr >= AUDIO_SR:
        return audio
    return librosa.resample(audio.astype(np.float32), orig_sr=AUDIO_SR, target_sr=target_sr, axis=0)


class AudioFeatureDataset(torch.utils.data.Dataset):
    def __init__(
        self,
        pairs: List[Tuple[Path, Path]],
        feature_type: str,
        feature_cfg: dict,
        dist_thresholds: Tuple[float, ...],
        dist_bins: int,
        train_mode: bool = False,
    ):
        self.pairs = pairs
        self.feature_type = feature_type
        self.feature_cfg = feature_cfg
        self.dist_thresholds = dist_thresholds
        self.dist_bins = dist_bins
        self.train_mode = train_mode

    def __len__(self) -> int:
        return len(self.pairs)

    def __getitem__(self, idx: int):
        audio_path, label_path = self.pairs[idx]
        angle_deg, dist_rel = load_labels(label_path)
        audio_mat = pd.read_csv(audio_path, dtype=np.float32, engine="c").values
        if audio_mat.ndim != 2 or audio_mat.shape[1] != NUM_CHANNELS:
            raise ValueError(f"Invalid audio shape in {audio_path}")

        if self.feature_type == "mel_ipd":
            feats = compute_mel_ipd_ild(
                audio_mat,
                sr=AUDIO_SR,
                n_mels=self.feature_cfg["n_mels"],
                n_fft=self.feature_cfg["n_fft"],
                hop_length=self.feature_cfg["hop_length"],
                ref_ch=0,
                ild_gain=self.feature_cfg.get("ild_gain", 1.5),
            )  # (C', M, T)
            feats_tensor = torch.from_numpy(feats)
            if self.train_mode:
                # Small time shift and channel gain jitter on spectrograms
                if np.random.rand() < 0.5:
                    shift = np.random.randint(-2, 3)
                    feats_tensor = torch.roll(feats_tensor, shifts=shift, dims=-1)
                gains = torch.empty(feats_tensor.shape[0]).uniform_(0.9, 1.1)
                feats_tensor = feats_tensor * gains[:, None, None]
        elif self.feature_type == "raw1d":
            dsr = self.feature_cfg["target_sr"]
            audio_ds = downsample_wave(audio_mat, dsr)
            feats_tensor = torch.from_numpy(audio_ds.T)  # (C, L)
            if self.train_mode:
                # Small time shift and per-channel gain jitter
                if np.random.rand() < 0.5:
                    shift = np.random.randint(-int(0.01 * feats_tensor.shape[1]), int(0.01 * feats_tensor.shape[1]) + 1)
                    feats_tensor = torch.roll(feats_tensor, shifts=shift, dims=-1)
                gains = torch.empty(feats_tensor.shape[0]).uniform_(0.9, 1.1)
                feats_tensor = feats_tensor * gains[:, None]
        else:
            raise ValueError(f"Unknown feature type {self.feature_type}")

        angle_cls = angle_deg_to_class(np.array([angle_deg], dtype=np.float32))[0]
        dist_cls, _ = dist_to_class(
            np.array([dist_rel], dtype=np.float32),
            thresholds=self.dist_thresholds,
            num_bins=self.dist_bins,
        )
        dist_cls = dist_cls[0]
        ang_vec = torch.tensor([math.sin(math.radians(angle_deg)), math.cos(math.radians(angle_deg))], dtype=torch.float32)

        return feats_tensor, angle_cls, dist_cls, ang_vec


# ===== Models =====


class ResidualBlock(nn.Module):
    def __init__(self, in_ch: int, out_ch: int, stride: int = 1):
        super().__init__()
        self.conv1 = nn.Conv2d(in_ch, out_ch, kernel_size=3, stride=stride, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(out_ch)
        self.conv2 = nn.Conv2d(out_ch, out_ch, kernel_size=3, stride=1, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(out_ch)
        self.skip = None
        if stride != 1 or in_ch != out_ch:
            self.skip = nn.Conv2d(in_ch, out_ch, kernel_size=1, stride=stride, bias=False)
            self.skip_bn = nn.BatchNorm2d(out_ch)

    def forward(self, x):
        out = F.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        if self.skip is not None:
            x = self.skip_bn(self.skip(x))
        out += x
        return F.relu(out)


class ResNet18MT(nn.Module):
    def __init__(self, in_ch: int, angle_classes: int, dist_classes: int, dropout: float = 0.2):
        super().__init__()
        widths = [64, 128, 256, 512]
        self.stem = nn.Sequential(
            nn.Conv2d(in_ch, widths[0], kernel_size=7, stride=2, padding=3, bias=False),
            nn.BatchNorm2d(widths[0]),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=3, stride=2, padding=1),
        )
        self.layer1 = nn.Sequential(ResidualBlock(widths[0], widths[0]), ResidualBlock(widths[0], widths[0]))
        self.layer2 = nn.Sequential(ResidualBlock(widths[0], widths[1], stride=2), ResidualBlock(widths[1], widths[1]))
        self.layer3 = nn.Sequential(ResidualBlock(widths[1], widths[2], stride=2), ResidualBlock(widths[2], widths[2]))
        self.layer4 = nn.Sequential(ResidualBlock(widths[2], widths[3], stride=2), ResidualBlock(widths[3], widths[3]))
        self.pool = nn.AdaptiveAvgPool2d((1, 1))
        self.drop = nn.Dropout(dropout)
        self.head_angle = nn.Linear(widths[3], angle_classes)
        self.head_dist = nn.Linear(widths[3], dist_classes)
        self.head_vec = nn.Linear(widths[3], 2)  # sin, cos

    def forward(self, x):
        x = self.stem(x)
        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.layer4(x)
        x = self.pool(x).flatten(1)
        x = self.drop(x)
        angle_logits = self.head_angle(x)
        dist_logits = self.head_dist(x)
        vec = torch.tanh(self.head_vec(x))
        return angle_logits, dist_logits, vec


class CRNN(nn.Module):
    def __init__(self, in_ch: int, angle_classes: int, dist_classes: int, hidden: int = 128, dropout: float = 0.2):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(in_ch, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.MaxPool2d((2, 2)),
            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(),
            nn.MaxPool2d((2, 2)),
        )
        self.gru = nn.GRU(input_size=128, hidden_size=hidden, num_layers=2, batch_first=True, bidirectional=True, dropout=dropout)
        self.drop = nn.Dropout(dropout)
        self.head_angle = nn.Linear(hidden * 2, angle_classes)
        self.head_dist = nn.Linear(hidden * 2, dist_classes)
        self.head_vec = nn.Linear(hidden * 2, 2)

    def forward(self, x):
        # x: (B, C, F, T)
        x = self.conv(x)  # (B, C', F', T')
        # Collapse frequency to channel dimension to keep GRU input fixed
        x = x.mean(dim=2)  # (B, C', T')
        x = x.permute(0, 2, 1)  # (B, T', C')
        out, _ = self.gru(x)
        out = out.mean(dim=1)
        out = self.drop(out)
        angle_logits = self.head_angle(out)
        dist_logits = self.head_dist(out)
        vec = torch.tanh(self.head_vec(out))
        return angle_logits, dist_logits, vec


class Conv1DSeparable(nn.Module):
    def __init__(self, in_ch: int, angle_classes: int, dist_classes: int, dropout: float = 0.15):
        super().__init__()
        layers = []
        chs = [in_ch, 32, 64, 128]
        for i in range(len(chs) - 1):
            layers.append(nn.Conv1d(chs[i], chs[i], kernel_size=5, padding=2, groups=chs[i]))
            layers.append(nn.Conv1d(chs[i], chs[i + 1], kernel_size=1))
            layers.append(nn.BatchNorm1d(chs[i + 1]))
            layers.append(nn.ReLU())
            layers.append(nn.MaxPool1d(kernel_size=2))
        self.conv = nn.Sequential(*layers)
        self.drop = nn.Dropout(dropout)
        self.head_angle = nn.Linear(128, angle_classes)
        self.head_dist = nn.Linear(128, dist_classes)
        self.head_vec = nn.Linear(128, 2)

    def forward(self, x):
        # x: (B, C, L)
        x = self.conv(x)
        x = x.mean(dim=-1)
        x = self.drop(x)
        angle_logits = self.head_angle(x)
        dist_logits = self.head_dist(x)
        vec = torch.tanh(self.head_vec(x))
        return angle_logits, dist_logits, vec


# ===== Training / evaluation =====


@dataclass
class Config:
    name: str
    feature_type: str  # mel_ipd or raw1d
    feature_cfg: dict
    model_cfg: dict
    epochs: int = 15
    batch_size: int = 8
    lr: float = 1e-3
    weight_decay: float = 1e-4
    patience: int = 3
    note: str = ""
    use_amp: bool = True
    label_smooth: float = 0.05
    augment: bool = True


def build_model(cfg: Config, in_ch: int, angle_classes: int, dist_classes: int) -> nn.Module:
    if cfg.name.startswith("resnet"):
        return ResNet18MT(in_ch, angle_classes, dist_classes, dropout=cfg.model_cfg.get("dropout", 0.2))
    if cfg.name.startswith("crnn"):
        return CRNN(in_ch, angle_classes, dist_classes, hidden=cfg.model_cfg.get("hidden", 128), dropout=cfg.model_cfg.get("dropout", 0.2))
    if cfg.name.startswith("conv1d"):
        return Conv1DSeparable(in_ch, angle_classes, dist_classes, dropout=cfg.model_cfg.get("dropout", 0.15))
    raise ValueError(f"Unknown model name {cfg.name}")


def multitask_loss(angle_logits, dist_logits, vec_pred, angle_cls, dist_cls, ang_vec, penalty_mat: torch.Tensor, dist_weight: torch.Tensor, label_smooth: float, dist_loss_scale: float = 1.0) -> torch.Tensor:
    ce_angle = F.cross_entropy(angle_logits, angle_cls, label_smoothing=label_smooth)
    ce_dist = F.cross_entropy(dist_logits, dist_cls, weight=dist_weight, label_smoothing=label_smooth) * dist_loss_scale
    l1_vec = F.l1_loss(vec_pred, ang_vec)
    with torch.no_grad():
        penalty = penalty_mat.to(angle_logits.device)
    probs = F.softmax(angle_logits, dim=1)
    # Expected penalty conditioned on true class for each sample
    penalty_vals = (penalty[angle_cls] * probs).sum(dim=1).mean()
    return ce_angle + ce_dist + 0.3 * l1_vec + PENALTY_SCALE * penalty_vals


def evaluate(
    model,
    loader,
    device,
    collect_preds: bool = False,
    penalty_mat: torch.Tensor | None = None,
    dist_bins: int = DIST_NUM_BINS,
):
    model.eval()
    angle_correct = 0
    dist_correct = 0
    joint_correct = 0
    total = 0
    angle_mae_list: List[float] = []
    severity_scores: List[float] = []
    dist_angle_weighted_sum = 0.0
    micro_angle_true: List[int] = []
    micro_angle_pred: List[int] = []
    micro_dist_true: List[int] = []
    micro_dist_pred: List[int] = []
    micro_angle_severity: List[float] = []
    micro_dist_severity: List[float] = []
    y_true_angle: List[int] = []
    y_pred_angle: List[int] = []
    y_true_dist: List[int] = []
    y_pred_dist: List[int] = []
    if penalty_mat is not None:
        penalty = penalty_mat.to(device)
        pen_min = float(penalty.min().item())
        pen_max = float(penalty.max().item())
        denom = (pen_max - pen_min) if pen_max > pen_min else 1.0
    else:
        penalty = None
        pen_min = 0.0
        denom = 1.0
    with torch.no_grad():
        for feats, angle_cls, dist_cls, ang_vec in loader:
            nb = device.type == "cuda"
            feats = feats.to(device, non_blocking=nb)
            angle_cls = angle_cls.to(device, non_blocking=nb)
            dist_cls = dist_cls.to(device, non_blocking=nb)
            ang_vec = ang_vec.to(device, non_blocking=nb)
            if feats.dim() == 3:  # raw1d -> (B, C, L)
                pass
            else:  # mel_ipd -> (B, C, F, T)
                feats = feats
            angle_logits, dist_logits, vec_pred = model(feats)
            angle_pred = angle_logits.argmax(dim=1)
            dist_pred = dist_logits.argmax(dim=1)
            angle_correct += (angle_pred == angle_cls).sum().item()
            dist_correct += (dist_pred == dist_cls).sum().item()
            joint_correct += ((angle_pred == angle_cls) & (dist_pred == dist_cls)).sum().item()
            total += angle_cls.size(0)
            pred_angle_rad = torch.atan2(vec_pred[:, 0], vec_pred[:, 1])
            true_angle_rad = torch.atan2(ang_vec[:, 0], ang_vec[:, 1])
            diff = torch.remainder(pred_angle_rad - true_angle_rad + math.pi, 2 * math.pi) - math.pi
            angle_mae_list.append(torch.abs(diff).cpu().numpy())
            if penalty is not None:
                sev = 1.0 - ((penalty[angle_cls, angle_pred] - pen_min) / denom)
                severity_scores.append(sev.detach().cpu().numpy())

            # Micro-angle confusion (12 classes, 30° bins)
            true_angle_deg = torch.remainder(true_angle_rad * 180.0 / math.pi + 360.0, 360.0)
            pred_angle_deg = torch.remainder(pred_angle_rad * 180.0 / math.pi + 360.0, 360.0)
            true_micro_a = torch.div(true_angle_deg, 360.0 / MICRO_ANGLE_CLASSES, rounding_mode="floor").to(torch.int64).clamp(0, MICRO_ANGLE_CLASSES - 1)
            pred_micro_a = torch.div(pred_angle_deg, 360.0 / MICRO_ANGLE_CLASSES, rounding_mode="floor").to(torch.int64).clamp(0, MICRO_ANGLE_CLASSES - 1)
            micro_angle_true.extend(true_micro_a.cpu().tolist())
            micro_angle_pred.extend(pred_micro_a.cpu().tolist())
            # Severity for micro-angles: circular distance normalized to [0,1]
            ang_diff = torch.remainder(pred_micro_a - true_micro_a + MICRO_ANGLE_CLASSES, MICRO_ANGLE_CLASSES)
            ang_diff = torch.minimum(ang_diff, MICRO_ANGLE_CLASSES - ang_diff).float()
            micro_angle_severity.append((1.0 - ang_diff / (MICRO_ANGLE_CLASSES / 2)).clamp(min=0.0).cpu().numpy())

            # Micro-distance confusion (9 classes) via scaled class expectation
            dist_probs = F.softmax(dist_logits, dim=1)
            cls_idx = torch.arange(dist_logits.size(1), device=device, dtype=torch.float32)
            expected_dist = (dist_probs * cls_idx).sum(dim=1)  # in [0, num_dist_classes-1]
            pred_micro_d = torch.round(
                (expected_dist / max(dist_logits.size(1) - 1, 1e-6)) * (MICRO_DIST_CLASSES - 1)
            ).to(torch.int64).clamp(0, MICRO_DIST_CLASSES - 1)
            true_micro_d = torch.round(
                (dist_cls.float() / max(dist_logits.size(1) - 1, 1e-6)) * (MICRO_DIST_CLASSES - 1)
            ).to(torch.int64).clamp(0, MICRO_DIST_CLASSES - 1)
            micro_dist_true.extend(true_micro_d.cpu().tolist())
            micro_dist_pred.extend(pred_micro_d.cpu().tolist())
            dist_diff = (pred_micro_d - true_micro_d).abs().float()
            micro_dist_severity.append((1.0 - dist_diff / (MICRO_DIST_CLASSES - 1)).clamp(min=0.0).cpu().numpy())
            # Distance accuracy weighted by angle severity reward
            dist_angle_weighted_sum += float((dist_pred == dist_cls).float().mul(sev if penalty is not None else 1.0).sum().item())
            if collect_preds:
                y_true_angle.extend(angle_cls.cpu().tolist())
                y_pred_angle.extend(angle_pred.cpu().tolist())
                y_true_dist.extend(dist_cls.cpu().tolist())
                y_pred_dist.extend(dist_pred.cpu().tolist())
    if total == 0:
        metrics = {"angle_acc": 0.0, "dist_acc": 0.0, "joint_acc": 0.0, "angle_mae": 0.0}
        return (metrics, y_true_angle, y_pred_angle, y_true_dist, y_pred_dist) if collect_preds else metrics
    angle_mae = float(np.mean(np.concatenate(angle_mae_list))) * 180.0 / math.pi
    metrics = {
        "angle_acc": angle_correct / total,
        "dist_acc": dist_correct / total,
        "joint_acc": joint_correct / total,
        "angle_mae": angle_mae,
        "angle_severity_acc": float(np.mean(np.concatenate(severity_scores))) if severity_scores else 0.0,
        "micro_angle_severity_acc": float(np.mean(np.concatenate(micro_angle_severity))) if micro_angle_severity else 0.0,
        "micro_dist_severity_acc": float(np.mean(np.concatenate(micro_dist_severity))) if micro_dist_severity else 0.0,
        "dist_acc_angle_weighted": dist_angle_weighted_sum / total if total > 0 else 0.0,
    }
    if collect_preds:
        return (
            metrics,
            y_true_angle,
            y_pred_angle,
            y_true_dist,
            y_pred_dist,
            micro_angle_true,
            micro_angle_pred,
            micro_dist_true,
            micro_dist_pred,
        )
    return metrics


def train_one_fold(cfg: Config, train_pairs, val_pairs, angle_classes_count: int, dist_classes_count: int, dist_thresholds: Tuple[float, ...], train_dist_classes: np.ndarray):
    train_ds = AudioFeatureDataset(train_pairs, cfg.feature_type, cfg.feature_cfg, dist_thresholds, dist_classes_count, train_mode=True)
    val_ds = AudioFeatureDataset(val_pairs, cfg.feature_type, cfg.feature_cfg, dist_thresholds, dist_classes_count, train_mode=False)
    # Oversample minority distance bins
    counts = np.bincount(train_dist_classes, minlength=dist_classes_count)
    weights = np.zeros_like(train_dist_classes, dtype=np.float32)
    for cls_idx in range(dist_classes_count):
        cls_mask = train_dist_classes == cls_idx
        if counts[cls_idx] > 0:
            weights[cls_mask] = 1.0 / counts[cls_idx]
    sampler = torch.utils.data.WeightedRandomSampler(weights.tolist(), num_samples=len(weights), replacement=True)

    train_loader = torch.utils.data.DataLoader(
        train_ds,
        batch_size=cfg.batch_size,
        shuffle=False,
        sampler=sampler,
        drop_last=False,
        num_workers=LOAD_WORKERS,
        pin_memory=True,
    )
    val_loader = torch.utils.data.DataLoader(
        val_ds,
        batch_size=cfg.batch_size,
        shuffle=False,
        drop_last=False,
        num_workers=LOAD_WORKERS,
        pin_memory=True,
    )

    sample_feats, _, _, _ = train_ds[0]
    in_ch = sample_feats.shape[0] if cfg.feature_type == "mel_ipd" else NUM_CHANNELS

    model = build_model(cfg, in_ch=in_ch, angle_classes=angle_classes_count, dist_classes=dist_classes_count).to(DEVICE)
    optimizer = torch.optim.AdamW(model.parameters(), lr=cfg.lr, weight_decay=cfg.weight_decay)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="max", patience=2, factor=0.5)
    penalty_mat = angle_penalty_matrix(angle_classes_count).to(DEVICE)
    # Distance class weights for imbalance
    class_counts = np.bincount(train_dist_classes, minlength=dist_classes_count)
    inv_counts = np.where(class_counts > 0, 1.0 / class_counts, 0.0)
    dist_weight = torch.tensor(inv_counts, dtype=torch.float32, device=DEVICE)
    scaler = make_grad_scaler(cfg.use_amp and DEVICE.type == "cuda")

    best_joint = -1.0
    best_metrics: Dict[str, float] = {}
    best_state: Dict[str, torch.Tensor] | None = None
    best_epoch = 0
    patience_ctr = 0

    print(f"[INFO] {cfg.name}: workers={LOAD_WORKERS}, train_batches={len(train_loader)}, val_batches={len(val_loader)}, dist_loss_scale={DIST_LOSS_SCALE}")
    for epoch in range(1, cfg.epochs + 1):
        model.train()
        epoch_loss = 0.0
        for feats, angle_cls, dist_cls, ang_vec in train_loader:
            nb = DEVICE.type == "cuda"
            feats = feats.to(DEVICE, non_blocking=nb)
            angle_cls = angle_cls.to(DEVICE, non_blocking=nb)
            dist_cls = dist_cls.to(DEVICE, non_blocking=nb)
            ang_vec = ang_vec.to(DEVICE, non_blocking=nb)
            optimizer.zero_grad(set_to_none=True)
            with autocast_ctx(cfg.use_amp and DEVICE.type == "cuda"):
                angle_logits, dist_logits, vec_pred = model(feats)
                loss = multitask_loss(
                    angle_logits,
                    dist_logits,
                    vec_pred,
                    angle_cls,
                    dist_cls,
                    ang_vec,
                    penalty_mat,
                    dist_weight,
                    cfg.label_smooth,
                    DIST_LOSS_SCALE,
                )
            scaler.scale(loss).backward()
            nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
            scaler.step(optimizer)
            scaler.update()
            epoch_loss += loss.item() * angle_cls.size(0)
        epoch_loss /= len(train_ds)

        val_metrics = evaluate(model, val_loader, DEVICE, collect_preds=False, penalty_mat=penalty_mat)
        scheduler.step(val_metrics["joint_acc"])

        if val_metrics["joint_acc"] > best_joint:
            best_joint = val_metrics["joint_acc"]
            best_metrics = {"loss": epoch_loss, **val_metrics}
            best_state = {k: v.detach().cpu() for k, v in model.state_dict().items()}
            best_epoch = epoch
            patience_ctr = 0
        else:
            patience_ctr += 1
            if patience_ctr >= cfg.patience:
                break

    if best_state is not None:
        model.load_state_dict(best_state)
    else:
        best_state = {k: v.detach().cpu() for k, v in model.state_dict().items()}
        best_epoch = cfg.epochs
        best_metrics = {"loss": epoch_loss, **evaluate(model, val_loader, DEVICE, collect_preds=False)}

    # Final evaluation with predictions for confusion matrices
    final_eval = evaluate(model, val_loader, DEVICE, collect_preds=True, penalty_mat=penalty_mat)
    (
        final_metrics,
        y_true_angle,
        y_pred_angle,
        y_true_dist,
        y_pred_dist,
        y_true_micro_angle,
        y_pred_micro_angle,
        y_true_micro_dist,
        y_pred_micro_dist,
    ) = final_eval
    metrics_out = {**final_metrics, "loss": best_metrics.get("loss", final_metrics.get("loss", 0.0)), "best_epoch": best_epoch}
    return (
        metrics_out,
        y_true_angle,
        y_pred_angle,
        y_true_dist,
        y_pred_dist,
        y_true_micro_angle,
        y_pred_micro_angle,
        y_true_micro_dist,
        y_pred_micro_dist,
        best_state,
        in_ch,
    )


def run_cv(cfg: Config, pairs: List[Tuple[Path, Path]], angle_classes: np.ndarray, dist_classes: np.ndarray, dist_thresholds: Tuple[float, ...], run_id: str, run_ckpt_dir: Path) -> Dict[str, float]:
    joint_classes = angle_classes * DIST_NUM_BINS + dist_classes
    skf = StratifiedKFold(n_splits=DESIRED_FOLDS, shuffle=True, random_state=SEED)
    fold_metrics: List[Dict[str, float]] = []
    all_true_angle: List[int] = []
    all_pred_angle: List[int] = []
    all_true_dist: List[int] = []
    all_pred_dist: List[int] = []
    all_true_micro_angle: List[int] = []
    all_pred_micro_angle: List[int] = []
    all_true_micro_dist: List[int] = []
    all_pred_micro_dist: List[int] = []
    per_fold_logs: List[str] = []
    best_fold_metrics: Dict[str, float] | None = None
    best_fold_state: Dict[str, torch.Tensor] | None = None
    best_fold_idx = -1
    best_in_ch = NUM_CHANNELS
    best_angle_state: Dict[str, torch.Tensor] | None = None
    best_distw_state: Dict[str, torch.Tensor] | None = None
    best_angle_in_ch = NUM_CHANNELS
    best_distw_in_ch = NUM_CHANNELS
    best_angle_fold_idx = -1
    best_angle_metrics: Dict[str, float] | None = None
    best_distw_fold_idx = -1
    best_distw_metrics: Dict[str, float] | None = None
    for fold_idx, (train_idx, val_idx) in enumerate(skf.split(pairs, joint_classes), start=1):
        train_pairs = [pairs[i] for i in train_idx]
        val_pairs = [pairs[i] for i in val_idx]
        (
            metrics,
            y_true_a,
            y_pred_a,
            y_true_d,
            y_pred_d,
            y_true_micro_a,
            y_pred_micro_a,
            y_true_micro_d,
            y_pred_micro_d,
            best_state,
            in_ch,
        ) = train_one_fold(cfg, train_pairs, val_pairs, len(ANGLE_LABELS), DIST_NUM_BINS, dist_thresholds, dist_classes[train_idx])
        fold_metrics.append(metrics)
        all_true_angle.extend(y_true_a)
        all_pred_angle.extend(y_pred_a)
        all_true_dist.extend(y_true_d)
        all_pred_dist.extend(y_pred_d)
        all_true_micro_angle.extend(y_true_micro_a)
        all_pred_micro_angle.extend(y_pred_micro_a)
        all_true_micro_dist.extend(y_true_micro_d)
        all_pred_micro_dist.extend(y_pred_micro_d)
        if best_fold_metrics is None or metrics.get("joint_acc", 0.0) > best_fold_metrics.get("joint_acc", -1.0):
            best_fold_metrics = metrics
            best_fold_state = best_state
            best_fold_idx = fold_idx
            best_in_ch = in_ch
        if best_angle_metrics is None or metrics.get("angle_severity_acc", 0.0) > best_angle_metrics.get("angle_severity_acc", -1.0):
            best_angle_metrics = metrics
            best_angle_fold_idx = fold_idx
            best_angle_state = best_state
            best_angle_in_ch = in_ch
        if best_distw_metrics is None or metrics.get("dist_acc_angle_weighted", 0.0) > best_distw_metrics.get("dist_acc_angle_weighted", -1.0):
            best_distw_metrics = metrics
            best_distw_fold_idx = fold_idx
            best_distw_state = best_state
            best_distw_in_ch = in_ch
        msg = (
            f"[INFO] {cfg.name} fold {fold_idx}/{DESIRED_FOLDS}: "
            f"joint={metrics.get('joint_acc', 0):.4f}, angle={metrics.get('angle_acc', 0):.4f}, "
            f"dist={metrics.get('dist_acc', 0):.4f}, mae={metrics.get('angle_mae', 0):.2f}, "
            f"sev_ang={metrics.get('angle_severity_acc', 0):.4f}, "
            f"sev_dist={metrics.get('micro_dist_severity_acc', 0):.4f}"
        )
        per_fold_logs.append(msg)
        print(msg)

    if best_fold_state is None or best_fold_metrics is None:
        raise RuntimeError(f"No best fold found for {cfg.name}")
    if best_angle_metrics is None:
        best_angle_metrics = best_fold_metrics
        best_angle_fold_idx = best_fold_idx
    if best_angle_state is None:
        best_angle_state = best_fold_state
    if best_angle_in_ch is None:
        best_angle_in_ch = best_in_ch
    if best_distw_metrics is None:
        best_distw_metrics = best_fold_metrics
        best_distw_fold_idx = best_fold_idx
    if best_distw_state is None:
        best_distw_state = best_fold_state
    if best_distw_in_ch is None:
        best_distw_in_ch = best_in_ch

    angle_cm = confusion_matrix(all_true_angle, all_pred_angle, labels=list(range(len(ANGLE_LABELS))))
    dist_cm = confusion_matrix(all_true_dist, all_pred_dist, labels=list(range(DIST_NUM_BINS)))
    joint_true = [a * DIST_NUM_BINS + d for a, d in zip(all_true_angle, all_true_dist)]
    joint_pred = [a * DIST_NUM_BINS + d for a, d in zip(all_pred_angle, all_pred_dist)]
    joint_labels = list(range(len(ANGLE_LABELS) * DIST_NUM_BINS))
    joint_cm = confusion_matrix(joint_true, joint_pred, labels=joint_labels)
    micro_angle_cm = confusion_matrix(all_true_micro_angle, all_pred_micro_angle, labels=list(range(MICRO_ANGLE_CLASSES)))
    micro_dist_cm = confusion_matrix(all_true_micro_dist, all_pred_micro_dist, labels=list(range(MICRO_DIST_CLASSES)))
    dist_labels = get_distance_labels(DIST_NUM_BINS)

    run_ckpt_dir.mkdir(parents=True, exist_ok=True)

    def _save_ckpt(path: Path, state: Dict[str, torch.Tensor], fold_id: int, metrics: Dict[str, float], tag: str, in_ch_val: int):
        torch.save(
            {
                "model_state": state,
                "config": cfg,
                "fold": fold_id,
                "run_id": run_id,
                "tag": tag,
                "input_channels": in_ch_val,
                "angle_labels": ANGLE_LABELS,
                "dist_labels": dist_labels,
                "dist_thresholds": dist_thresholds,
                "metrics": metrics,
            },
            path,
        )

    joint_ckpt_path = run_ckpt_dir / f"{cfg.name}_best_joint.pt"
    angle_ckpt_path = run_ckpt_dir / f"{cfg.name}_best_angle.pt"
    distw_ckpt_path = run_ckpt_dir / f"{cfg.name}_best_dist_angle_weighted.pt"

    _save_ckpt(joint_ckpt_path, best_fold_state, best_fold_idx, best_fold_metrics, "best_joint", best_in_ch)
    _save_ckpt(angle_ckpt_path, best_angle_state, best_angle_fold_idx, best_angle_metrics, "best_angle_severity", best_angle_in_ch)
    _save_ckpt(distw_ckpt_path, best_distw_state, best_distw_fold_idx, best_distw_metrics, "best_dist_angle_weighted", best_distw_in_ch)

    print(f"[INFO] Saved best checkpoints for {cfg.name}: joint={joint_ckpt_path}, angle={angle_ckpt_path}, dist_aw={distw_ckpt_path}")

    summary = {
        "config": cfg,
        "mean_joint": float(np.mean([m["joint_acc"] for m in fold_metrics])),
        "mean_angle": float(np.mean([m["angle_acc"] for m in fold_metrics])),
        "mean_dist": float(np.mean([m["dist_acc"] for m in fold_metrics])),
        "mean_mae": float(np.mean([m["angle_mae"] for m in fold_metrics])),
        "mean_severity": float(np.mean([m.get("angle_severity_acc", 0.0) for m in fold_metrics])),
        "mean_micro_angle_severity": float(np.mean([m.get("micro_angle_severity_acc", 0.0) for m in fold_metrics])),
        "mean_micro_dist_severity": float(np.mean([m.get("micro_dist_severity_acc", 0.0) for m in fold_metrics])),
        "angle_cm": angle_cm,
        "dist_cm": dist_cm,
        "joint_cm": joint_cm,
        "micro_angle_cm": micro_angle_cm,
        "micro_dist_cm": micro_dist_cm,
        "micro_angle_labels": micro_angle_labels(),
        "micro_dist_labels": micro_dist_labels(),
        "fold_logs": per_fold_logs,
        "checkpoint": joint_ckpt_path,
        "checkpoint_angle": angle_ckpt_path,
        "checkpoint_dist_angle": distw_ckpt_path,
        "best_fold": best_fold_idx,
        "best_fold_metrics": best_fold_metrics,
        "best_angle_fold": best_angle_fold_idx,
        "best_angle_fold_metrics": best_angle_metrics,
        "best_distw_fold": best_distw_fold_idx,
        "best_distw_fold_metrics": best_distw_metrics,
    }
    return summary


def main():
    if REQUIRE_CUDA and not torch.cuda.is_available():
        raise RuntimeError("CLASSIFIER_REQUIRE_CUDA=1 but no CUDA device is available")
    set_seed(SEED)
    configure_runtime()
    pairs = load_pairs()
    angles = []
    dists = []
    for _, label_path in pairs:
        ang, dist = load_labels(label_path)
        angles.append(ang)
        dists.append(dist)
    angles = np.array(angles, dtype=np.float32)
    dists = np.array(dists, dtype=np.float32)
    angle_classes = angle_deg_to_class(angles)
    dist_thresholds_override: Tuple[float, ...] | None = None
    if DIST_THRESHOLDS_ENV:
        dist_thresholds_override = parse_thresholds(DIST_THRESHOLDS_ENV, DIST_NUM_BINS - 1, "CLASSIFIER_DIST_THRESHOLDS")
    elif DIST_QUANTILES_ENV:
        qs = parse_thresholds(DIST_QUANTILES_ENV, DIST_NUM_BINS - 1, "CLASSIFIER_DIST_QUANTILES")
        dist_thresholds_override = tuple(np.quantile(dists, qs))
    elif DIST_NUM_BINS == 3:
        dist_thresholds_override = tuple(np.quantile(dists, DEFAULT_DIST_QUANTILES))

    dist_classes, dist_thresholds = dist_to_class(dists, thresholds=dist_thresholds_override, num_bins=DIST_NUM_BINS)
    dist_labels = get_distance_labels(DIST_NUM_BINS)
    print(f"[INFO] Loaded {len(pairs)} samples | angle bins={len(ANGLE_LABELS)}, dist bins={len(dist_labels)} thresholds={dist_thresholds}")
    print(f"[INFO] Device: {DEVICE} | folds={DESIRED_FOLDS}")

    configs: List[Config] = [
        Config(
            name="resnet18_mel96",
            feature_type="mel_ipd",
            feature_cfg={"n_mels": 96, "n_fft": 2048, "hop_length": 768, "ild_gain": 1.6},
            model_cfg={"dropout": 0.3},
            epochs=20,
            batch_size=6,
            lr=3.2e-4,
            weight_decay=1e-4,
        ),
        Config(
            name="crnn_mel80",
            feature_type="mel_ipd",
            feature_cfg={"n_mels": 80, "n_fft": 2048, "hop_length": 720, "ild_gain": 1.6},
            model_cfg={"hidden": 192, "dropout": 0.22},
            epochs=18,
            batch_size=6,
            lr=4.5e-4,
            weight_decay=1e-4,
        ),
        Config(
            name="conv1d_sep_ds48k",
            feature_type="raw1d",
            feature_cfg={"target_sr": 48_000},
            model_cfg={"dropout": 0.12},
            epochs=16,
            batch_size=4,
            lr=6e-4,
            weight_decay=1e-4,
        ),
    ]

    summaries: List[Dict[str, float]] = []
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_ckpt_dir = CHECKPOINT_DIR  # Salva direttamente in checkpoints invece che in sottocartella
    results_path = BASE_DIR / "model_classifier" / f"results_{run_id}.txt"

    for cfg in configs:
        start = time.time()
        summary = run_cv(cfg, pairs, angle_classes, dist_classes, dist_thresholds, run_id, run_ckpt_dir)
        summary["duration_min"] = (time.time() - start) / 60.0
        summaries.append(summary)
        print(f"[INFO] Confusion matrix (angle) for {cfg.name}:\n{summary['angle_cm']}")
        print(f"[INFO] Confusion matrix (distance) for {cfg.name}:\n{summary['dist_cm']}")
        print(
            f"[INFO] {cfg.name} summary -> joint={summary['mean_joint']:.4f}, "
            f"angle={summary['mean_angle']:.4f}, dist={summary['mean_dist']:.4f}, mae={summary['mean_mae']:.2f}, "
            f"duration_min={summary['duration_min']:.2f}"
        )
        # Per-model detailed log file
        model_log = BASE_DIR / "model_classifier" / f"result_{cfg.name}_{run_id}.txt"
        with open(model_log, "w", encoding="utf-8") as mf:
            mf.write(f"Model: {cfg.name}\n")
            mf.write(f"Run: {run_id}\n")
            mf.write(f"Config: feat_type={cfg.feature_type}, feat_cfg={cfg.feature_cfg}, model_cfg={cfg.model_cfg}, epochs={cfg.epochs}, batch={cfg.batch_size}, lr={cfg.lr}, wd={cfg.weight_decay}, note={cfg.note}\n")
            for line in summary["fold_logs"]:
                mf.write(line + "\n")
            mf.write(f"Angle confusion matrix (labels={ANGLE_LABELS}):\n{summary['angle_cm']}\n")
            mf.write(f"Distance confusion matrix (labels={get_distance_labels(DIST_NUM_BINS)}):\n{summary['dist_cm']}\n")
            joint_labels_named = [f"{ANGLE_LABELS[a]}-{get_distance_labels(DIST_NUM_BINS)[d]}" for a in range(len(ANGLE_LABELS)) for d in range(DIST_NUM_BINS)]
            mf.write(f"Joint confusion matrix (angle x distance) labels={joint_labels_named}:\n{summary['joint_cm']}\n")
            mf.write(f"Micro-angle confusion matrix (12 classes, 30° bins): labels={summary['micro_angle_labels']}\n{summary['micro_angle_cm']}\n")
            mf.write(f"Micro-distance confusion matrix (9 classes): labels={summary['micro_dist_labels']}\n{summary['micro_dist_cm']}\n")
            mf.write(
                f"Means: joint={summary['mean_joint']:.4f}, angle={summary['mean_angle']:.4f}, dist={summary['mean_dist']:.4f}, mae={summary['mean_mae']:.2f}, "
                f"sev_acc={summary['mean_severity']:.4f}, micro_ang_sev={summary['mean_micro_angle_severity']:.4f}, micro_dist_sev={summary['mean_micro_dist_severity']:.4f}, "
                f"duration_min={summary['duration_min']:.2f}\n"
            )
            best_fold_metrics = summary.get("best_fold_metrics", {})
            mf.write(
                "Best fold summary:\n"
                f"  fold={summary.get('best_fold')} | checkpoint={summary.get('checkpoint')}\n"
                f"  joint_acc={best_fold_metrics.get('joint_acc', 0):.4f} | angle_acc={best_fold_metrics.get('angle_acc', 0):.4f} | "
                f"dist_acc={best_fold_metrics.get('dist_acc', 0):.4f} | angle_mae={best_fold_metrics.get('angle_mae', 0):.2f} | "
                f"angle_sev={best_fold_metrics.get('angle_severity_acc', 0):.4f} | "
                f"micro_ang_sev={best_fold_metrics.get('micro_angle_severity_acc', 0):.4f} | "
                f"micro_dist_sev={best_fold_metrics.get('micro_dist_severity_acc', 0):.4f} | "
                f"best_epoch={best_fold_metrics.get('best_epoch', 0)} | loss={best_fold_metrics.get('loss', 0):.4f}\n"
            )
            best_angle_metrics = summary.get("best_angle_fold_metrics", {})
            mf.write(
                "Best fold (angle severity):\n"
                f"  fold={summary.get('best_angle_fold')} | checkpoint={summary.get('checkpoint_angle')}\n"
                f"  angle_acc={best_angle_metrics.get('angle_acc', 0):.4f} | angle_sev={best_angle_metrics.get('angle_severity_acc', 0):.4f} | "
                f"joint_acc={best_angle_metrics.get('joint_acc', 0):.4f} | dist_acc={best_angle_metrics.get('dist_acc', 0):.4f}\n"
            )
            best_distw_metrics = summary.get("best_distw_fold_metrics", {})
            mf.write(
                "Best fold (dist weighted by angle):\n"
                f"  fold={summary.get('best_distw_fold')} | checkpoint={summary.get('checkpoint_dist_angle')}\n"
                f"  dist_acc_angle_weighted={best_distw_metrics.get('dist_acc_angle_weighted', 0):.4f} | dist_acc={best_distw_metrics.get('dist_acc', 0):.4f} | "
                f"angle_sev={best_distw_metrics.get('angle_severity_acc', 0):.4f} | joint_acc={best_distw_metrics.get('joint_acc', 0):.4f}\n"
            )
        print(f"[INFO] Per-model log written to {model_log}")

    # Sort and pick best by joint/angle/dist accuracy
    sorted_joint = sorted(summaries, key=lambda s: s["mean_joint"], reverse=True)
    best_joint = sorted_joint[0]
    best_angle = sorted(summaries, key=lambda s: s["mean_angle"], reverse=True)[0]
    best_dist = sorted(summaries, key=lambda s: s["mean_dist"], reverse=True)[0]

    with open(results_path, "w", encoding="utf-8") as f:
        f.write(f"Run {run_id}\n")
        f.write(f"Samples={len(pairs)} | folds={DESIRED_FOLDS} | dist_bins={DIST_NUM_BINS} | device={DEVICE}\n")
        f.write(f"Dist thresholds: {dist_thresholds}\n")
        for s in summaries:
            cfg = s["config"]
            f.write(
                f"{cfg.name}: joint={s['mean_joint']:.4f}, angle={s['mean_angle']:.4f}, "
                f"dist={s['mean_dist']:.4f}, mae={s['mean_mae']:.2f}, sev_acc={s.get('mean_severity', 0):.4f}, "
                f"micro_ang_sev={s.get('mean_micro_angle_severity', 0):.4f}, micro_dist_sev={s.get('mean_micro_dist_severity', 0):.4f}, "
                f"epochs={cfg.epochs}, batch={cfg.batch_size}, lr={cfg.lr}, wd={cfg.weight_decay}, "
                f"feat={cfg.feature_type}, feat_cfg={cfg.feature_cfg}, model_cfg={cfg.model_cfg}, "
                f"duration_min={s['duration_min']:.2f}, best_fold={s.get('best_fold')}, checkpoint={s.get('checkpoint')}, "
                f"checkpoint_angle={s.get('checkpoint_angle')}, checkpoint_dist_angle={s.get('checkpoint_dist_angle')}\n"
            )
            f.write(f"  angle_cm:\n{s['angle_cm']}\n")
            f.write(f"  dist_cm:\n{s['dist_cm']}\n")
            joint_labels_named = [f"{ANGLE_LABELS[a]}-{get_distance_labels(DIST_NUM_BINS)[d]}" for a in range(len(ANGLE_LABELS)) for d in range(DIST_NUM_BINS)]
            f.write(f"  joint_cm (angle x distance) labels={joint_labels_named}:\n{s['joint_cm']}\n")
            f.write(f"  micro_angle_cm (labels={s['micro_angle_labels']}):\n{s['micro_angle_cm']}\n")
            f.write(f"  micro_dist_cm (labels={s['micro_dist_labels']}):\n{s['micro_dist_cm']}\n")
        f.write("CHECKPOINTS (best fold per config):\n")
        for s in summaries:
            bfm = s.get("best_fold_metrics", {})
            f.write(
                f"- {s['config'].name}: fold={s.get('best_fold')} | ckpt_joint={s.get('checkpoint')} | "
                f"joint={bfm.get('joint_acc', 0):.4f}, angle={bfm.get('angle_acc', 0):.4f}, "
                f"dist={bfm.get('dist_acc', 0):.4f}, mae={bfm.get('angle_mae', 0):.2f}, "
                f"best_epoch={bfm.get('best_epoch', 0)}, loss={bfm.get('loss', 0):.4f}\n"
            )
            baf = s.get("best_angle_fold_metrics", {})
            f.write(
                f"  angle_best: fold={s.get('best_angle_fold')} | ckpt_angle={s.get('checkpoint_angle')} | "
                f"angle_sev={baf.get('angle_severity_acc', 0):.4f}, angle_acc={baf.get('angle_acc', 0):.4f}, "
                f"joint={baf.get('joint_acc', 0):.4f}, dist={baf.get('dist_acc', 0):.4f}\n"
            )
            bdf = s.get("best_distw_fold_metrics", {})
            f.write(
                f"  dist_aw_best: fold={s.get('best_distw_fold')} | ckpt_dist_angle={s.get('checkpoint_dist_angle')} | "
                f"dist_acc_angle_weighted={bdf.get('dist_acc_angle_weighted', 0):.4f}, dist_acc={bdf.get('dist_acc', 0):.4f}, "
                f"angle_sev={bdf.get('angle_severity_acc', 0):.4f}, joint={bdf.get('joint_acc', 0):.4f}\n"
            )
        f.write(
            f"BEST JOINT => {best_joint['config'].name}: joint={best_joint['mean_joint']:.4f}, "
            f"angle={best_joint['mean_angle']:.4f}, dist={best_joint['mean_dist']:.4f}, mae={best_joint['mean_mae']:.2f}, "
            f"sev_acc={best_joint.get('mean_severity', 0):.4f}, micro_ang_sev={best_joint.get('mean_micro_angle_severity', 0):.4f}, "
            f"micro_dist_sev={best_joint.get('mean_micro_dist_severity', 0):.4f}, "
            f"checkpoint={best_joint.get('checkpoint')}\n"
        )
        f.write(
            f"BEST ANGLE (severity) => {best_angle['config'].name}: angle={best_angle['mean_angle']:.4f}, "
            f"angle_sev={best_angle.get('mean_severity', 0):.4f}, joint={best_angle['mean_joint']:.4f}, dist={best_angle['mean_dist']:.4f}, mae={best_angle['mean_mae']:.2f}, "
            f"micro_ang_sev={best_angle.get('mean_micro_angle_severity', 0):.4f}, micro_dist_sev={best_angle.get('mean_micro_dist_severity', 0):.4f}, "
            f"checkpoint={best_angle.get('checkpoint')}\n"
        )
        f.write(
            f"BEST DIST (angle-weighted) => {best_dist['config'].name}: dist={best_dist['mean_dist']:.4f}, "
            f"dist_ang_weighted={best_dist.get('mean_micro_dist_severity', 0):.4f}, joint={best_dist['mean_joint']:.4f}, angle={best_dist['mean_angle']:.4f}, mae={best_dist['mean_mae']:.2f}, "
            f"sev_acc={best_dist.get('mean_severity', 0):.4f}, micro_ang_sev={best_dist.get('mean_micro_angle_severity', 0):.4f}, "
            f"checkpoint={best_dist.get('checkpoint')}\n"
        )

    print(f"[INFO] Results written to {results_path}")
    print(
        f"[INFO] Best joint: {best_joint['config'].name} | joint={best_joint['mean_joint']:.4f} angle={best_joint['mean_angle']:.4f} dist={best_joint['mean_dist']:.4f} "
        f"sev={best_joint.get('mean_severity', 0):.4f} micro_ang_sev={best_joint.get('mean_micro_angle_severity', 0):.4f} micro_dist_sev={best_joint.get('mean_micro_dist_severity', 0):.4f} "
        f"| checkpoint={best_joint.get('checkpoint')} fold={best_joint.get('best_fold')}"
    )
    print(
        f"[INFO] Best angle (severity): {best_angle['config'].name} | angle={best_angle['mean_angle']:.4f} joint={best_angle['mean_joint']:.4f} dist={best_angle['mean_dist']:.4f} "
        f"angle_sev={best_angle.get('mean_severity', 0):.4f} micro_ang_sev={best_angle.get('mean_micro_angle_severity', 0):.4f} micro_dist_sev={best_angle.get('mean_micro_dist_severity', 0):.4f} "
        f"| checkpoint={best_angle.get('checkpoint')} fold={best_angle.get('best_angle_fold') or best_angle.get('best_fold')}"
    )
    print(
        f"[INFO] Best dist (angle-weighted): {best_dist['config'].name} | dist={best_dist['mean_dist']:.4f} joint={best_dist['mean_joint']:.4f} angle={best_dist['mean_angle']:.4f} "
        f"dist_ang_weighted={best_dist.get('mean_micro_dist_severity', 0):.4f} sev={best_dist.get('mean_severity', 0):.4f} "
        f"| checkpoint={best_dist.get('checkpoint')} fold={best_dist.get('best_distw_fold') or best_dist.get('best_fold')}"
    )


if __name__ == "__main__":
    main()
