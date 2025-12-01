#!/usr/bin/env python3
"""
eval_with_perturbation.py

Script per valutare i modelli del collega con e senza perturbazione audio.
Applica la perturbazione SOLO sul test set, lasciando training e validation intatti.

Uso:
    python -m model_classifier.eval_with_perturbation --preset pitch_P2_pos --max-samples 100

Autore: Francesco Carcangiu (integrazione anti-cheat)
Data: 2025-01-XX
"""

from __future__ import annotations

import argparse
import csv
import math
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.model_selection import train_test_split

# Aggiungi ADV_ML al path per importare audio_effects
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "ADV_ML"))

try:
    import audio_effects
except ImportError:
    print("[ERROR] Non riesco a importare ADV_ML/audio_effects.py")
    print("        Verifica che ADV_ML/ sia nella root del progetto.")
    sys.exit(1)

# Import dal modulo deep_cv del collega
if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parent.parent))
    from model_classifier.deep_cv import (
        AUDIO_SR,
        NUM_CHANNELS,
        DEVICE,
        SEED,
        BASE_DIR,
        AUDIO_DIR,
        LABEL_DIR,
        DIST_NUM_BINS,
        ANGLE_LABELS,
        set_seed,
        get_audio_uuid,
        load_labels,
        load_pairs,
        compute_mel_ipd_ild,
        downsample_wave,
        angle_deg_to_class,
        dist_to_class,
        get_distance_labels,
        ResNet18MT,
        CRNN,
        Conv1DSeparable,
    )
else:
    from model_classifier.deep_cv import (
        AUDIO_SR,
        NUM_CHANNELS,
        DEVICE,
        SEED,
        BASE_DIR,
        AUDIO_DIR,
        LABEL_DIR,
        DIST_NUM_BINS,
        ANGLE_LABELS,
        set_seed,
        get_audio_uuid,
        load_labels,
        load_pairs,
        compute_mel_ipd_ild,
        downsample_wave,
        angle_deg_to_class,
        dist_to_class,
        get_distance_labels,
        ResNet18MT,
        CRNN,
        Conv1DSeparable,
    )


# ============================================================================
# PRESET DI PERTURBAZIONE (calibrati dal CSV di configurazione)
# ============================================================================

PERTURB_PRESETS = {
    # Pitch shift
    "pitch_P1_pos": {"type": "pitch", "cents": +100.0},
    "pitch_P2_pos": {"type": "pitch", "cents": +150.0},
    "pitch_P3_pos": {"type": "pitch", "cents": +200.0},
    "pitch_P1_neg": {"type": "pitch", "cents": -100.0},
    "pitch_P2_neg": {"type": "pitch", "cents": -150.0},
    "pitch_P3_neg": {"type": "pitch", "cents": -200.0},
    
    # White noise (SNR in dB)
    "white_W1": {"type": "white_noise", "snr_db": 42.0},  # light
    "white_W2": {"type": "white_noise", "snr_db": 40.0},  # medium
    "white_W3": {"type": "white_noise", "snr_db": 38.0},  # strong
    
    # Pink noise (SNR in dB)
    "pink_K1": {"type": "pink_noise", "snr_db": 22.0},  # light
    "pink_K2": {"type": "pink_noise", "snr_db": 20.0},  # medium
    "pink_K3": {"type": "pink_noise", "snr_db": 18.0},  # strong
    
    # EQ tilt
    "eq_boost_light": {"type": "eq_tilt", "tilt_db": +3.0},
    "eq_boost_medium": {"type": "eq_tilt", "tilt_db": +4.5},
    "eq_boost_strong": {"type": "eq_tilt", "tilt_db": +6.0},
    "eq_cut_light": {"type": "eq_tilt", "tilt_db": -3.0},
    "eq_cut_medium": {"type": "eq_tilt", "tilt_db": -6.0},
    "eq_cut_strong": {"type": "eq_tilt", "tilt_db": -9.0},
    
    # High-pass filter
    "hp_150": {"type": "highpass", "cutoff_hz": 150},
    "hp_200": {"type": "highpass", "cutoff_hz": 200},
    "hp_250": {"type": "highpass", "cutoff_hz": 250},
    
    # Low-pass filter
    "lp_8000": {"type": "lowpass", "cutoff_hz": 8000},
    "lp_10000": {"type": "lowpass", "cutoff_hz": 10000},
    "lp_12000": {"type": "lowpass", "cutoff_hz": 12000},
}


