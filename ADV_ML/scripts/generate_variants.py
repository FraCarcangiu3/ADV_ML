#!/usr/bin/env python3
"""
generate_variants.py - Genera varianti audio per test coarse → fine
Autore: Francesco Carcangiu
Data: 23 Ottobre 2025

Implementa la procedura coarse → fine per trovare min_perc e max_ok:
1. COARSE SWEEP: testa range ampi per identificare regioni candidate
2. FINE SWEEP: testa range ristretti intorno alle soglie identificate

Configurazione:
- COARSE_PITCH = [0, 10, 25, 50, 100] (genera sia + che -)
- COARSE_NOISE_SNR = [40, 35, 30, 25] dB
- FINE_PITCH_STEP = 2 cents
- FINE_RANGE_WINDOW = ±20 cents around detected threshold
- TRIALS_PER_SETTING = 3
"""

import os
import sys
import subprocess
import json
import numpy as np
import soundfile as sf
import librosa
from pathlib import Path
import argparse
import csv

# ============================================================================
# CONFIGURAZIONE TEST COARSE → FINE
# ============================================================================

# Suoni di input (path relativi a root AC/)
SOUNDS = [
    "AC/packages/audio/weapon/auto.ogg",
    "AC/packages/audio/player/footsteps.ogg",
    "AC/packages/audio/voicecom/affirmative.ogg"
]

# Parametri COARSE SWEEP
COARSE_PITCH = [0, 10, 25, 50, 100]  # cents (genera sia + che -)
COARSE_NOISE_SNR = [40, 35, 30, 25]  # dB

# Parametri FINE SWEEP
FINE_PITCH_STEP = 2  # cents
FINE_RANGE_WINDOW = 20  # ±20 cents around detected threshold
TRIALS_PER_SETTING = 3

# Directory output (archived, ora in archive/)
# NOTA: Questi percorsi puntano all'archive per compatibilità con dati esistenti
OUTPUT_DIR = Path("ADV_ML/archive/output")
COARSE_DIR = OUTPUT_DIR / "coarse"
FINE_DIR = OUTPUT_DIR / "fine"
COARSE_RESULTS_DIR = Path("ADV_ML/archive/coarse_results")

# Pitch test tool path
PITCH_TEST_TOOL = "AC/tools/pitch_test"

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def log(msg):
    """Log con timestamp"""
    print(f"[{__file__}] {msg}")

def check_pitch_test_available():
    """Verifica se AC/tools/pitch_test è eseguibile"""
    if os.path.exists(PITCH_TEST_TOOL) and os.access(PITCH_TEST_TOOL, os.X_OK):
        return True
    return False

