#!/usr/bin/env python3
"""
snrdiff_auto.py - Calcola SNR tra file audio di riferimento e variante
Autore: Francesco Carcangiu
Data: 23 Ottobre 2025

Calcola RMS e SNR tra due file audio per la procedura coarse→fine:
- RMS del segnale di riferimento
- RMS del rumore (differenza tra test e ref)
- SNR in dB = 20 * log10(RMS_ref / RMS_noise)

Supporta anche batch processing per tutti i file in una directory.
"""

import sys
import numpy as np
import soundfile as sf
import argparse
import json
import csv
from pathlib import Path

def calculate_rms(signal):
    """Calcola RMS di un segnale"""
    return np.sqrt(np.mean(signal**2))

def calculate_snr(ref_path, test_path, output_format="json"):
    """
    Calcola SNR tra file di riferimento e test
    
    Args:
        ref_path: Path al file di riferimento
        test_path: Path al file di test
        output_format: "json" o "text"
    
    Returns:
        dict con rms_ref, rms_test, rms_noise, snr_db
    """
    try:
        # Carica i file
        ref_signal, ref_sr = sf.read(str(ref_path))
        test_signal, test_sr = sf.read(str(test_path))
        
        # Verifica sample rate compatibili
        if ref_sr != test_sr:
            print(f"WARNING: Sample rate mismatch: ref={ref_sr}, test={test_sr}", file=sys.stderr)
        
        # Allinea lunghezze (usa la più corta)
        min_len = min(len(ref_signal), len(test_signal))
        ref_signal = ref_signal[:min_len]
        test_signal = test_signal[:min_len]
        
        # Calcola RMS
        rms_ref = calculate_rms(ref_signal)
        rms_test = calculate_rms(test_signal)
        
        # Calcola rumore (differenza)
        noise_signal = test_signal - ref_signal
        rms_noise = calculate_rms(noise_signal)
        
        # Calcola SNR
        if rms_noise > 1e-10:  # Evita divisione per zero
            snr_db = 20 * np.log10(rms_ref / rms_noise)
        else:
            snr_db = float('inf')  # SNR infinito se rumore trascurabile
        
        result = {
            "rms_ref": float(rms_ref),
            "rms_test": float(rms_test), 
            "rms_noise": float(rms_noise),
            "snr_db": float(snr_db),
            "ref_file": str(ref_path),
            "test_file": str(test_path)
        }
        
        return result
        
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return None

def process_coarse_results():
    """Processa tutti i risultati coarse e genera CSV"""
    coarse_dir = Path("ADV_ML/tests/output/coarse")
    results_dir = Path("ADV_ML/tests/coarse_results")
    results_dir.mkdir(parents=True, exist_ok=True)
    
    # Trova tutti i suoni processati
    sound_dirs = [d for d in coarse_dir.iterdir() if d.is_dir()]
    
    for sound_dir in sound_dirs:
        sound_name = sound_dir.name
        log(f"Processing coarse results for: {sound_name}")
        
        # Trova file di riferimento
        ref_file = sound_dir / f"{sound_name}_ref.wav"
        if not ref_file.exists():
            print(f"WARNING: Reference file not found: {ref_file}", file=sys.stderr)
            continue
        
        # Trova tutti i file variante
        variant_files = [f for f in sound_dir.glob("*.wav") if f.name != ref_file.name]
        
        # Crea CSV per questo suono
        csv_file = results_dir / f"{sound_name}_coarse.csv"
        
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'file', 'trial', 'variant_type', 'applied_pitch_cents', 
                'applied_noise_snr_db', 'rms_ref', 'rms_test', 'rms_noise', 'snr_db'
            ])
            
            for variant_file in variant_files:
                # Parse filename per estrarre parametri
                filename = variant_file.stem
                parts = filename.split('__')
                
                if len(parts) >= 4:
                    trial = int(parts[4].split('-')[1])  # trial è in parts[4]
                    variant_type = parts[2].split('-')[1]  # type-p, type-n, type-w
                    
                    if variant_type == 'p':
                        # Pitch variant
                        pitch_str = parts[3].split('-')[1]
                        pitch_cents = int(pitch_str)
                        noise_snr = None
                    elif variant_type == 'n':
                        # Pitch variant negativo
                        pitch_str = parts[3].split('-')[1]
                        pitch_cents = -int(pitch_str)
                        noise_snr = None
                    elif variant_type == 'w':
                        # Noise variant
                        pitch_cents = None
                        noise_snr = int(parts[3].split('-')[1])
                    else:
                        pitch_cents = None
                        noise_snr = None
                    
                    # Calcola SNR
                    result = calculate_snr(ref_file, variant_file)
                    
                    if result:
                        writer.writerow([
                            variant_file.name,
                            trial,
                            'pitch' if variant_type in ['p', 'n'] else 'noise',
                            pitch_cents,
                            noise_snr,
                            result['rms_ref'],
                            result['rms_test'],
                            result['rms_noise'],
                            result['snr_db']
                        ])
        
        print(f"✓ Coarse results saved: {csv_file}")