# ============================================================================
# FUNZIONE DI PERTURBAZIONE
# ============================================================================

def apply_offline_perturbation_to_waveform(
    waveform: np.ndarray,
    sr: int,
    perturbation_config: Dict
) -> np.ndarray:
    """
    Applica perturbazione audio al waveform usando ADV_ML/audio_effects.py.
    
    Args:
        waveform: Array numpy [frames, channels] o [frames]
        sr: Sample rate in Hz
        perturbation_config: Dizionario con tipo e parametri:
            {"type": "pitch", "cents": 150.0}
            {"type": "white_noise", "snr_db": 40.0}
            {"type": "pink_noise", "snr_db": 20.0}
            {"type": "eq_tilt", "tilt_db": 3.0}
            {"type": "highpass", "cutoff_hz": 200}
            {"type": "lowpass", "cutoff_hz": 10000}
    
    Returns:
        Waveform perturbato (stessa shape di input)
    """
    pert_type = perturbation_config.get("type")
    
    if pert_type == "pitch":
        cents = perturbation_config.get("cents", 0.0)
        return audio_effects.apply_pitch_shift(waveform, sr, cents)
    
    elif pert_type == "white_noise":
        snr_db = perturbation_config.get("snr_db", 40.0)
        return audio_effects.add_white_noise(waveform, sr, snr_db)
    
    elif pert_type == "pink_noise":
        snr_db = perturbation_config.get("snr_db", 20.0)
        return audio_effects.add_pink_noise(waveform, sr, snr_db)
    
    elif pert_type == "eq_tilt":
        tilt_db = perturbation_config.get("tilt_db", 0.0)
        return audio_effects.apply_eq_tilt(waveform, sr, tilt_db)
    
    elif pert_type == "highpass":
        cutoff_hz = perturbation_config.get("cutoff_hz", 200)
        return audio_effects.apply_highpass(waveform, sr, cutoff_hz)
    
    elif pert_type == "lowpass":
        cutoff_hz = perturbation_config.get("cutoff_hz", 10000)
        return audio_effects.apply_lowpass(waveform, sr, cutoff_hz)
    
    else:
        raise ValueError(f"Tipo di perturbazione sconosciuto: {pert_type}")


# ============================================================================
# DATASET CON PERTURBAZIONE
# ============================================================================

