#!/usr/bin/env python3
"""
run_best_models_perturb_sweep.py

Script completo per testare i due modelli migliori del collega con TUTTE
le perturbazioni audio a 3 livelli di intensità (LOW, MEDIUM, HIGH).

Modelli testati:
  - crnn_mel80_best_angle.pt (migliore per direzione)
  - resnet18_mel96_best_dist_angle_weighted.pt (migliore per distanza)

Perturbazioni testate:
  - Pitch shift (low/medium/high)
  - White noise (low/medium/high)
  - Pink noise (low/medium/high)
  - EQ tilt (low/medium/high)
  - High-pass filter (low/medium/high)
  - Low-pass filter (low/medium/high)
  - Combo: pink+eq, pink+hp (medium/high)

Output:
  - CSV riassuntivo: results/summary_perturbations_best_models.csv
  - Confusion matrix: results/confusion_matrices/ (CSV)

Uso:
    python -m model_classifier.run_best_models_perturb_sweep [--max-samples N]

Autore: Francesco Carcangiu
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.metrics import confusion_matrix
from sklearn.model_selection import train_test_split

# Aggiungi ADV_ML al path per import audio_effects
_ADV_ML_PATH = Path(__file__).resolve().parent.parent.parent / "ADV_ML"
if str(_ADV_ML_PATH) not in sys.path:
    sys.path.insert(0, str(_ADV_ML_PATH))

import audio_effects

# Import da deep_cv del collega
from model_classifier.deep_cv import (
    AUDIO_SR,
    NUM_CHANNELS,
    DEVICE,
    SEED,
    BASE_DIR,
    DIST_NUM_BINS,
    ANGLE_LABELS,
    Config,
    set_seed,
    load_pairs,
    load_labels,
    angle_deg_to_class,
    dist_to_class,
    compute_mel_ipd_ild,
    downsample_wave,
    build_model,
)

# Import utilità perturbazione
from model_classifier.perturbation_utils import (
    apply_perturbation_waveform,
    PERTURB_PRESETS,
)


# ============================================================================
# DEFINIZIONE LIVELLI DI INTENSITÀ (LOW / MEDIUM / HIGH)
# ============================================================================

PERTURBATION_LEVELS = {
    # Pitch shift (cents): dead zone ±75, range tipico ±75..±200
    "pitch_pos": {
        "LOW": {"type": "pitch", "cents": +75.0},
        "MEDIUM": {"type": "pitch", "cents": +150.0},
        "HIGH": {"type": "pitch", "cents": +200.0},
    },
    "pitch_neg": {
        "LOW": {"type": "pitch", "cents": -75.0},
        "MEDIUM": {"type": "pitch", "cents": -150.0},
        "HIGH": {"type": "pitch", "cents": -200.0},
    },
    
    # White noise (SNR in dB): più alto SNR = meno rumore
    "white_noise": {
        "LOW": {"type": "white_noise", "snr_db": 42.0},    # poco rumore
        "MEDIUM": {"type": "white_noise", "snr_db": 40.0},
        "HIGH": {"type": "white_noise", "snr_db": 38.0},   # più rumore
    },
    
    # Pink noise (SNR in dB): più basso SNR = più rumore
    "pink_noise": {
        "LOW": {"type": "pink_noise", "snr_db": 22.0},
        "MEDIUM": {"type": "pink_noise", "snr_db": 20.0},
        "HIGH": {"type": "pink_noise", "snr_db": 18.0},
    },
    
    # EQ tilt boost (dB positivi = brighten)
    "eq_boost": {
        "LOW": {"type": "eq_tilt", "tilt_db": +3.0},
        "MEDIUM": {"type": "eq_tilt", "tilt_db": +4.5},
        "HIGH": {"type": "eq_tilt", "tilt_db": +6.0},
    },
    
    # EQ tilt cut (dB negativi = darken)
    "eq_cut": {
        "LOW": {"type": "eq_tilt", "tilt_db": -3.0},
        "MEDIUM": {"type": "eq_tilt", "tilt_db": -6.0},
        "HIGH": {"type": "eq_tilt", "tilt_db": -9.0},
    },
    
    # High-pass filter (Hz): più alto = più aggressivo
    "highpass": {
        "LOW": {"type": "highpass", "cutoff_hz": 150},
        "MEDIUM": {"type": "highpass", "cutoff_hz": 200},
        "HIGH": {"type": "highpass", "cutoff_hz": 250},
    },
    
    # Low-pass filter (Hz): più basso = più aggressivo
    "lowpass": {
        "LOW": {"type": "lowpass", "cutoff_hz": 12000},
        "MEDIUM": {"type": "lowpass", "cutoff_hz": 10000},
        "HIGH": {"type": "lowpass", "cutoff_hz": 8000},
    },
    
    # ========================================================================
    # NUOVI EFFETTI SPAZIALI (per disturbare IPD/ILD)
    # ========================================================================
    
    # Spatial delay — micro-delay tra canali (disturba IPD)
    "spatial_delay": {
        "LOW": {"type": "spatial_delay", "max_samples": 2},      # ~0.02ms @ 96kHz
        "MEDIUM": {"type": "spatial_delay", "max_samples": 5},   # ~0.05ms @ 96kHz
        "HIGH": {"type": "spatial_delay", "max_samples": 10},    # ~0.1ms @ 96kHz
    },
    
    # Channel gain jitter — variazioni di gain per canale (disturba ILD)
    "gain_jitter": {
        "LOW": {"type": "gain_jitter", "max_db": 0.5},          # Molto sottile
        "MEDIUM": {"type": "gain_jitter", "max_db": 1.0},       # Sottile
        "HIGH": {"type": "gain_jitter", "max_db": 1.5},         # Percettibile
    },
    
    # Multi-channel white noise — rumore indipendente per canale
    "multi_white_noise": {
        "LOW": {"type": "multi_noise", "noise_subtype": "white", "snr_db": 42.0},
        "MEDIUM": {"type": "multi_noise", "noise_subtype": "white", "snr_db": 40.0},
        "HIGH": {"type": "multi_noise", "noise_subtype": "white", "snr_db": 38.0},
    },
    
    # Multi-channel pink noise — rumore indipendente per canale
    "multi_pink_noise": {
        "LOW": {"type": "multi_noise", "noise_subtype": "pink", "snr_db": 22.0},
        "MEDIUM": {"type": "multi_noise", "noise_subtype": "pink", "snr_db": 20.0},
        "HIGH": {"type": "multi_noise", "noise_subtype": "pink", "snr_db": 18.0},
    },
}

# Combo perturbations (applicate in sequenza)
COMBO_PERTURBATIONS = {
    "pink_eq": {
        "MEDIUM": [
            {"type": "pink_noise", "snr_db": 20.0},
            {"type": "eq_tilt", "tilt_db": +4.5},
        ],
        "HIGH": [
            {"type": "pink_noise", "snr_db": 18.0},
            {"type": "eq_tilt", "tilt_db": +6.0},
        ],
    },
    "pink_hp": {
        "MEDIUM": [
            {"type": "pink_noise", "snr_db": 20.0},
            {"type": "highpass", "cutoff_hz": 200},
        ],
        "HIGH": [
            {"type": "pink_noise", "snr_db": 18.0},
            {"type": "highpass", "cutoff_hz": 250},
        ],
    },
    # Nuove combo con effetti spaziali
    "spatial_gain": {
        "MEDIUM": [
            {"type": "spatial_delay", "max_samples": 5},
            {"type": "gain_jitter", "max_db": 1.0},
        ],
        "HIGH": [
            {"type": "spatial_delay", "max_samples": 10},
            {"type": "gain_jitter", "max_db": 1.5},
        ],
    },
    "multi_pink_spatial": {
        "MEDIUM": [
            {"type": "multi_noise", "noise_subtype": "pink", "snr_db": 20.0},
            {"type": "spatial_delay", "max_samples": 5},
        ],
        "HIGH": [
            {"type": "multi_noise", "noise_subtype": "pink", "snr_db": 18.0},
            {"type": "spatial_delay", "max_samples": 10},
        ],
    },
}


def apply_combo_perturbation(waveform: np.ndarray, sr: int, combo_list: List[Dict]) -> np.ndarray:
    """Applica sequenza di perturbazioni."""
    result = waveform.copy()
    for config in combo_list:
        pert_type = config["type"]
        
        if pert_type == "pitch":
            result = audio_effects.apply_pitch_shift(result, sr, config["cents"])
        elif pert_type == "white_noise":
            result = audio_effects.add_white_noise(result, config["snr_db"])
        elif pert_type == "pink_noise":
            result = audio_effects.add_pink_noise(result, config["snr_db"])
        elif pert_type == "eq_tilt":
            result = audio_effects.apply_eq_tilt(result, sr, config["tilt_db"])
        elif pert_type == "highpass":
            result = audio_effects.apply_highpass(result, sr, config["cutoff_hz"])
        elif pert_type == "lowpass":
            result = audio_effects.apply_lowpass(result, sr, config["cutoff_hz"])
        elif pert_type == "spatial_delay":
            result = audio_effects.apply_spatial_delay(result, sr, config["max_samples"])
        elif pert_type == "gain_jitter":
            result = audio_effects.apply_channel_gain_jitter(result, config["max_db"])
        elif pert_type == "multi_noise":
            noise_subtype = config.get("noise_subtype", "white")
            result = audio_effects.apply_multi_channel_noise(result, config["snr_db"], noise_subtype)
    
    return result


# ============================================================================
# DATASET CON PERTURBAZIONE
# ============================================================================

class AudioFeatureDatasetBestModels(torch.utils.data.Dataset):
    """
    Dataset per testare i modelli migliori con perturbazioni.
    """
    def __init__(
        self,
        pairs: List[Tuple[Path, Path]],
        feature_type: str,
        feature_cfg: dict,
        dist_thresholds: Tuple[float, ...],
        dist_bins: int,
        perturbation_config: Dict | None = None,
        is_combo: bool = False,
    ):
        self.pairs = pairs
        self.feature_type = feature_type
        self.feature_cfg = feature_cfg
        self.dist_thresholds = dist_thresholds
        self.dist_bins = dist_bins
        self.perturbation_config = perturbation_config
        self.is_combo = is_combo

    def __len__(self) -> int:
        return len(self.pairs)

    def __getitem__(self, idx: int):
        audio_path, label_path = self.pairs[idx]
        angle_deg, dist_rel = load_labels(label_path)
        
        # Carica audio CSV (waveform)
        audio_mat = pd.read_csv(audio_path, dtype=np.float32, engine="c").values
        if audio_mat.ndim != 2 or audio_mat.shape[1] != NUM_CHANNELS:
            raise ValueError(f"Invalid audio shape in {audio_path}")
        
        # Applica perturbazione
        if self.perturbation_config is not None:
            if self.is_combo:
                # Combo: lista di perturbazioni
                audio_mat = apply_combo_perturbation(audio_mat, AUDIO_SR, self.perturbation_config)
            else:
                # Singola perturbazione
                pert_type = self.perturbation_config["type"]
                
                if pert_type == "pitch":
                    audio_mat = audio_effects.apply_pitch_shift(audio_mat, AUDIO_SR, self.perturbation_config["cents"])
                elif pert_type == "white_noise":
                    audio_mat = audio_effects.add_white_noise(audio_mat, self.perturbation_config["snr_db"])
                elif pert_type == "pink_noise":
                    audio_mat = audio_effects.add_pink_noise(audio_mat, self.perturbation_config["snr_db"])
                elif pert_type == "eq_tilt":
                    audio_mat = audio_effects.apply_eq_tilt(audio_mat, AUDIO_SR, self.perturbation_config["tilt_db"])
                elif pert_type == "highpass":
                    audio_mat = audio_effects.apply_highpass(audio_mat, AUDIO_SR, self.perturbation_config["cutoff_hz"])
                elif pert_type == "lowpass":
                    audio_mat = audio_effects.apply_lowpass(audio_mat, AUDIO_SR, self.perturbation_config["cutoff_hz"])
                elif pert_type == "spatial_delay":
                    audio_mat = audio_effects.apply_spatial_delay(audio_mat, AUDIO_SR, self.perturbation_config["max_samples"])
                elif pert_type == "gain_jitter":
                    audio_mat = audio_effects.apply_channel_gain_jitter(audio_mat, self.perturbation_config["max_db"])
                elif pert_type == "multi_noise":
                    noise_subtype = self.perturbation_config.get("noise_subtype", "white")
                    audio_mat = audio_effects.apply_multi_channel_noise(audio_mat, self.perturbation_config["snr_db"], noise_subtype)
        
        # Feature extraction
        if self.feature_type == "mel_ipd":
            feats = compute_mel_ipd_ild(
                audio_mat,
                sr=AUDIO_SR,
                n_mels=self.feature_cfg["n_mels"],
                n_fft=self.feature_cfg["n_fft"],
                hop_length=self.feature_cfg["hop_length"],
                ref_ch=0,
            )
            feats_tensor = torch.from_numpy(feats)
        elif self.feature_type == "raw1d":
            dsr = self.feature_cfg["target_sr"]
            audio_ds = downsample_wave(audio_mat, dsr)
            feats_tensor = torch.from_numpy(audio_ds.T)
        else:
            raise ValueError(f"Unknown feature type {self.feature_type}")

        # Converti labels
        angle_cls = angle_deg_to_class(np.array([angle_deg], dtype=np.float32))[0]
        dist_cls, _ = dist_to_class(
            np.array([dist_rel], dtype=np.float32),
            thresholds=self.dist_thresholds,
            num_bins=self.dist_bins,
        )
        dist_cls = dist_cls[0]
        ang_vec = torch.tensor(
            [math.sin(math.radians(angle_deg)), math.cos(math.radians(angle_deg))],
            dtype=torch.float32
        )

        return feats_tensor, angle_cls, dist_cls, ang_vec


# ============================================================================
# VALUTAZIONE CON METRICHE + CONFUSION MATRIX
# ============================================================================

def evaluate_with_confusion_matrix(
    model: nn.Module,
    loader: torch.utils.data.DataLoader,
    device: torch.device,
) -> Dict:
    """
    Valuta modello e calcola confusion matrix.
    
    Returns:
        Dict con metriche + confusion matrices
    """
    model.eval()
    
    all_angle_preds = []
    all_angle_true = []
    all_dist_preds = []
    all_dist_true = []
    all_angle_mae = []
    
    with torch.no_grad():
        for feats, angle_cls, dist_cls, ang_vec in loader:
            feats = feats.to(device)
            angle_cls = angle_cls.to(device)
            dist_cls = dist_cls.to(device)
            ang_vec = ang_vec.to(device)
            
            # Forward pass
            angle_logits, dist_logits, vec_pred = model(feats)
            
            # Predictions
            angle_pred = torch.argmax(angle_logits, dim=1)
            dist_pred = torch.argmax(dist_logits, dim=1)
            
            # Accumula
            all_angle_preds.extend(angle_pred.cpu().numpy())
            all_angle_true.extend(angle_cls.cpu().numpy())
            all_dist_preds.extend(dist_pred.cpu().numpy())
            all_dist_true.extend(dist_cls.cpu().numpy())
            
            # Calcola MAE angolare
            # Converti predizione in gradi
            # ANGLE_LABELS = ["n", "w", "s", "e"] -> [0°, 270°, 180°, 90°]
            angle_to_deg = {0: 0.0, 1: 270.0, 2: 180.0, 3: 90.0}  # n, w, s, e
            
            pred_angles = []
            true_angles = []
            for i in range(len(angle_pred)):
                pred_cls = angle_pred[i].item()
                true_cls = angle_cls[i].item()
                pred_angle = angle_to_deg[pred_cls]
                true_angle = angle_to_deg[true_cls]
                pred_angles.append(pred_angle)
                true_angles.append(true_angle)
            
            # MAE con wraparound
            for pred_ang, true_ang in zip(pred_angles, true_angles):
                diff = abs(pred_ang - true_ang)
                if diff > 180:
                    diff = 360 - diff
                all_angle_mae.append(diff)
    
    # Converti a numpy
    all_angle_preds = np.array(all_angle_preds)
    all_angle_true = np.array(all_angle_true)
    all_dist_preds = np.array(all_dist_preds)
    all_dist_true = np.array(all_dist_true)
    
    # Metriche
    angle_acc = np.mean(all_angle_preds == all_angle_true)
    dist_acc = np.mean(all_dist_preds == all_dist_true)
    joint_acc = np.mean((all_angle_preds == all_angle_true) & (all_dist_preds == all_dist_true))
    angle_mae = np.mean(all_angle_mae)
    
    # Confusion matrices
    cm_angle = confusion_matrix(all_angle_true, all_angle_preds, labels=range(len(ANGLE_LABELS)))
    cm_dist = confusion_matrix(all_dist_true, all_dist_preds, labels=range(DIST_NUM_BINS))
    
    return {
        "angle_acc": angle_acc,
        "dist_acc": dist_acc,
        "joint_acc": joint_acc,
        "angle_mae": angle_mae,
        "cm_angle": cm_angle,
        "cm_dist": cm_dist,
        "n_samples": len(all_angle_true),
    }


# ============================================================================
# CARICAMENTO MODELLI BEST
# ============================================================================

def load_best_model(model_name: str, checkpoint_dir: Path) -> Tuple[nn.Module, str, dict]:
    """
    Carica uno dei due modelli migliori.
    
    Args:
        model_name: "crnn_angle" o "resnet_dist"
        checkpoint_dir: Cartella con checkpoint
    
    Returns:
        (model, feature_type, feature_cfg)
    """
    if model_name == "crnn_angle":
        checkpoint_path = checkpoint_dir / "crnn_mel80_best_angle.pt"
    elif model_name == "resnet_dist":
        checkpoint_path = checkpoint_dir / "resnet18_mel96_best_dist_angle_weighted.pt"
    else:
        raise ValueError(f"Unknown model: {model_name}")
    
    if not checkpoint_path.exists():
        raise FileNotFoundError(f"Checkpoint non trovato: {checkpoint_path}")
    
    # Carica checkpoint per recuperare config
    checkpoint = torch.load(checkpoint_path, map_location=DEVICE, weights_only=False)
    
    # Recupera config dal checkpoint
    if 'config' in checkpoint:
        config = checkpoint['config']
        feature_type = config.feature_type
        feature_cfg = config.feature_cfg
    else:
        # Fallback: usa config di default
        if model_name == "crnn_angle":
            feature_type = "mel_ipd"
            feature_cfg = {"n_mels": 80, "n_fft": 2048, "hop_length": 960}
            model_cfg = {"hidden": 160, "dropout": 0.2}
            config_name = "crnn_mel80"
            config = Config(
                name=config_name,
                feature_type=feature_type,
                feature_cfg=feature_cfg,
                model_cfg=model_cfg,
            )
        elif model_name == "resnet_dist":
            feature_type = "mel_ipd"
            feature_cfg = {"n_mels": 96, "n_fft": 2048, "hop_length": 1024}
            model_cfg = {"dropout": 0.25}
            config_name = "resnet18_mel96"
            config = Config(
                name=config_name,
                feature_type=feature_type,
                feature_cfg=feature_cfg,
                model_cfg=model_cfg,
            )
    
    # Determina input channels
    # Crea sample dataset per inferire shape
    pairs = load_pairs()
    sample_ds = AudioFeatureDatasetBestModels(
        pairs[:1], feature_type, feature_cfg, (28.4, 51.6), DIST_NUM_BINS, None
    )
    sample_feats, _, _, _ = sample_ds[0]
    in_ch = sample_feats.shape[0]
    
    # Build model
    model = build_model(
        config, in_ch=in_ch,
        angle_classes=len(ANGLE_LABELS), dist_classes=DIST_NUM_BINS
    ).to(DEVICE)
    
    # Carica state_dict dal checkpoint già caricato
    if isinstance(checkpoint, dict):
        # Checkpoint è un dizionario, prova diverse chiavi
        if 'model_state' in checkpoint:
            model.load_state_dict(checkpoint['model_state'])
        elif 'model_state_dict' in checkpoint:
            model.load_state_dict(checkpoint['model_state_dict'])
        elif 'state_dict' in checkpoint:
            model.load_state_dict(checkpoint['state_dict'])
        elif 'model' in checkpoint:
            model.load_state_dict(checkpoint['model'])
        else:
            # Assume che il dict sia direttamente lo state_dict
            model.load_state_dict(checkpoint)
    else:
        # Checkpoint è direttamente il modello o lo state_dict
        try:
            model.load_state_dict(checkpoint)
        except:
            # Se fallisce, potrebbe essere il modello stesso
            model = checkpoint.to(DEVICE)
    
    print(f"✅ Caricato modello: {checkpoint_path.name}")
    print(f"   Feature type: {feature_type}, cfg: {feature_cfg}")
    
    return model, feature_type, feature_cfg


# ============================================================================
# MAIN SWEEP
# ============================================================================

def run_perturbation_sweep(max_samples: int | None = None):
    """
    Esegue sweep completo su tutti i modelli e perturbazioni.
    """
    set_seed(SEED)
    
    print("="*80)
    print("SWEEP PERTURBAZIONI SU MODELLI MIGLIORI")
    print("="*80)
    print(f"Max samples per test: {max_samples if max_samples else 'tutti'}")
    print(f"Device: {DEVICE}")
    print("="*80 + "\n")
    
    # Carica dataset e crea test split
    print("[1/4] Caricamento dataset...")
    pairs = load_pairs()
    
    # Estrai labels per discretizzazione
    angles = []
    dists = []
    for _, label_path in pairs:
        ang, dist = load_labels(label_path)
        angles.append(ang)
        dists.append(dist)
    angles = np.array(angles, dtype=np.float32)
    dists = np.array(dists, dtype=np.float32)
    angle_classes = angle_deg_to_class(angles)
    dist_classes, dist_thresholds = dist_to_class(dists, num_bins=DIST_NUM_BINS)
    
    # Split train/test (80/20) con stratificazione
    joint_classes = angle_classes * DIST_NUM_BINS + dist_classes
    indices = np.arange(len(pairs))
    _, test_indices = train_test_split(
        indices, test_size=0.2, random_state=SEED, stratify=joint_classes
    )
    
    test_pairs = [pairs[i] for i in test_indices]
    
    # Limita se richiesto
    if max_samples and max_samples < len(test_pairs):
        np.random.seed(SEED)
        test_indices_sub = np.random.choice(len(test_pairs), max_samples, replace=False)
        test_pairs = [test_pairs[i] for i in test_indices_sub]
    
    print(f"   → Test set: {len(test_pairs)} campioni")
    print(f"   → Dist thresholds: {dist_thresholds}\n")
    
    # Prepara output
    results_dir = BASE_DIR / "model_classifier" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    
    cm_dir = results_dir / "confusion_matrices"
    cm_dir.mkdir(parents=True, exist_ok=True)
    
    checkpoint_dir = BASE_DIR / "model_classifier" / "checkpoints"
    
    # Lista modelli da testare
    models_to_test = [
        ("crnn_angle", "CRNN MEL80 (best angle)"),
        ("resnet_dist", "ResNet18 MEL96 (best dist+angle weighted)"),
    ]
    
    all_results = []
    
    # Loop sui modelli
    for model_key, model_desc in models_to_test:
        print(f"\n{'='*80}")
        print(f"[2/4] Testando modello: {model_desc}")
        print(f"{'='*80}\n")
        
        model, feature_type, feature_cfg = load_best_model(model_key, checkpoint_dir)
        
        # Baseline (no perturbation)
        print(f"\n   → Baseline (no perturbation)...")
        test_ds_baseline = AudioFeatureDatasetBestModels(
            test_pairs, feature_type, feature_cfg, dist_thresholds, DIST_NUM_BINS, None
        )
        test_loader_baseline = torch.utils.data.DataLoader(
            test_ds_baseline, batch_size=8, shuffle=False, num_workers=0
        )
        
        metrics_baseline = evaluate_with_confusion_matrix(model, test_loader_baseline, DEVICE)
        
        print(f"      Baseline: angle_acc={metrics_baseline['angle_acc']:.4f}, "
              f"dist_acc={metrics_baseline['dist_acc']:.4f}, "
              f"joint_acc={metrics_baseline['joint_acc']:.4f}, "
              f"MAE={metrics_baseline['angle_mae']:.2f}°")
        
        # Salva confusion matrix baseline
        cm_angle_base_path = cm_dir / f"{model_key}_baseline_cm_angle.csv"
        cm_dist_base_path = cm_dir / f"{model_key}_baseline_cm_dist.csv"
        pd.DataFrame(metrics_baseline['cm_angle']).to_csv(cm_angle_base_path, index=False)
        pd.DataFrame(metrics_baseline['cm_dist']).to_csv(cm_dist_base_path, index=False)
        
        # Loop sulle perturbazioni singole
        print(f"\n[3/4] Testando perturbazioni singole...")
        for pert_name, levels in PERTURBATION_LEVELS.items():
            print(f"\n   → Perturbazione: {pert_name}")
            
            for level_name, pert_config in levels.items():
                print(f"      Livello: {level_name} - {pert_config}")
                
                # Crea dataset perturbato
                test_ds_pert = AudioFeatureDatasetBestModels(
                    test_pairs, feature_type, feature_cfg, dist_thresholds, DIST_NUM_BINS,
                    pert_config, is_combo=False
                )
                test_loader_pert = torch.utils.data.DataLoader(
                    test_ds_pert, batch_size=8, shuffle=False, num_workers=0
                )
                
                # Valuta
                metrics_pert = evaluate_with_confusion_matrix(model, test_loader_pert, DEVICE)
                
                # Calcola drop
                angle_drop = metrics_baseline['angle_acc'] - metrics_pert['angle_acc']
                dist_drop = metrics_baseline['dist_acc'] - metrics_pert['dist_acc']
                joint_drop = metrics_baseline['joint_acc'] - metrics_pert['joint_acc']
                mae_increase = metrics_pert['angle_mae'] - metrics_baseline['angle_mae']
                
                print(f"         Pert: angle_acc={metrics_pert['angle_acc']:.4f} (drop={angle_drop:+.4f}), "
                      f"joint_acc={metrics_pert['joint_acc']:.4f} (drop={joint_drop:+.4f}), "
                      f"MAE={metrics_pert['angle_mae']:.2f}° (+{mae_increase:.2f}°)")
                
                # Salva confusion matrix
                cm_angle_path = cm_dir / f"{model_key}_{pert_name}_{level_name}_cm_angle.csv"
                cm_dist_path = cm_dir / f"{model_key}_{pert_name}_{level_name}_cm_dist.csv"
                pd.DataFrame(metrics_pert['cm_angle']).to_csv(cm_angle_path, index=False)
                pd.DataFrame(metrics_pert['cm_dist']).to_csv(cm_dist_path, index=False)
                
                # Aggiungi a risultati
                all_results.append({
                    "model": model_key,
                    "model_desc": model_desc,
                    "perturbation": pert_name,
                    "level": level_name,
                    "config": str(pert_config),
                    "n_test": metrics_pert['n_samples'],
                    "angle_base": metrics_baseline['angle_acc'],
                    "angle_pert": metrics_pert['angle_acc'],
                    "angle_drop": angle_drop,
                    "dist_base": metrics_baseline['dist_acc'],
                    "dist_pert": metrics_pert['dist_acc'],
                    "dist_drop": dist_drop,
                    "joint_base": metrics_baseline['joint_acc'],
                    "joint_pert": metrics_pert['joint_acc'],
                    "joint_drop": joint_drop,
                    "mae_base": metrics_baseline['angle_mae'],
                    "mae_pert": metrics_pert['angle_mae'],
                    "mae_increase": mae_increase,
                })
        
        # Loop sulle combo
        print(f"\n[4/4] Testando perturbazioni combo...")
        for combo_name, levels in COMBO_PERTURBATIONS.items():
            print(f"\n   → Combo: {combo_name}")
            
            for level_name, combo_list in levels.items():
                print(f"      Livello: {level_name} - {combo_list}")
                
                # Crea dataset perturbato
                test_ds_pert = AudioFeatureDatasetBestModels(
                    test_pairs, feature_type, feature_cfg, dist_thresholds, DIST_NUM_BINS,
                    combo_list, is_combo=True
                )
                test_loader_pert = torch.utils.data.DataLoader(
                    test_ds_pert, batch_size=8, shuffle=False, num_workers=0
                )
                
                # Valuta
                metrics_pert = evaluate_with_confusion_matrix(model, test_loader_pert, DEVICE)
                
                # Calcola drop
                angle_drop = metrics_baseline['angle_acc'] - metrics_pert['angle_acc']
                dist_drop = metrics_baseline['dist_acc'] - metrics_pert['dist_acc']
                joint_drop = metrics_baseline['joint_acc'] - metrics_pert['joint_acc']
                mae_increase = metrics_pert['angle_mae'] - metrics_baseline['angle_mae']
                
                print(f"         Pert: angle_acc={metrics_pert['angle_acc']:.4f} (drop={angle_drop:+.4f}), "
                      f"joint_acc={metrics_pert['joint_acc']:.4f} (drop={joint_drop:+.4f}), "
                      f"MAE={metrics_pert['angle_mae']:.2f}° (+{mae_increase:.2f}°)")
                
                # Salva confusion matrix
                cm_angle_path = cm_dir / f"{model_key}_combo_{combo_name}_{level_name}_cm_angle.csv"
                cm_dist_path = cm_dir / f"{model_key}_combo_{combo_name}_{level_name}_cm_dist.csv"
                pd.DataFrame(metrics_pert['cm_angle']).to_csv(cm_angle_path, index=False)
                pd.DataFrame(metrics_pert['cm_dist']).to_csv(cm_dist_path, index=False)
                
                # Aggiungi a risultati
                all_results.append({
                    "model": model_key,
                    "model_desc": model_desc,
                    "perturbation": f"combo_{combo_name}",
                    "level": level_name,
                    "config": str(combo_list),
                    "n_test": metrics_pert['n_samples'],
                    "angle_base": metrics_baseline['angle_acc'],
                    "angle_pert": metrics_pert['angle_acc'],
                    "angle_drop": angle_drop,
                    "dist_base": metrics_baseline['dist_acc'],
                    "dist_pert": metrics_pert['dist_acc'],
                    "dist_drop": dist_drop,
                    "joint_base": metrics_baseline['joint_acc'],
                    "joint_pert": metrics_pert['joint_acc'],
                    "joint_drop": joint_drop,
                    "mae_base": metrics_baseline['angle_mae'],
                    "mae_pert": metrics_pert['angle_mae'],
                    "mae_increase": mae_increase,
                })
    
    # Salva CSV riassuntivo
    csv_path = results_dir / "summary_perturbations_best_models.csv"
    fieldnames = [
        "model", "model_desc", "perturbation", "level", "config", "n_test",
        "angle_base", "angle_pert", "angle_drop",
        "dist_base", "dist_pert", "dist_drop",
        "joint_base", "joint_pert", "joint_drop",
        "mae_base", "mae_pert", "mae_increase",
    ]
    
    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_results)
    
    print(f"\n{'='*80}")
    print(f"SWEEP COMPLETATO!")
    print(f"{'='*80}")
    print(f"Risultati salvati in:")
    print(f"  - CSV riassuntivo: {csv_path}")
    print(f"  - Confusion matrices: {cm_dir}/")
    print(f"\nTotale righe CSV: {len(all_results)}")
    print(f"{'='*80}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Sweep completo perturbazioni su modelli migliori"
    )
    parser.add_argument(
        "--max-samples",
        type=int,
        default=None,
        help="Limita numero sample test set (default: tutti, circa 194 = 20%% di 970)"
    )
    
    args = parser.parse_args()
    
    run_perturbation_sweep(max_samples=args.max_samples)


if __name__ == "__main__":
    main()