def convert_ogg_to_wav(ogg_path, wav_path, sample_rate=44100):
    """Converte OGG a WAV mono usando ffmpeg"""
    cmd = [
        "ffmpeg", "-y", "-i", str(ogg_path),
        "-ar", str(sample_rate), "-ac", "1",
        str(wav_path)
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        log(f"ERROR: ffmpeg failed: {e.stderr}")
        return False
    except FileNotFoundError:
        log("ERROR: ffmpeg not found")
        return False

def apply_pitch_shift_pitch_test(input_wav, output_wav, cents):
    """Applica pitch shift usando AC/tools/pitch_test"""
    cmd = [PITCH_TEST_TOOL, str(input_wav), str(output_wav), "--cents", str(cents)]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        log(f"ERROR: pitch_test failed: {e.stderr}")
        return False

def apply_pitch_shift_librosa(input_wav, output_wav, cents, sample_rate=44100):
    """Applica pitch shift usando librosa (fallback)"""
    try:
        # Carica audio
        y, sr = librosa.load(str(input_wav), sr=sample_rate, mono=True)
        
        # Calcola n_steps (cents to semitones)
        n_steps = cents / 100.0
        
        # Applica pitch shift
        y_shifted = librosa.effects.pitch_shift(y, sr=sr, n_steps=n_steps)
        
        # Salva
        sf.write(str(output_wav), y_shifted, sample_rate)
        return True
    except Exception as e:
        log(f"ERROR: librosa pitch shift failed: {e}")
        return False

def add_white_noise(input_wav, output_wav, target_snr_db, sample_rate=44100):
    """Aggiunge white noise con SNR target"""
    try:
        # Carica audio
        y, sr = librosa.load(str(input_wav), sr=sample_rate, mono=True)
        
        # Calcola RMS del segnale
        rms_signal = np.sqrt(np.mean(y**2))
        if rms_signal < 1e-6:
            log(f"WARNING: Signal too weak for {input_wav}")
            return False
        
        # Calcola amplitude rumore: A_noise = RMS_signal / (10^(SNR/20))
        noise_amplitude = rms_signal / (10**(target_snr_db / 20.0))
        
        # Genera white noise
        noise = np.random.normal(0, noise_amplitude, len(y))
        
        # Somma e clipping
        y_noisy = y + noise
        y_noisy = np.clip(y_noisy, -1.0, 1.0)
        
        # Salva
        sf.write(str(output_wav), y_noisy, sample_rate)
        return True
    except Exception as e:
        log(f"ERROR: white noise failed: {e}")
        return False

def generate_filename(base_name, variant_type, value, trial, sweep_type="coarse"):
    """Genera nome file per variante"""
    if variant_type == "pitch":
        sign = "p" if value >= 0 else "n"
        val_str = f"{abs(value)}"
    elif variant_type == "noise":
        sign = "w"
        val_str = f"{value}"
    else:
        sign = "x"
        val_str = f"{value}"
    
    return f"{base_name}__{sweep_type}__type-{sign}__val-{val_str}__trial-{trial}.wav"

# ============================================================================
# COARSE SWEEP IMPLEMENTATION
# ============================================================================

def run_coarse_sweep(sound_path, output_metadata):
    """Esegue coarse sweep per un suono"""
    log(f"COARSE SWEEP: {sound_path}")
    
    # Verifica file esiste
    if not os.path.exists(sound_path):
        log(f"ERROR: File not found: {sound_path}")
        return False
    
    # Crea base name
    base_name = Path(sound_path).stem
    
    # Crea directory per questo suono
    sound_coarse_dir = COARSE_DIR / base_name
    sound_coarse_dir.mkdir(parents=True, exist_ok=True)
    
    # Converti a WAV reference
    ref_wav = sound_coarse_dir / f"{base_name}_ref.wav"
    if not convert_ogg_to_wav(sound_path, ref_wav):
        log(f"ERROR: Failed to convert {sound_path}")
        return False
    
    log(f"Created reference: {ref_wav}")
    
    # Verifica pitch_test disponibilità
    use_pitch_test = check_pitch_test_available()
    log(f"Using pitch_test: {use_pitch_test}")
    
    # Genera varianti coarse
    variant_count = 0
    
    # 1. Pitch variants (+ e - per ogni valore)
    for pitch_cents in COARSE_PITCH:
        for trial in range(1, TRIALS_PER_SETTING + 1):
            # Pitch positivo
            output_name = generate_filename(base_name, "pitch", pitch_cents, trial, "coarse")
            output_wav = sound_coarse_dir / output_name
            
            success = False
            if use_pitch_test:
                success = apply_pitch_shift_pitch_test(ref_wav, output_wav, pitch_cents)
            else:
                success = apply_pitch_shift_librosa(ref_wav, output_wav, pitch_cents)
            
            if success:
                output_metadata.append({
                    "file": output_name,
                    "trial": trial,
                    "variant_type": "pitch",
                    "applied_pitch_cents": pitch_cents,
                    "applied_noise_snr_db": None,
                    "base_sound": sound_path,
                    "sweep_type": "coarse",
                    "ref_file": str(ref_wav)
                })
                variant_count += 1
                log(f"  Created pitch +{pitch_cents}: {output_name}")
            
            # Pitch negativo
            output_name = generate_filename(base_name, "pitch", -pitch_cents, trial, "coarse")
            output_wav = sound_coarse_dir / output_name
            
            success = False
            if use_pitch_test:
                success = apply_pitch_shift_pitch_test(ref_wav, output_wav, -pitch_cents)
            else:
                success = apply_pitch_shift_librosa(ref_wav, output_wav, -pitch_cents)
            
            if success:
                output_metadata.append({
                    "file": output_name,
                    "trial": trial,
                    "variant_type": "pitch",
                    "applied_pitch_cents": -pitch_cents,
                    "applied_noise_snr_db": None,
                    "base_sound": sound_path,
                    "sweep_type": "coarse",
                    "ref_file": str(ref_wav)
                })
                variant_count += 1
                log(f"  Created pitch {pitch_cents}: {output_name}")
    
    # 2. Noise variants
    for snr_db in COARSE_NOISE_SNR:
        for trial in range(1, TRIALS_PER_SETTING + 1):
            output_name = generate_filename(base_name, "noise", snr_db, trial, "coarse")
            output_wav = sound_coarse_dir / output_name
            
            if add_white_noise(ref_wav, output_wav, snr_db):
                output_metadata.append({
                    "file": output_name,
                    "trial": trial,
                    "variant_type": "noise",
                    "applied_pitch_cents": None,
                    "applied_noise_snr_db": snr_db,
                    "base_sound": sound_path,
                    "sweep_type": "coarse",
                    "ref_file": str(ref_wav)
                })
                variant_count += 1
                log(f"  Created noise SNR={snr_db}: {output_name}")
    
    log(f"Generated {variant_count} coarse variants for {base_name}")
    return True

# ============================================================================
# FINE SWEEP IMPLEMENTATION
# ============================================================================

def analyze_coarse_results(sound_name):
    """Analizza risultati coarse per identificare regioni candidate per fine sweep"""
    coarse_csv = COARSE_RESULTS_DIR / f"{sound_name}_coarse.csv"
    
    if not coarse_csv.exists():
        log(f"WARNING: Coarse results not found: {coarse_csv}")
        return None
    
    # Leggi risultati coarse
    pitch_thresholds = []
    
    try:
        with open(coarse_csv, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['variant_type'] == 'pitch' and row['snr_db'] != 'inf':
                    pitch_cents = float(row['applied_pitch_cents'])
                    snr_db = float(row['snr_db'])
                    
                    # Identifica soglie: SNR < 35 dB
                    if snr_db < 35:
                        pitch_thresholds.append(abs(pitch_cents))
    except Exception as e:
        log(f"ERROR: Failed to analyze coarse results: {e}")
        return None
    
    if not pitch_thresholds:
        log(f"WARNING: No thresholds found for {sound_name}")
        return None
    
    # Trova la soglia più piccola
    min_threshold = min(pitch_thresholds)
    log(f"Identified threshold for {sound_name}: {min_threshold} cents")
    
    # Calcola range fine: ±20 cents around threshold
    fine_range = (min_threshold - FINE_RANGE_WINDOW, min_threshold + FINE_RANGE_WINDOW)
    log(f"Fine range for {sound_name}: {fine_range[0]} to {fine_range[1]} cents")
    
    return fine_range

def run_fine_sweep(sound_path, fine_range, output_metadata):
    """Esegue fine sweep per un suono nel range specificato"""
    log(f"FINE SWEEP: {sound_path} in range {fine_range}")
    
    # Crea base name
    base_name = Path(sound_path).stem
    
    # Crea directory per questo suono
    sound_fine_dir = FINE_DIR / base_name
    sound_fine_dir.mkdir(parents=True, exist_ok=True)
    
    # Trova file di riferimento
    ref_wav = COARSE_DIR / base_name / f"{base_name}_ref.wav"
    if not ref_wav.exists():
        log(f"ERROR: Reference file not found: {ref_wav}")
        return False
    
    # Verifica pitch_test disponibilità
    use_pitch_test = check_pitch_test_available()
    
    # Genera varianti fine
    variant_count = 0
    
    # Genera pitch values nel range con step FINE_PITCH_STEP
    fine_pitch_values = []
    current = fine_range[0]
    while current <= fine_range[1]:
        fine_pitch_values.append(current)
        current += FINE_PITCH_STEP
    
    # Aggiungi anche valori negativi
    fine_pitch_values.extend([-x for x in fine_pitch_values if x != 0])
    fine_pitch_values = sorted(set(fine_pitch_values))
    
    log(f"Fine pitch values: {fine_pitch_values}")
    
    # Genera varianti
    for pitch_cents in fine_pitch_values:
        for trial in range(1, TRIALS_PER_SETTING + 1):
            output_name = generate_filename(base_name, "pitch", pitch_cents, trial, "fine")
            output_wav = sound_fine_dir / output_name
            
            success = False
            if use_pitch_test:
                success = apply_pitch_shift_pitch_test(ref_wav, output_wav, pitch_cents)
            else:
                success = apply_pitch_shift_librosa(ref_wav, output_wav, pitch_cents)
            
            if success:
                output_metadata.append({
                    "file": output_name,
                    "trial": trial,
                    "variant_type": "pitch",
                    "applied_pitch_cents": pitch_cents,
                    "applied_noise_snr_db": None,
                    "base_sound": sound_path,
                    "sweep_type": "fine",
                    "ref_file": str(ref_wav)
                })
                variant_count += 1
                log(f"  Created fine pitch {pitch_cents}: {output_name}")
    
    log(f"Generated {variant_count} fine variants for {base_name}")
    return True

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Generate audio variants for coarse→fine testing")
    parser.add_argument("--sounds", nargs="+", default=SOUNDS, help="Input sound files")
    parser.add_argument("--coarse-only", action="store_true", help="Run only coarse sweep")
    parser.add_argument("--fine-only", action="store_true", help="Run only fine sweep")
    args = parser.parse_args()
    
    # Crea directory output
    COARSE_DIR.mkdir(parents=True, exist_ok=True)
    FINE_DIR.mkdir(parents=True, exist_ok=True)
    COARSE_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    
    log("Starting coarse→fine variant generation...")
    log(f"Pitch test available: {check_pitch_test_available()}")
    log(f"Coarse dir: {COARSE_DIR}")
    log(f"Fine dir: {FINE_DIR}")
    
    # Metadata per tutte le varianti
    all_metadata = []
    
    # STEP 1: COARSE SWEEP
    if not args.fine_only:
        log("=" * 50)
        log("STEP 1: COARSE SWEEP")
        log("=" * 50)
        
        for sound_path in args.sounds:
            # Logging richiesto per verifica run
            log(f"Processing sound: {Path(sound_path).name}")
            if run_coarse_sweep(sound_path, all_metadata):
                log(f"✓ Coarse completed: {sound_path}")
            else:
                log(f"✗ Coarse failed: {sound_path}")
    
    # STEP 2: FINE SWEEP
    if not args.coarse_only:
        log("=" * 50)
        log("STEP 2: FINE SWEEP")
        log("=" * 50)
        
        for sound_path in args.sounds:
            base_name = Path(sound_path).stem
            # Logging richiesto per verifica run
            log(f"Processing sound: {Path(sound_path).name}")
            
            # Analizza risultati coarse per identificare range fine
            fine_range = analyze_coarse_results(base_name)
            
            if fine_range:
                if run_fine_sweep(sound_path, fine_range, all_metadata):
                    log(f"✓ Fine completed: {sound_path}")
                else:
                    log(f"✗ Fine failed: {sound_path}")
            else:
                log(f"⚠ Skipping fine sweep for {sound_path} (no coarse results)")
    
    # Salva metadata
    metadata_file = OUTPUT_DIR / "variants_metadata.json"
    with open(metadata_file, 'w') as f:
        json.dump(all_metadata, f, indent=2)
    
    log(f"Generated {len(all_metadata)} total variants")
    log(f"Metadata saved: {metadata_file}")
    
    return len(all_metadata) > 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)