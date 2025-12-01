#!/usr/bin/env python3
"""
run_abx.py - Test ABX per discriminazione audio
Autore: Francesco Carcangiu
Data: 30 Ottobre 2025

Test ABX: dato A (ref), B (variant), X (uno dei due random), l'utente
deve indovinare se X == A o X == B.
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
            if p.startswith('snr'):
                return 'noise', int(p[3:])
    elif 'tone' in stem:
        for i, p in enumerate(parts):
            if p.endswith('hz'):
                return 'tone', int(p[:-2])
    
    return 'unknown', 0

def run_abx_test(sound_dir, subject_name, output_csv, num_trials=10):
    """Esegue test ABX"""
    sound_dir = Path(sound_dir)
    if not sound_dir.exists():
        print(f"ERROR: Directory not found: {sound_dir}")
        return
    
    # Trova file
    wav_files = list(sound_dir.glob("*.wav"))
    ref_file = [f for f in wav_files if 'ref' in f.name]
    variant_files = [f for f in wav_files if 'ref' not in f.name]
    
    if not ref_file or not variant_files:
        print("ERROR: Reference or variant files not found")
        return
    
    ref_file = ref_file[0]
    
    # Seleziona varianti random
    random.shuffle(variant_files)
    variant_files = variant_files[:num_trials]
    
    print("=" * 60)
    print(f"ABX TEST - {sound_dir.name}")
    print("=" * 60)
    print(f"Subject: {subject_name}")
    print(f"Trials: {len(variant_files)}")
    print("\nInstructions:")
    print("- You will hear A (reference), B (variant), then X (one of them)")
    print("- Guess if X is A or B")
    print("- Score >50% means you can discriminate")
    print("\nPress ENTER to start...")
    input()
    
    results = []
    correct = 0
    
    for i, variant in enumerate(variant_files, 1):
        print(f"\n--- Trial {i}/{len(variant_files)} ---")
        
        # Randomize X
        x_is_a = random.choice([True, False])
        x_file = ref_file if x_is_a else variant
        
        # Play sequence
        print("Playing A (reference)...")
        play_audio(ref_file)
        input("Press ENTER for B...")
        
        print("Playing B (variant)...")
        play_audio(variant)
        input("Press ENTER for X...")
        
        print("Playing X...")
        play_audio(x_file)
        
        # Collect answer
        answer = input("\nIs X = A or X = B? ").strip().upper()
        while answer not in ['A', 'B']:
            answer = input("Please enter A or B: ").strip().upper()
        
        # Check correctness
        is_correct = (answer == 'A' and x_is_a) or (answer == 'B' and not x_is_a)
        if is_correct:
            correct += 1
            print("✓ Correct!")
        else:
            print("✗ Wrong (X was", "A" if x_is_a else "B", ")")
        
        variant_type, value = get_variant_info(variant.name)
        
        results.append({
            'subject': subject_name,
            'trial': i,
            'variant_file': variant.name,
            'value': value,
            'type': variant_type,
            'x_was_a': x_is_a,
            'answer': answer,
            'correct': is_correct,
            'timestamp': datetime.now().isoformat()
        })
    
    # Save results
    output_path = Path(output_csv)
    file_exists = output_path.exists()
    
    with open(output_path, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'subject', 'trial', 'variant_file', 'value', 'type',
            'x_was_a', 'answer', 'correct', 'timestamp'
        ])
        if not file_exists:
            writer.writeheader()
        writer.writerows(results)
    
    print("\n" + "=" * 60)
    print(f"✓ ABX test complete! Results saved to: {output_csv}")
    print("=" * 60)
    
    # Summary
    accuracy = 100 * correct / len(results)
    print(f"\nResults:")
    print(f"- Correct: {correct}/{len(results)} ({accuracy:.1f}%)")
    
    if accuracy > 70:
        print("- Interpretation: You can CLEARLY discriminate")
    elif accuracy > 60:
        print("- Interpretation: You can discriminate (above chance)")
    elif accuracy > 50:
        print("- Interpretation: Slight discrimination (borderline)")
    else:
        print("- Interpretation: Cannot discriminate (at chance level)")

def main():
    parser = argparse.ArgumentParser(description="ABX discrimination test")
    parser.add_argument("sound_dir", help="Directory with audio variants")
    parser.add_argument("--subject", default="user", help="Subject name/ID")
    parser.add_argument("--output", default="ADV_ML/tests/subjective_results_abx.csv",
                       help="Output CSV file")
    parser.add_argument("--trials", type=int, default=10, help="Number of ABX trials")
    
    args = parser.parse_args()
    
    run_abx_test(args.sound_dir, args.subject, args.output, args.trials)

if __name__ == "__main__":
    main()

