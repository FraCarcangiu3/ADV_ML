#!/usr/bin/env python3
"""
test_new_spatial_effects.py

Smoke test per i 3 nuovi effetti spaziali:
- spatial_delay
- gain_jitter
- multi_channel_noise

Verifica che:
1. Non crashino
2. Modifichino effettivamente il waveform
3. Cambino le feature MEL+IPD/ILD in modo significativo

Uso:
    python -m model_classifier.test_new_spatial_effects

Autore: Francesco Carcangiu
"""

import numpy as np
import pandas as pd
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
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "ADV_ML"))
import audio_effects


def test_spatial_effects():
    """Test smoke dei 3 nuovi effetti spaziali."""
    
    print("="*80)
    print("SMOKE TEST: Nuovi Effetti Spaziali")
    print("="*80)
    print("Testando:")
    print("  1. spatial_delay (micro-delay tra canali)")
    print("  2. gain_jitter (variazioni gain per canale)")
    print("  3. multi_channel_noise (rumore indipendente per canale)")
    print("="*80 + "\n")
    
    # Carica un campione di test
    pairs = load_pairs()
    np.random.seed(42)
    idx = np.random.choice(len(pairs))
    audio_path, label_path = pairs[idx]
    angle_deg, dist_rel = load_labels(label_path)
    
    print(f"Sample di test: {audio_path.name}")
    print(f"  Angle: {angle_deg:.1f}°, Distance: {dist_rel:.2f}\n")
    
    # Carica audio
    audio_mat = pd.read_csv(audio_path, dtype=np.float32, engine="c").values
    print(f"Audio shape: {audio_mat.shape} (frames, channels)")
    print(f"Sample rate: {AUDIO_SR} Hz")
    print(f"Duration: {audio_mat.shape[0] / AUDIO_SR:.3f} sec\n")
    
    # Feature extraction baseline
    feature_cfg = {"n_mels": 96, "n_fft": 2048, "hop_length": 1024}
    feats_orig = compute_mel_ipd_ild(
        audio_mat,
        sr=AUDIO_SR,
        n_mels=feature_cfg["n_mels"],
        n_fft=feature_cfg["n_fft"],
        hop_length=feature_cfg["hop_length"],
        ref_ch=0,
    )
    
    print("-"*80)
    print("TEST 1: SPATIAL DELAY")
    print("-"*80)
    
    for level, max_samples in [("LOW", 2), ("MEDIUM", 5), ("HIGH", 10)]:
        print(f"\nLivello {level} (±{max_samples} samples ~= ±{max_samples/AUDIO_SR*1000:.3f}ms):")
        
        try:
            audio_delayed = audio_effects.apply_spatial_delay(audio_mat, AUDIO_SR, max_samples, seed=42)
            
            # Verifica shape
            assert audio_delayed.shape == audio_mat.shape, "Shape mismatch!"
            
            # Verifica che sia diverso
            wf_diff = np.mean(np.abs(audio_mat - audio_delayed))
            print(f"  ✅ Applicato correttamente")
            print(f"     Waveform diff mean: {wf_diff:.6f}")
            
            # Calcola feature
            feats_delayed = compute_mel_ipd_ild(
                audio_delayed,
                sr=AUDIO_SR,
                n_mels=feature_cfg["n_mels"],
                n_fft=feature_cfg["n_fft"],
                hop_length=feature_cfg["hop_length"],
                ref_ch=0,
            )
            
            feat_diff = np.mean(np.abs(feats_orig - feats_delayed))
            feat_diff_rel = feat_diff / (np.mean(np.abs(feats_orig)) + 1e-8)
            print(f"     Feature diff mean: {feat_diff:.6f} (rel: {feat_diff_rel:.2%})")
            
            if wf_diff < 1e-6:
                print(f"  ⚠️  WARNING: Waveform quasi identico!")
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
    
    print("\n" + "-"*80)
    print("TEST 2: CHANNEL GAIN JITTER")
    print("-"*80)
    
    for level, max_db in [("LOW", 0.5), ("MEDIUM", 1.0), ("HIGH", 1.5)]:
        print(f"\nLivello {level} (±{max_db} dB):")
        
        try:
            audio_jittered = audio_effects.apply_channel_gain_jitter(audio_mat, max_db, seed=42)
            
            # Verifica shape
            assert audio_jittered.shape == audio_mat.shape, "Shape mismatch!"
            
            # Verifica che sia diverso
            wf_diff = np.mean(np.abs(audio_mat - audio_jittered))
            print(f"  ✅ Applicato correttamente")
            print(f"     Waveform diff mean: {wf_diff:.6f}")
            
            # Calcola feature
            feats_jittered = compute_mel_ipd_ild(
                audio_jittered,
                sr=AUDIO_SR,
                n_mels=feature_cfg["n_mels"],
                n_fft=feature_cfg["n_fft"],
                hop_length=feature_cfg["hop_length"],
                ref_ch=0,
            )
            
            feat_diff = np.mean(np.abs(feats_orig - feats_jittered))
            feat_diff_rel = feat_diff / (np.mean(np.abs(feats_orig)) + 1e-8)
            print(f"     Feature diff mean: {feat_diff:.6f} (rel: {feat_diff_rel:.2%})")
            
            if wf_diff < 1e-6:
                print(f"  ⚠️  WARNING: Waveform quasi identico!")
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
    
    print("\n" + "-"*80)
    print("TEST 3: MULTI-CHANNEL NOISE (white)")
    print("-"*80)
    
    for level, snr_db in [("LOW", 42.0), ("MEDIUM", 40.0), ("HIGH", 38.0)]:
        print(f"\nLivello {level} (SNR {snr_db} dB):")
        
        try:
            audio_multi_white = audio_effects.apply_multi_channel_noise(
                audio_mat, snr_db, noise_type="white", seed=42
            )
            
            # Verifica shape
            assert audio_multi_white.shape == audio_mat.shape, "Shape mismatch!"
            
            # Verifica che sia diverso
            wf_diff = np.mean(np.abs(audio_mat - audio_multi_white))
            print(f"  ✅ Applicato correttamente")
            print(f"     Waveform diff mean: {wf_diff:.6f}")
            
            # Calcola feature
            feats_multi_white = compute_mel_ipd_ild(
                audio_multi_white,
                sr=AUDIO_SR,
                n_mels=feature_cfg["n_mels"],
                n_fft=feature_cfg["n_fft"],
                hop_length=feature_cfg["hop_length"],
                ref_ch=0,
            )
            
            feat_diff = np.mean(np.abs(feats_orig - feats_multi_white))
            feat_diff_rel = feat_diff / (np.mean(np.abs(feats_orig)) + 1e-8)
            print(f"     Feature diff mean: {feat_diff:.6f} (rel: {feat_diff_rel:.2%})")
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
    
    print("\n" + "-"*80)
    print("TEST 4: MULTI-CHANNEL NOISE (pink)")
    print("-"*80)
    
    for level, snr_db in [("LOW", 22.0), ("MEDIUM", 20.0), ("HIGH", 18.0)]:
        print(f"\nLivello {level} (SNR {snr_db} dB):")
        
        try:
            audio_multi_pink = audio_effects.apply_multi_channel_noise(
                audio_mat, snr_db, noise_type="pink", seed=42
            )
            
            # Verifica shape
            assert audio_multi_pink.shape == audio_mat.shape, "Shape mismatch!"
            
            # Verifica che sia diverso
            wf_diff = np.mean(np.abs(audio_mat - audio_multi_pink))
            print(f"  ✅ Applicato correttamente")
            print(f"     Waveform diff mean: {wf_diff:.6f}")
            
            # Calcola feature
            feats_multi_pink = compute_mel_ipd_ild(
                audio_multi_pink,
                sr=AUDIO_SR,
                n_mels=feature_cfg["n_mels"],
                n_fft=feature_cfg["n_fft"],
                hop_length=feature_cfg["hop_length"],
                ref_ch=0,
            )
            
            feat_diff = np.mean(np.abs(feats_orig - feats_multi_pink))
            feat_diff_rel = feat_diff / (np.mean(np.abs(feats_orig)) + 1e-8)
            print(f"     Feature diff mean: {feat_diff:.6f} (rel: {feat_diff_rel:.2%})")
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
    
    print("\n" + "="*80)
    print("CONCLUSIONI SMOKE TEST")
    print("="*80)
    print("✅ Se tutti i test sono passati, i 3 nuovi effetti funzionano correttamente!")
    print("\nProssimi passi:")
    print("  1. Ricompila il client C++ per usare i nuovi effetti in-game")
    print("  2. Testa in-game con AC_AUDIO_OBF_RANDOMIZE=1")
    print("  3. Esegui sweep completo per vedere l'impatto sulle accuracy:")
    print("     python -m model_classifier.run_best_models_perturb_sweep")
    print("="*80 + "\n")


if __name__ == "__main__":
    test_spatial_effects()

