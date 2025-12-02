#!/usr/bin/env python3
"""
debug_pitch_effect.py

Script di debug per verificare che il pitch shift venga applicato
e per analizzare come cambiano le feature MEL+IPD/ILD.

Uso:
    python -m model_classifier.debug_pitch_effect

Autore: Francesco Carcangiu
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import sys

# Import da deep_cv del collega
from model_classifier.deep_cv import (
    AUDIO_SR,
    NUM_CHANNELS,
    BASE_DIR,
    load_pairs,
    load_labels,
    compute_mel_ipd_ild,
)

# Import utilità perturbazione
from model_classifier.perturbation_utils import (
    apply_perturbation_waveform,
    get_preset_config,
)


def analyze_pitch_effect_on_features(n_samples=5):
    """
    Analizza l'effetto del pitch shift sulle feature MEL+IPD/ILD.
    
    Args:
        n_samples: Numero di campioni da analizzare
    """
    print("="*70)
    print("DEBUG: Effetto Pitch Shift su Feature MEL+IPD/ILD")
    print("="*70)
    print(f"Analizzeremo {n_samples} campioni casuali...\n")
    
    # Carica dataset
    pairs = load_pairs()
    
    # Seleziona campioni casuali
    np.random.seed(42)
    indices = np.random.choice(len(pairs), n_samples, replace=False)
    
    preset_name = "pitch_P2_pos"  # +150 cents
    preset_config = get_preset_config(preset_name)
    
    print(f"Preset perturbazione: {preset_name}")
    print(f"Configurazione: {preset_config}\n")
    print("-"*70)
    
    feature_cfg = {"n_mels": 96, "n_fft": 2048, "hop_length": 1024}
    
    for i, idx in enumerate(indices, start=1):
        audio_path, label_path = pairs[idx]
        angle_deg, dist_rel = load_labels(label_path)
        
        print(f"\n[Sample {i}/{n_samples}]")
        print(f"  File: {audio_path.name}")
        print(f"  Angle: {angle_deg:.1f}°, Distance: {dist_rel:.2f}")
        
        # Carica audio CSV (waveform)
        audio_mat = pd.read_csv(audio_path, dtype=np.float32, engine="c").values
        
        # Calcola statistiche waveform originale
        wf_mean_orig = np.mean(np.abs(audio_mat))
        wf_max_orig = np.max(np.abs(audio_mat))
        wf_std_orig = np.std(audio_mat)
        
        print(f"\n  Waveform ORIGINALE:")
        print(f"    Mean(abs): {wf_mean_orig:.6f}")
        print(f"    Max(abs):  {wf_max_orig:.6f}")
        print(f"    Std:       {wf_std_orig:.6f}")
        
        # Applica pitch shift
        audio_mat_shifted = apply_perturbation_waveform(audio_mat, AUDIO_SR, preset_name)
        
        # Calcola statistiche waveform shiftato
        wf_mean_shifted = np.mean(np.abs(audio_mat_shifted))
        wf_max_shifted = np.max(np.abs(audio_mat_shifted))
        wf_std_shifted = np.std(audio_mat_shifted)
        
        print(f"\n  Waveform SHIFTATO (+150 cents):")
        print(f"    Mean(abs): {wf_mean_shifted:.6f} (diff: {wf_mean_shifted - wf_mean_orig:+.6f})")
        print(f"    Max(abs):  {wf_max_shifted:.6f} (diff: {wf_max_shifted - wf_max_orig:+.6f})")
        print(f"    Std:       {wf_std_shifted:.6f} (diff: {wf_std_shifted - wf_std_orig:+.6f})")
        
        # Verifica se il pitch shift ha avuto effetto
        wf_diff = np.mean(np.abs(audio_mat - audio_mat_shifted))
        print(f"\n  ⚠️  Differenza media waveform: {wf_diff:.6f}")
        
        if wf_diff < 1e-4:
            print(f"  ❌ WARNING: Waveform quasi identico! Pitch shift NON applicato?")
        else:
            print(f"  ✅ Waveform modificato dal pitch shift")
        
        # Estrai feature MEL+IPD/ILD
        feats_orig = compute_mel_ipd_ild(
            audio_mat,
            sr=AUDIO_SR,
            n_mels=feature_cfg["n_mels"],
            n_fft=feature_cfg["n_fft"],
            hop_length=feature_cfg["hop_length"],
            ref_ch=0,
        )
        
        feats_shifted = compute_mel_ipd_ild(
            audio_mat_shifted,
            sr=AUDIO_SR,
            n_mels=feature_cfg["n_mels"],
            n_fft=feature_cfg["n_fft"],
            hop_length=feature_cfg["hop_length"],
            ref_ch=0,
        )
        
        # Analizza differenze nelle feature
        # Le feature sono shape: (n_channels, n_mels, n_frames)
        # Dove n_channels = 8*3 = 24 (8 canali mel + 8 canali IPD + 8 canali ILD)
        
        feat_diff = np.abs(feats_orig - feats_shifted)
        feat_diff_mean = np.mean(feat_diff)
        feat_diff_max = np.max(feat_diff)
        feat_diff_rel = feat_diff_mean / (np.mean(np.abs(feats_orig)) + 1e-8)
        
        print(f"\n  Feature MEL+IPD/ILD:")
        print(f"    Shape: {feats_orig.shape}")
        print(f"    Diff mean: {feat_diff_mean:.6f}")
        print(f"    Diff max:  {feat_diff_max:.6f}")
        print(f"    Diff rel:  {feat_diff_rel:.2%}")
        
        # Analizza separatamente MEL, IPD, ILD
        # Assumendo che siano impilati verticalmente (da verificare in deep_cv.py)
        n_feat_channels = feats_orig.shape[0]
        channels_per_type = n_feat_channels // 3  # MEL, IPD, ILD
        
        mel_slice = slice(0, channels_per_type)
        ipd_slice = slice(channels_per_type, 2 * channels_per_type)
        ild_slice = slice(2 * channels_per_type, 3 * channels_per_type)
        
        mel_diff = np.mean(np.abs(feats_orig[mel_slice] - feats_shifted[mel_slice]))
        ipd_diff = np.mean(np.abs(feats_orig[ipd_slice] - feats_shifted[ipd_slice]))
        ild_diff = np.mean(np.abs(feats_orig[ild_slice] - feats_shifted[ild_slice]))
        
        mel_orig_mean = np.mean(np.abs(feats_orig[mel_slice]))
        ipd_orig_mean = np.mean(np.abs(feats_orig[ipd_slice]))
        ild_orig_mean = np.mean(np.abs(feats_orig[ild_slice]))
        
        print(f"\n  Breakdown per tipo di feature:")
        print(f"    MEL diff: {mel_diff:.6f} (rel: {mel_diff/(mel_orig_mean+1e-8):.2%})")
        print(f"    IPD diff: {ipd_diff:.6f} (rel: {ipd_diff/(ipd_orig_mean+1e-8):.2%})")
        print(f"    ILD diff: {ild_diff:.6f} (rel: {ild_diff/(ild_orig_mean+1e-8):.2%})")
        
        if ipd_diff < 1e-3 and ild_diff < 1e-3:
            print(f"\n  💡 INSIGHT: IPD e ILD cambiano pochissimo!")
            print(f"     Queste sono feature GEOMETRICHE, invarianti al pitch.")
            print(f"     Il modello probabilmente usa principalmente IPD/ILD per localizzare,")
            print(f"     quindi il pitch shift ha POCO impatto sulla predizione.")
        
        print("-"*70)
    
    print("\n" + "="*70)
    print("CONCLUSIONE ANALISI")
    print("="*70)
    print("\nSe IPD e ILD cambiano pochissimo, significa che:")
    print("1. Il pitch shift è applicato correttamente al waveform")
    print("2. MA le feature spaziali (IPD/ILD) sono INVARIANTI al pitch")
    print("3. Il modello usa principalmente queste feature → è robusto al pitch!")
    print("\nPER DEGRADARE LE PERFORMANCE:")
    print("- Usa perturbazioni che influenzano la FASE e il LIVELLO (IPD/ILD)")
    print("- Es: Pink noise (disturba fase), EQ tilt (disturba livello)")
    print("- Il pitch shift NON è efficace contro questo tipo di modello")
    print("="*70 + "\n")


if __name__ == "__main__":
    analyze_pitch_effect_on_features(n_samples=3)

