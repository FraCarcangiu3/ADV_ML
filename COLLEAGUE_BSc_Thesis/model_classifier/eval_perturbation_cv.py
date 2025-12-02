#!/usr/bin/env python3
"""
eval_perturbation_cv.py

Valutazione con perturbazione audio su 9-fold cross-validation.
Carica checkpoint addestrati da deep_cv.py e valuta baseline vs perturbato.

Uso:
    python -m model_classifier.eval_perturbation_cv \
        --model resnet18_mel96 \
        --perturb-preset pitch_P2_pos \
        --results-csv results/perturb_pitch_P2_pos.csv

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
import torch.nn.functional as F
from sklearn.model_selection import StratifiedKFold

# Import da deep_cv del collega
from model_classifier.deep_cv import (
    AUDIO_SR,
    NUM_CHANNELS,
    DEVICE,
    SEED,
    BASE_DIR,
    DIST_NUM_BINS,
    ANGLE_LABELS,
    DESIRED_FOLDS,
    Config,
    set_seed,
    load_pairs,
    load_labels,
    angle_deg_to_class,
    dist_to_class,
    get_distance_labels,
    compute_mel_ipd_ild,
    downsample_wave,
    ResNet18MT,
    CRNN,
    Conv1DSeparable,
    build_model,
    evaluate,
)

# Import utilità perturbazione
from model_classifier.perturbation_utils import (
    apply_perturbation_waveform,
    get_preset_config,
)


# ============================================================================
# DATASET CON PERTURBAZIONE
# ============================================================================

class AudioFeatureDatasetWithPerturbation(torch.utils.data.Dataset):
    """
    Dataset che applica perturbazione al waveform PRIMA della feature extraction.
    Basato su AudioFeatureDataset di deep_cv.py.
    """
    def __init__(
        self,
        pairs: List[Tuple[Path, Path]],
        feature_type: str,
        feature_cfg: dict,
        dist_thresholds: Tuple[float, ...],
        dist_bins: int,
        perturbation_config: Dict | None = None,
    ):
        self.pairs = pairs
        self.feature_type = feature_type
        self.feature_cfg = feature_cfg
        self.dist_thresholds = dist_thresholds
        self.dist_bins = dist_bins
        self.perturbation_config = perturbation_config

    def __len__(self) -> int:
        return len(self.pairs)

    def __getitem__(self, idx: int):
        audio_path, label_path = self.pairs[idx]
        angle_deg, dist_rel = load_labels(label_path)
        
        # Carica audio CSV (waveform)
        audio_mat = pd.read_csv(audio_path, dtype=np.float32, engine="c").values
        if audio_mat.ndim != 2 or audio_mat.shape[1] != NUM_CHANNELS:
            raise ValueError(f"Invalid audio shape in {audio_path}")
        
        # ===== PUNTO DI PERTURBAZIONE =====
        # Applica perturbazione al waveform PRIMA della feature extraction
        if self.perturbation_config is not None:
            preset_name = self.perturbation_config.get("preset_name", "")
            if preset_name:
                audio_mat = apply_perturbation_waveform(audio_mat, AUDIO_SR, preset_name)
        
        # Feature extraction (come in deep_cv.py)
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

        # Converti labels in classi
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
# VALUTAZIONE CON PERTURBAZIONE SU 9-FOLD CV
# ============================================================================

def eval_perturbation_cv(
    model_name: str,
    perturb_preset: str,
    results_csv: Path | None = None,
    max_samples: int | None = None,
):
    """
    Valuta modello con perturbazione su 9-fold CV.
    
    Args:
        model_name: Nome modello (resnet18_mel96, crnn_mel80, conv1d_sep_ds48k)
        perturb_preset: Nome preset perturbazione (es. 'pitch_P2_pos')
        results_csv: Path CSV output (None = auto-genera nome)
        max_samples: Limita numero sample (None = tutti)
    """
    set_seed(SEED)
    
    print(f"\n{'='*70}")
    print(f"VALUTAZIONE CON PERTURBAZIONE SU 9-FOLD CV")
    print(f"{'='*70}")
    print(f"Modello: {model_name}")
    print(f"Perturbazione: {perturb_preset}")
    print(f"Max samples: {max_samples if max_samples else 'tutti'}")
    print(f"Device: {DEVICE}")
    print(f"{'='*70}\n")
    
    # Carica dataset
    print("[1/5] Caricamento dataset...")
    pairs = load_pairs()
    
    if max_samples and max_samples < len(pairs):
        np.random.seed(SEED)
        indices = np.random.choice(len(pairs), max_samples, replace=False)
        pairs = [pairs[i] for i in indices]
        print(f"      → Limitato a {len(pairs)} sample casuali")
    
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
    
    print(f"      → Caricati {len(pairs)} campioni")
    print(f"      → Angle bins: {len(ANGLE_LABELS)}, Dist bins: {DIST_NUM_BINS}")
    print(f"      → Dist thresholds: {dist_thresholds}")
    
    # Configurazione modello
    print(f"\n[2/5] Configurazione modello {model_name}...")
    if model_name == "resnet18_mel96":
        feature_type = "mel_ipd"
        feature_cfg = {"n_mels": 96, "n_fft": 2048, "hop_length": 1024}
        model_cfg = {"dropout": 0.25}
    elif model_name == "crnn_mel80":
        feature_type = "mel_ipd"
        feature_cfg = {"n_mels": 80, "n_fft": 2048, "hop_length": 960}
        model_cfg = {"hidden": 160, "dropout": 0.2}
    elif model_name == "conv1d_sep_ds48k":
        feature_type = "raw1d"
        feature_cfg = {"target_sr": 48_000}
        model_cfg = {"dropout": 0.12}
    else:
        raise ValueError(f"Modello sconosciuto: {model_name}")
    
    # Configurazione perturbazione
    print(f"\n[3/5] Configurazione perturbazione {perturb_preset}...")
    try:
        preset_config = get_preset_config(perturb_preset)
        perturbation_config = {"preset_name": perturb_preset, **preset_config}
        print(f"      → Tipo: {preset_config['type']}")
        print(f"      → Parametri: {preset_config}")
    except ValueError as e:
        print(f"[ERROR] {e}")
        return
    
    # 9-fold CV (stesso split del training)
    print(f"\n[4/5] 9-fold Cross-Validation...")
    joint_classes = angle_classes * DIST_NUM_BINS + dist_classes
    skf = StratifiedKFold(n_splits=DESIRED_FOLDS, shuffle=True, random_state=SEED)
    
    checkpoint_dir = BASE_DIR / "model_classifier" / "checkpoints"
    results: List[Dict] = []
    
    for fold_idx, (train_idx, val_idx) in enumerate(skf.split(pairs, joint_classes), start=1):
        print(f"\n      Fold {fold_idx}/{DESIRED_FOLDS}...")
        val_pairs = [pairs[i] for i in val_idx]
        
        # Carica checkpoint per questo fold
        checkpoint_path = checkpoint_dir / f"{model_name}_fold{fold_idx}.pth"
        if not checkpoint_path.exists():
            print(f"      ⚠️  Checkpoint non trovato: {checkpoint_path}")
            print(f"      → Salta questo fold. Esegui prima: python -m model_classifier.deep_cv")
            continue
        
        checkpoint = torch.load(checkpoint_path, map_location=DEVICE, weights_only=False)
        
        # Crea modello
        sample_ds = AudioFeatureDatasetWithPerturbation(
            val_pairs[:1], feature_type, feature_cfg, dist_thresholds, DIST_NUM_BINS, None
        )
        sample_feats, _, _, _ = sample_ds[0]
        in_ch = sample_feats.shape[0] if feature_type == "mel_ipd" else NUM_CHANNELS
        
        model = build_model(
            checkpoint['config'], in_ch=in_ch,
            angle_classes=len(ANGLE_LABELS), dist_classes=DIST_NUM_BINS
        ).to(DEVICE)
        model.load_state_dict(checkpoint['model_state_dict'])
        
        # Dataset baseline (senza perturbazione)
        val_ds_baseline = AudioFeatureDatasetWithPerturbation(
            val_pairs, feature_type, feature_cfg, dist_thresholds, DIST_NUM_BINS, None
        )
        val_loader_baseline = torch.utils.data.DataLoader(
            val_ds_baseline, batch_size=8, shuffle=False, num_workers=0
        )
        
        # Dataset perturbato
        val_ds_pert = AudioFeatureDatasetWithPerturbation(
            val_pairs, feature_type, feature_cfg, dist_thresholds, DIST_NUM_BINS, perturbation_config
        )
        val_loader_pert = torch.utils.data.DataLoader(
            val_ds_pert, batch_size=8, shuffle=False, num_workers=0
        )
        
        # Valutazione baseline
        metrics_baseline = evaluate(model, val_loader_baseline, DEVICE, collect_preds=False)
        
        # Valutazione perturbata
        metrics_pert = evaluate(model, val_loader_pert, DEVICE, collect_preds=False)
        
        # Calcola degradazione
        dir_drop = metrics_baseline['angle_acc'] - metrics_pert['angle_acc']
        dist_drop = metrics_baseline['dist_acc'] - metrics_pert['dist_acc']
        joint_drop = metrics_baseline['joint_acc'] - metrics_pert['joint_acc']
        mae_increase = metrics_pert['angle_mae'] - metrics_baseline['angle_mae']
        
        print(f"        Baseline:  angle={metrics_baseline['angle_acc']:.4f}, "
              f"dist={metrics_baseline['dist_acc']:.4f}, joint={metrics_baseline['joint_acc']:.4f}")
        print(f"        Perturbato: angle={metrics_pert['angle_acc']:.4f}, "
              f"dist={metrics_pert['dist_acc']:.4f}, joint={metrics_pert['joint_acc']:.4f}")
        print(f"        Drop:       angle={dir_drop:+.4f}, dist={dist_drop:+.4f}, joint={joint_drop:+.4f}")
        
        results.append({
            'fold': fold_idx,
            'preset': perturb_preset,
            'n_test': len(val_pairs),
            'angle_base': metrics_baseline['angle_acc'],
            'angle_pert': metrics_pert['angle_acc'],
            'angle_drop': dir_drop,
            'dist_base': metrics_baseline['dist_acc'],
            'dist_pert': metrics_pert['dist_acc'],
            'dist_drop': dist_drop,
            'joint_base': metrics_baseline['joint_acc'],
            'joint_pert': metrics_pert['joint_acc'],
            'joint_drop': joint_drop,
            'mae_base': metrics_baseline['angle_mae'],
            'mae_pert': metrics_pert['angle_mae'],
            'mae_increase': mae_increase,
        })
    
    if not results:
        print("\n[ERROR] Nessun risultato disponibile. Verifica che i checkpoint esistano.")
        return
    
    # Calcola medie
    print(f"\n[5/5] Calcolo medie su {len(results)} fold...")
    mean_results = {
        'fold': 'mean',
        'preset': perturb_preset,
        'n_test': int(np.mean([r['n_test'] for r in results])),
        'angle_base': float(np.mean([r['angle_base'] for r in results])),
        'angle_pert': float(np.mean([r['angle_pert'] for r in results])),
        'angle_drop': float(np.mean([r['angle_drop'] for r in results])),
        'dist_base': float(np.mean([r['dist_base'] for r in results])),
        'dist_pert': float(np.mean([r['dist_pert'] for r in results])),
        'dist_drop': float(np.mean([r['dist_drop'] for r in results])),
        'joint_base': float(np.mean([r['joint_base'] for r in results])),
        'joint_pert': float(np.mean([r['joint_pert'] for r in results])),
        'joint_drop': float(np.mean([r['joint_drop'] for r in results])),
        'mae_base': float(np.mean([r['mae_base'] for r in results])),
        'mae_pert': float(np.mean([r['mae_pert'] for r in results])),
        'mae_increase': float(np.mean([r['mae_increase'] for r in results])),
    }
    
    print(f"\n{'='*70}")
    print(f"RISULTATI AGGREGATI")
    print(f"{'='*70}")
    print(f"Baseline (media):")
    print(f"  Direction accuracy: {mean_results['angle_base']:.4f}")
    print(f"  Distance accuracy:  {mean_results['dist_base']:.4f}")
    print(f"  Joint accuracy:     {mean_results['joint_base']:.4f}")
    print(f"  Angle MAE:          {mean_results['mae_base']:.2f}°")
    print(f"\nCon perturbazione {perturb_preset} (media):")
    print(f"  Direction accuracy: {mean_results['angle_pert']:.4f}")
    print(f"  Distance accuracy:  {mean_results['dist_pert']:.4f}")
    print(f"  Joint accuracy:     {mean_results['joint_pert']:.4f}")
    print(f"  Angle MAE:          {mean_results['mae_pert']:.2f}°")
    print(f"\nDegradazione (media):")
    print(f"  Direction: {mean_results['angle_drop']:+.4f}")
    print(f"  Distance:  {mean_results['dist_drop']:+.4f}")
    print(f"  Joint:     {mean_results['joint_drop']:+.4f}")
    print(f"  Angle MAE: {mean_results['mae_increase']:+.2f}°")
    print(f"{'='*70}\n")
    
    # Salva CSV
    if results_csv is None:
        results_csv = BASE_DIR / "model_classifier" / f"perturbation_cv_{perturb_preset}.csv"
    else:
        results_csv = Path(results_csv)
        results_csv.parent.mkdir(parents=True, exist_ok=True)
    
    fieldnames = [
        'fold', 'preset', 'n_test',
        'angle_base', 'angle_pert', 'angle_drop',
        'dist_base', 'dist_pert', 'dist_drop',
        'joint_base', 'joint_pert', 'joint_drop',
        'mae_base', 'mae_pert', 'mae_increase'
    ]
    
    with open(results_csv, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
        writer.writerow(mean_results)
    
    print(f"[INFO] Risultati salvati in: {results_csv}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Valutazione con perturbazione su 9-fold CV"
    )
    parser.add_argument(
        "--model",
        choices=["resnet18_mel96", "crnn_mel80", "conv1d_sep_ds48k"],
        default="resnet18_mel96",
        help="Modello da valutare (default: resnet18_mel96)"
    )
    parser.add_argument(
        "--perturb-preset",
        required=True,
        help="Preset perturbazione (es. pitch_P2_pos, white_W2, pink_K2)"
    )
    parser.add_argument(
        "--results-csv",
        type=str,
        default=None,
        help="Path CSV output (default: auto-genera nome)"
    )
    parser.add_argument(
        "--max-samples",
        type=int,
        default=None,
        help="Limita numero sample (default: tutti)"
    )
    
    args = parser.parse_args()
    
    eval_perturbation_cv(
        model_name=args.model,
        perturb_preset=args.perturb_preset,
        results_csv=args.results_csv,
        max_samples=args.max_samples,
    )


if __name__ == "__main__":
    main()