def process_fine_results():
    """Processa tutti i risultati fine e genera CSV"""
    fine_dir = Path("ADV_ML/tests/output/fine")
    results_file = Path("ADV_ML/tests/TEST_RESULTS_FINE.csv")
    
    # Trova tutti i suoni processati
    sound_dirs = [d for d in fine_dir.iterdir() if d.is_dir()]
    
    all_results = []
    
    for sound_dir in sound_dirs:
        sound_name = sound_dir.name
        print(f"Processing fine results for: {sound_name}")
        
        # Trova file di riferimento (dalla directory coarse)
        ref_file = Path("ADV_ML/tests/output/coarse") / sound_name / f"{sound_name}_ref.wav"
        if not ref_file.exists():
            print(f"WARNING: Reference file not found: {ref_file}", file=sys.stderr)
            continue
        
        # Trova tutti i file variante
        variant_files = [f for f in sound_dir.glob("*.wav")]
        
        for variant_file in variant_files:
            # Parse filename per estrarre parametri
            filename = variant_file.stem
            parts = filename.split('__')
            
            if len(parts) >= 4:
                trial = int(parts[4].split('-')[1])  # trial è in parts[4]
                variant_type = parts[2].split('-')[1]  # type-p, type-n, type-w
                
                if variant_type == 'p':
                    # Pitch variant
                    pitch_str = parts[3].split('-')[1]
                    pitch_cents = float(pitch_str)
                    noise_snr = None
                elif variant_type == 'n':
                    # Pitch variant negativo
                    pitch_str = parts[3].split('-')[1]
                    pitch_cents = -float(pitch_str)
                    noise_snr = None
                elif variant_type == 'w':
                    # Noise variant
                    pitch_cents = None
                    noise_snr = int(parts[3].split('-')[1])
                else:
                    pitch_cents = None
                    noise_snr = None
                
                # Calcola SNR
                result = calculate_snr(ref_file, variant_file)
                
                if result:
                    all_results.append({
                        'sound': sound_name,
                        'file': variant_file.name,
                        'trial': trial,
                        'variant_type': 'pitch' if variant_type in ['p', 'n'] else 'noise',
                        'applied_pitch_cents': pitch_cents,
                        'applied_noise_snr_db': noise_snr,
                        'rms_ref': result['rms_ref'],
                        'rms_test': result['rms_test'],
                        'rms_noise': result['rms_noise'],
                        'snr_db': result['snr_db']
                    })
    
    # Salva tutti i risultati
    with open(results_file, 'w', newline='') as f:
        if all_results:
            writer = csv.DictWriter(f, fieldnames=all_results[0].keys())
            writer.writeheader()
            writer.writerows(all_results)
    
    print(f"✓ Fine results saved: {results_file}")
    return len(all_results)

def log(msg):
    """Log con timestamp"""
    print(f"[{__file__}] {msg}")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Calculate SNR between reference and test audio")
    parser.add_argument("ref_file", nargs='?', help="Reference audio file")
    parser.add_argument("test_file", nargs='?', help="Test audio file")
    parser.add_argument("--format", choices=["json", "text"], default="json", 
                       help="Output format")
    parser.add_argument("--quiet", action="store_true", help="Suppress warnings")
    parser.add_argument("--process-coarse", action="store_true", 
                       help="Process all coarse results and generate CSV")
    parser.add_argument("--process-fine", action="store_true",
                       help="Process all fine results and generate CSV")
    
    args = parser.parse_args()
    
    # Processa risultati batch
    if args.process_coarse:
        process_coarse_results()
        return 0
    
    if args.process_fine:
        count = process_fine_results()
        print(f"Processed {count} fine results")
        return 0
    
    # Calcola SNR singolo
    if not args.ref_file or not args.test_file:
        parser.error("ref_file and test_file are required for single SNR calculation")
    
    result = calculate_snr(args.ref_file, args.test_file, args.format)
    
    if result is None:
        sys.exit(1)
    
    # Output
    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        print(f"RMS_ref: {result['rms_ref']:.6f}")
        print(f"RMS_test: {result['rms_test']:.6f}")
        print(f"RMS_noise: {result['rms_noise']:.6f}")
        print(f"SNR_db: {result['snr_db']:.2f}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())