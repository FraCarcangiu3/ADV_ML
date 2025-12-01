#!/usr/bin/env python3
"""
human_test_cli.py - CLI interattivo per test soggettivi guidati
Autore: Francesco Carcangiu  
Data: 30 Ottobre 2025

Riproduce varianti audio in ordine casuale e raccoglie feedback dell'utente.
"""

import os
import sys
import subprocess
import random
import csv
from pathlib import Path
from datetime import datetime
import argparse

def play_audio(file_path, player="afplay"):
    """Riproduce un file audio"""
    if player == "afplay" and sys.platform == "darwin":
        cmd = ["afplay", str(file_path)]
    else:
        cmd = ["ffplay", "-nodisp", "-autoexit", str(file_path)]
    
    try:
        subprocess.run(cmd, check=True, stderr=subprocess.DEVNULL)
        return True
    except:
        return False

def get_variant_info(filename):
    """Estrae tipo e valore dal nome file"""
    stem = Path(filename).stem
    parts = stem.split('_')
    
    if 'pitch' in stem:
        for i, p in enumerate(parts):
            if p == 'pitch' and i+1 < len(parts):
                val = parts[i+1]
                sign = -1 if val.startswith('n') else 1
                cents = int(val[1:]) * sign
                return 'pitch', cents
    elif 'noise' in stem:
        for i, p in enumerate(parts):
            if p == 'snr' and i-1 >= 0:
                continue
            if p.startswith('snr'):
                return 'noise', int(p[3:])
    elif 'tone' in stem:
        for i, p in enumerate(parts):
            if p.endswith('hz'):
                return 'tone', int(p[:-2])
    
    return 'unknown', 0

def run_listening_test(sound_dir, subject_name, output_csv, num_samples=None):
    """Esegue il test di ascolto guidato"""
    sound_dir = Path(sound_dir)
    if not sound_dir.exists():
        print(f"ERROR: Directory not found: {sound_dir}")
        return
    
    # Trova file
    wav_files = list(sound_dir.glob("*.wav"))
    ref_file = [f for f in wav_files if 'ref' in f.name]
    variant_files = [f for f in wav_files if 'ref' not in f.name]
    
    if not ref_file:
        print("ERROR: Reference file (*_ref.wav) not found")
        return
    
    ref_file = ref_file[0]
    
    # Randomizza
    random.shuffle(variant_files)
    if num_samples:
        variant_files = variant_files[:num_samples]
    
    print("=" * 60)
    print(f"LISTENING TEST - {sound_dir.name}")
    print("=" * 60)
    print(f"Subject: {subject_name}")
    print(f"Variants to test: {len(variant_files)}")
    print("\nInstructions:")
    print("- You will hear the REFERENCE first, then a VARIANT")
    print("- Answer if you perceived a change (Y/N)")
    print("- Rate severity (1=barely noticeable, 5=very obvious)")
    print("- Add optional notes")
    print("\nPress ENTER to start...")
    input()
    
    results = []
    
    for i, variant in enumerate(variant_files, 1):
        print(f"\n--- Test {i}/{len(variant_files)} ---")
        
        # Play reference
        print("Playing REFERENCE...")
        play_audio(ref_file)
        
        # Play variant
        print(f"Playing VARIANT: {variant.name}")
        play_audio(variant)
        
        # Collect feedback
        perceived = input("Perceived change? (Y/N): ").strip().upper()
        while perceived not in ['Y', 'N']:
            perceived = input("Please enter Y or N: ").strip().upper()
        
        severity = 0
        if perceived == 'Y':
            severity = input("Severity (1-5, 1=barely, 5=obvious): ").strip()
            while not severity.isdigit() or int(severity) not in range(1, 6):
                severity = input("Please enter 1-5: ").strip()
            severity = int(severity)
        
        notes = input("Notes (optional, press ENTER to skip): ").strip()
        
        variant_type, value = get_variant_info(variant.name)
        
        results.append({
            'subject': subject_name,
            'file': variant.name,
            'value': value,
            'type': variant_type,
            'perceived_change': perceived,
            'severity': severity,
            'notes': notes,
            'timestamp': datetime.now().isoformat()
        })
        
        print("✓ Recorded")
    
    # Save results
    output_path = Path(output_csv)
    file_exists = output_path.exists()
    
    with open(output_path, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'subject', 'file', 'value', 'type', 'perceived_change', 
            'severity', 'notes', 'timestamp'
        ])
        if not file_exists:
            writer.writeheader()
        writer.writerows(results)
    
    print("\n" + "=" * 60)
    print(f"✓ Test complete! Results saved to: {output_csv}")
    print("=" * 60)
    
    # Quick summary
    perceived_count = sum(1 for r in results if r['perceived_change'] == 'Y')
    print(f"\nQuick summary:")
    print(f"- Perceived changes: {perceived_count}/{len(results)} ({100*perceived_count/len(results):.1f}%)")
    if perceived_count > 0:
        avg_severity = sum(r['severity'] for r in results if r['severity'] > 0) / perceived_count
        print(f"- Average severity: {avg_severity:.1f}/5")

def main():
    parser = argparse.ArgumentParser(description="Interactive listening test CLI")
    parser.add_argument("sound_dir", help="Directory with audio variants")
    parser.add_argument("--subject", default="user", help="Subject name/ID")
    parser.add_argument("--output", default="ADV_ML/tests/subjective_results.csv", 
                       help="Output CSV file")
    parser.add_argument("--num", type=int, help="Number of samples to test (default: all)")
    
    args = parser.parse_args()
    
    run_listening_test(args.sound_dir, args.subject, args.output, args.num)

if __name__ == "__main__":
    main()