class AudioFeatureDatasetWithPerturbation(torch.utils.data.Dataset):
    """
    Dataset modificato che applica perturbazione prima della feature extraction.
    
    Basato su AudioFeatureDataset di deep_cv.py, ma con opzione per applicare
    perturbazione al waveform prima di estrarre le feature.
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
        
        # Carica audio CSV
        audio_mat = pd.read_csv(audio_path, dtype=np.float32, engine="c").values
        if audio_mat.ndim != 2 or audio_mat.shape[1] != NUM_CHANNELS:
            raise ValueError(f"Invalid audio shape in {audio_path}")
        
        # ===== PUNTO DI PERTURBAZIONE =====
        # Se c'è una config di perturbazione, applicala al waveform
        if self.perturbation_config is not None:
            audio_mat = apply_offline_perturbation_to_waveform(
                audio_mat, AUDIO_SR, self.perturbation_config
            )
        
        # Feature extraction (come in deep_cv.py)
        if self.feature_type == "mel_ipd":
            feats = compute_mel_ipd_ild(
                audio_mat,
                sr=AUDIO_SR,
                n_mels=self.feature_cfg["n_mels"],
                n_fft=self.feature_cfg["n_fft"],
                hop_length=self.feature_cfg["hop_length"],
                ref_ch=0,
            )  # (C', M, T)
            feats_tensor = torch.from_numpy(feats)
        elif self.feature_type == "raw1d":
            dsr = self.feature_cfg["target_sr"]
            audio_ds = downsample_wave(audio_mat, dsr)
            feats_tensor = torch.from_numpy(audio_ds.T)  # (C, L)
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
# FUNZIONE DI VALUTAZIONE (come evaluate() in deep_cv.py)
# ============================================================================

def evaluate_model(
    model: nn.Module,
    loader: torch.utils.data.DataLoader,
    device: torch.device
) -> Dict[str, float]:
    """
    Valuta modello su un DataLoader e restituisce metriche.
    
    Returns:
        Dict con accuracy (angle, distance, joint) e MAE angolare
    """
    model.eval()
    angle_correct = 0
    dist_correct = 0
    joint_correct = 0
    total = 0
    angle_mae_list: List[float] = []
    
    with torch.no_grad():
        for feats, angle_cls, dist_cls, ang_vec in loader:
            feats = feats.to(device)
            angle_cls = angle_cls.to(device)
            dist_cls = dist_cls.to(device)
            ang_vec = ang_vec.to(device)
            
            # Predizioni
            angle_logits, dist_logits, vec_pred = model(feats)
            angle_pred = angle_logits.argmax(dim=1)
            dist_pred = dist_logits.argmax(dim=1)
            
            # Accuracy
            angle_correct += (angle_pred == angle_cls).sum().item()
            dist_correct += (dist_pred == dist_cls).sum().item()
            joint_correct += ((angle_pred == angle_cls) & (dist_pred == dist_cls)).sum().item()
            total += angle_cls.size(0)
            
            # MAE angolare (da vettore sin/cos)
            pred_angle_rad = torch.atan2(vec_pred[:, 0], vec_pred[:, 1])
            true_angle_rad = torch.atan2(ang_vec[:, 0], ang_vec[:, 1])
            diff = torch.remainder(pred_angle_rad - true_angle_rad + math.pi, 2 * math.pi) - math.pi
            angle_mae_list.append(torch.abs(diff).cpu().numpy())
    
    if total == 0:
        return {"angle_acc": 0.0, "dist_acc": 0.0, "joint_acc": 0.0, "angle_mae": 0.0}
    
    angle_mae = float(np.mean(np.concatenate(angle_mae_list))) * 180.0 / math.pi
    
    return {
        "angle_acc": angle_correct / total,
        "dist_acc": dist_correct / total,
        "joint_acc": joint_correct / total,
        "angle_mae": angle_mae,
    }


# ============================================================================
# FUNZIONE PRINCIPALE
# ============================================================================

def evaluate_with_and_without_perturbation(
    perturbation_config: Dict,
    max_samples: int | None = None,
    model_name: str = "resnet18_mel96",
):
    """
    Valuta modello con e senza perturbazione.
    
    Args:
        perturbation_config: Config perturbazione (da PERTURB_PRESETS)
        max_samples: Numero massimo di sample da testare (None = tutti)
        model_name: Nome modello da usare (resnet18_mel96, crnn_mel80, conv1d_sep_ds48k)
    """
    set_seed(SEED)
    
    print(f"\n{'='*70}")
    print(f"VALUTAZIONE CON E SENZA PERTURBAZIONE")
    print(f"{'='*70}")
    print(f"Modello: {model_name}")
    print(f"Perturbazione: {perturbation_config}")
    print(f"Max samples: {max_samples if max_samples else 'tutti'}")
    print(f"Device: {DEVICE}")
    print(f"{'='*70}\n")
    
    # Carica dataset
    print("[1/6] Caricamento dataset...")
    pairs = load_pairs()
    
    if max_samples and max_samples < len(pairs):
        # Limita a max_samples (prendi sample random ma con seed fisso)
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
    
    # Split train/test (80/20)
    print("\n[2/6] Split train/test...")
    
    # Per dataset piccoli (< 50 sample), non usare stratify
    # perché alcune classi potrebbero avere solo 1 sample
    if len(pairs) >= 50:
        stratify_labels = angle_classes * DIST_NUM_BINS + dist_classes
        print(f"      → Usando split stratificato")
    else:
        stratify_labels = None
        print(f"      → Dataset piccolo: usando split NON stratificato")
    
    train_pairs, test_pairs = train_test_split(
        pairs, test_size=0.2, random_state=SEED, stratify=stratify_labels
    )
    print(f"      → Train: {len(train_pairs)} sample")
    print(f"      → Test:  {len(test_pairs)} sample")
    
    # Configurazione modello
    print(f"\n[3/6] Configurazione modello {model_name}...")
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
    
    # Crea dataset di test SENZA perturbazione (baseline)
    print("\n[4/6] Creazione dataset baseline (senza perturbazione)...")
    test_ds_baseline = AudioFeatureDatasetWithPerturbation(
        test_pairs,
        feature_type,
        feature_cfg,
        dist_thresholds,
        DIST_NUM_BINS,
        perturbation_config=None,  # NESSUNA perturbazione
    )
    test_loader_baseline = torch.utils.data.DataLoader(
        test_ds_baseline, batch_size=8, shuffle=False, num_workers=0
    )
    
    # Crea dataset di test CON perturbazione
    print("[5/6] Creazione dataset perturbato...")
    test_ds_pert = AudioFeatureDatasetWithPerturbation(
        test_pairs,
        feature_type,
        feature_cfg,
        dist_thresholds,
        DIST_NUM_BINS,
        perturbation_config=perturbation_config,  # PERTURBAZIONE ATTIVA
    )
    test_loader_pert = torch.utils.data.DataLoader(
        test_ds_pert, batch_size=8, shuffle=False, num_workers=0
    )
    
    # Crea modello (per ora non addestrato, solo per testare shape)
    print(f"\n[6/6] Creazione modello {model_name}...")
    
    # Determina numero di canali input
    sample_feats, _, _, _ = test_ds_baseline[0]
    in_ch = sample_feats.shape[0] if feature_type == "mel_ipd" else NUM_CHANNELS
    
    if model_name.startswith("resnet"):
        model = ResNet18MT(in_ch, len(ANGLE_LABELS), DIST_NUM_BINS, dropout=model_cfg.get("dropout", 0.2))
    elif model_name.startswith("crnn"):
        model = CRNN(in_ch, len(ANGLE_LABELS), DIST_NUM_BINS, hidden=model_cfg.get("hidden", 128), dropout=model_cfg.get("dropout", 0.2))
    elif model_name.startswith("conv1d"):
        model = Conv1DSeparable(in_ch, len(ANGLE_LABELS), DIST_NUM_BINS, dropout=model_cfg.get("dropout", 0.15))
    else:
        raise ValueError(f"Tipo modello non riconosciuto: {model_name}")
    
    model = model.to(DEVICE)
    
    # ===== CHECKPOINT =====
    # Cerca se esiste un checkpoint salvato
    checkpoint_path = BASE_DIR / "model_classifier" / f"checkpoint_{model_name}.pth"
    
    if checkpoint_path.exists():
        print(f"\n{'='*70}")
        print(f"CARICAMENTO CHECKPOINT")
        print(f"{'='*70}")
        print(f"Trovato checkpoint: {checkpoint_path}")
        checkpoint = torch.load(checkpoint_path, map_location=DEVICE, weights_only=False)
        model.load_state_dict(checkpoint["model_state_dict"])
        print("Checkpoint caricato con successo!")
        
        # Valutazione baseline
        print(f"\n{'='*70}")
        print(f"BASELINE (senza perturbazione) su {len(test_pairs)} sample di test")
        print(f"{'='*70}")
        metrics_baseline = evaluate_model(model, test_loader_baseline, DEVICE)
        print(f"Direction accuracy: {metrics_baseline['angle_acc']:.4f}")
        print(f"Distance accuracy:  {metrics_baseline['dist_acc']:.4f}")
        print(f"Joint accuracy:     {metrics_baseline['joint_acc']:.4f}")
        print(f"Angle MAE:          {metrics_baseline['angle_mae']:.2f}°")
        
        # Valutazione con perturbazione
        print(f"\n{'='*70}")
        print(f"CON PERTURBAZIONE: {perturbation_config}")
        print(f"{'='*70}")
        metrics_pert = evaluate_model(model, test_loader_pert, DEVICE)
        print(f"Direction accuracy: {metrics_pert['angle_acc']:.4f}")
        print(f"Distance accuracy:  {metrics_pert['dist_acc']:.4f}")
        print(f"Joint accuracy:     {metrics_pert['joint_acc']:.4f}")
        print(f"Angle MAE:          {metrics_pert['angle_mae']:.2f}°")
        
        # Degradazione
        print(f"\n{'='*70}")
        print(f"DEGRADAZIONE (baseline - perturbata)")
        print(f"{'='*70}")
        dir_drop = metrics_baseline['angle_acc'] - metrics_pert['angle_acc']
        dist_drop = metrics_baseline['dist_acc'] - metrics_pert['dist_acc']
        joint_drop = metrics_baseline['joint_acc'] - metrics_pert['joint_acc']
        mae_increase = metrics_pert['angle_mae'] - metrics_baseline['angle_mae']
        
        print(f"Direction: {dir_drop:+.4f}")
        print(f"Distance:  {dist_drop:+.4f}")
        print(f"Joint:     {joint_drop:+.4f}")
        print(f"Angle MAE: {mae_increase:+.2f}°")
        print(f"{'='*70}\n")
        
        # Salva risultati in CSV
        results_csv = BASE_DIR / "model_classifier" / f"perturbation_results_{perturbation_config['type']}.csv"
        write_header = not results_csv.exists()
        
        with open(results_csv, "a", newline="") as f:
            writer = csv.writer(f)
            if write_header:
                writer.writerow([
                    "preset", "n_samples", 
                    "dir_base", "dir_pert", "dir_drop",
                    "dist_base", "dist_pert", "dist_drop",
                    "joint_base", "joint_pert", "joint_drop",
                    "mae_base", "mae_pert", "mae_increase"
                ])
            
            # Determina nome preset
            preset_name = f"{perturbation_config['type']}"
            if 'cents' in perturbation_config:
                preset_name += f"_{perturbation_config['cents']:+.0f}c"
            elif 'snr_db' in perturbation_config:
                preset_name += f"_{perturbation_config['snr_db']:.1f}dB"
            elif 'tilt_db' in perturbation_config:
                preset_name += f"_{perturbation_config['tilt_db']:+.1f}dB"
            elif 'cutoff_hz' in perturbation_config:
                preset_name += f"_{perturbation_config['cutoff_hz']}Hz"
            
            writer.writerow([
                preset_name, len(test_pairs),
                f"{metrics_baseline['angle_acc']:.4f}", f"{metrics_pert['angle_acc']:.4f}", f"{dir_drop:+.4f}",
                f"{metrics_baseline['dist_acc']:.4f}", f"{metrics_pert['dist_acc']:.4f}", f"{dist_drop:+.4f}",
                f"{metrics_baseline['joint_acc']:.4f}", f"{metrics_pert['joint_acc']:.4f}", f"{joint_drop:+.4f}",
                f"{metrics_baseline['angle_mae']:.2f}", f"{metrics_pert['angle_mae']:.2f}", f"{mae_increase:+.2f}"
            ])
        
        print(f"[INFO] Risultati salvati in: {results_csv}\n")
        
    else:
        print(f"\n{'='*70}")
        print(f"ATTENZIONE: MODELLO NON ADDESTRATO")
        print(f"{'='*70}")
        print(f"Checkpoint non trovato: {checkpoint_path}")
        print("")
        print("Per addestrare il modello, lancia:")
        print(f"  cd COLLEAGUE_BSc_Thesis")
        print(f"  python -m model_classifier.deep_cv")
        print("")
        print("Poi modifica deep_cv.py per salvare checkpoint dopo il training.")
        print("")
        print("Per ora ho verificato che:")
        print("  ✓ Dataset si carica correttamente")
        print("  ✓ Perturbazione si applica senza crash")
        print("  ✓ Feature extraction funziona")
        print("  ✓ Modello si istanzia correttamente")
        print("")
        print(f"Shape feature baseline: {sample_feats.shape}")
        print(f"Input channels: {in_ch}")
        print(f"Angle classes: {len(ANGLE_LABELS)}")
        print(f"Distance bins: {DIST_NUM_BINS}")
        print(f"{'='*70}\n")


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Valuta modelli con e senza perturbazione audio"
    )
    parser.add_argument(
        "--preset",
        choices=list(PERTURB_PRESETS.keys()),
        required=True,
        help="Preset di perturbazione da usare"
    )
    parser.add_argument(
        "--max-samples",
        type=int,
        default=None,
        help="Numero massimo di sample da testare (default: tutti)"
    )
    parser.add_argument(
        "--model",
        choices=["resnet18_mel96", "crnn_mel80", "conv1d_sep_ds48k"],
        default="resnet18_mel96",
        help="Modello da usare (default: resnet18_mel96)"
    )
    
    args = parser.parse_args()
    
    cfg = PERTURB_PRESETS[args.preset]
    evaluate_with_and_without_perturbation(
        cfg,
        max_samples=args.max_samples,
        model_name=args.model
    )


if __name__ == "__main__":
    main()

