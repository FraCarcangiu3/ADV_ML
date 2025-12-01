#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
audio_converter.py
==================

Script per convertire file audio OGG in WAV e applicare pitch shift.

COSA FA QUESTO SCRIPT:
1. Converte file .ogg in .wav mono 44.1kHz
2. Applica pitch shift usando librosa
3. Salva i file con nomi appropriati

COME USARLO:
    python3 audio_converter.py

REQUISITI:
    - librosa
    - soundfile
    - numpy
"""

import os
import sys
import librosa
import soundfile as sf
import numpy as np
from pathlib import Path

# ==============================================================================
# CONFIGURAZIONE
# ==============================================================================

# Path delle cartelle
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
AC_AUDIO_DIR = os.path.join(os.path.dirname(PROJECT_DIR), "AC", "packages", "audio")
DATASET_ORIGINAL = os.path.join(PROJECT_DIR, "dataset", "original")
DATASET_OBFUSCATED = os.path.join(PROJECT_DIR, "dataset", "obfuscated")

# Parametri audio
SAMPLE_RATE = 44100  # 44.1kHz
MONO = True          # Mono channel
PITCH_SHIFT_CENTS = 100  # +100 cents = +1 semitone

# File da processare
AUDIO_FILES = [
    {
        "source": "weapon/shotgun.ogg",
        "original_name": "shotgun_ref.wav",
        "obfuscated_name": "shotgun_ref_p100.wav"
    },
    {
        "source": "player/footsteps.ogg", 
        "original_name": "footsteps_ref.wav",
        "obfuscated_name": "footsteps_ref_p100.wav"
    },
    {
        "source": "voicecom/affirmative.ogg",
        "original_name": "vc_affirmative_ref.wav", 
        "obfuscated_name": "vc_affirmative_ref_p100.wav"
    }
]

# ==============================================================================
# FUNZIONI HELPER
# ==============================================================================

def convert_ogg_to_wav(ogg_path, wav_path, target_sr=44100, mono=True):
    """
    Converte un file OGG in WAV con parametri specifici.
    
    Args:
        ogg_path (str): Path del file OGG di input
        wav_path (str): Path del file WAV di output
        target_sr (int): Sample rate target (default: 44100)
        mono (bool): Se True, converte in mono
    
    Returns:
        bool: True se conversione riuscita, False altrimenti
    """
    try:
        print(f"   📁 Caricamento: {os.path.basename(ogg_path)}")
        
        # Carica il file audio
        y, sr = librosa.load(ogg_path, sr=target_sr, mono=mono)
        
        print(f"   📊 Durata: {len(y)/target_sr:.2f}s, Sample rate: {sr}Hz")
        
        # Salva come WAV
        sf.write(wav_path, y, target_sr)
        
        print(f"   ✅ Salvato: {os.path.basename(wav_path)}")
        return True
        
    except Exception as e:
        print(f"   ❌ Errore: {str(e)}")
        return False


def apply_pitch_shift(wav_path, output_path, n_steps):
    """
    Applica pitch shift a un file WAV e salva il risultato.
    
    Args:
        wav_path (str): Path del file WAV di input
        output_path (str): Path del file WAV di output
        n_steps (float): Numero di semitoni per il pitch shift
    
    Returns:
        bool: True se pitch shift riuscito, False altrimenti
    """
    try:
        print(f"   🎵 Pitch shift: {n_steps} semitoni")
        
        # Carica il file
        y, sr = librosa.load(wav_path, sr=SAMPLE_RATE)
        
        # Applica pitch shift
        y_shifted = librosa.effects.pitch_shift(y, sr=sr, n_steps=n_steps)
        
        # Salva il risultato
        sf.write(output_path, y_shifted, sr)
        
        print(f"   ✅ Salvato: {os.path.basename(output_path)}")
        return True
        
    except Exception as e:
        print(f"   ❌ Errore pitch shift: {str(e)}")
        return False


def get_file_size(file_path):
    """Restituisce la dimensione del file in bytes."""
    try:
        return os.path.getsize(file_path)
    except:
        return 0


def format_size(size_bytes):
    """Formatta la dimensione in formato leggibile."""
    if size_bytes == 0:
        return "0 B"
    
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    
    return f"{size_bytes:.1f} TB"


# ==============================================================================
# FUNZIONE PRINCIPALE
# ==============================================================================

def main():
    """
    Funzione principale che coordina tutto il processo.
    """
    
    print("=" * 80)
    print("🎵  AUDIO CONVERTER - Dataset Population per AntiCheat ML")
    print("=" * 80)
    
    # Verifica cartelle
    print("\n📋 STEP 1: Verifica cartelle...")
    for folder in [DATASET_ORIGINAL, DATASET_OBFUSCATED]:
        if not os.path.exists(folder):
            os.makedirs(folder)
            print(f"   ✓ Creata: {folder}")
        else:
            print(f"   ✓ Esistente: {folder}")
    
    # Lista per il report
    report_data = []
    errors = []
    
    # Processa ogni file
    print(f"\n📋 STEP 2: Conversione file audio...")
    
    for i, file_info in enumerate(AUDIO_FILES, 1):
        print(f"\n🔍 File {i}/{len(AUDIO_FILES)}: {file_info['source']}")
        
        # Path completi
        ogg_path = os.path.join(AC_AUDIO_DIR, file_info['source'])
        original_wav = os.path.join(DATASET_ORIGINAL, file_info['original_name'])
        obfuscated_wav = os.path.join(DATASET_OBFUSCATED, file_info['obfuscated_name'])
        
        # Verifica file sorgente
        if not os.path.exists(ogg_path):
            error_msg = f"File sorgente non trovato: {ogg_path}"
            print(f"   ❌ {error_msg}")
            errors.append(error_msg)
            continue
        
        # Conversione OGG -> WAV
        print(f"   📁 Conversione: {os.path.basename(ogg_path)} -> {file_info['original_name']}")
        success = convert_ogg_to_wav(ogg_path, original_wav, SAMPLE_RATE, MONO)
        
        if not success:
            error_msg = f"Conversione fallita: {file_info['source']}"
            errors.append(error_msg)
            continue
        
        # Aggiungi al report
        original_size = get_file_size(original_wav)
        report_data.append({
            'type': 'original',
            'path': original_wav,
            'size': original_size,
            'source': file_info['source']
        })
        
        # Pitch shift
        print(f"   🎵 Pitch shift: {file_info['original_name']} -> {file_info['obfuscated_name']}")
        success = apply_pitch_shift(original_wav, obfuscated_wav, PITCH_SHIFT_CENTS/100)
        
        if not success:
            error_msg = f"Pitch shift fallito: {file_info['source']}"
            errors.append(error_msg)
            continue
        
        # Aggiungi al report
        obfuscated_size = get_file_size(obfuscated_wav)
        report_data.append({
            'type': 'obfuscated',
            'path': obfuscated_wav,
            'size': obfuscated_size,
            'source': file_info['source']
        })
    
    # Genera report
    print(f"\n📋 STEP 3: Generazione report...")
    
    report_path = os.path.join(os.path.dirname(PROJECT_DIR), ".cursor-output", "dataset_populate_report.txt")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("DATASET POPULATION REPORT\n")
        f.write("=" * 50 + "\n")
        f.write(f"Data: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Script: audio_converter.py\n")
        f.write(f"Pitch shift: +{PITCH_SHIFT_CENTS} cents (+{PITCH_SHIFT_CENTS/100:.1f} semitones)\n")
        f.write(f"Sample rate: {SAMPLE_RATE} Hz\n")
        f.write(f"Channels: {'Mono' if MONO else 'Stereo'}\n\n")
        
        f.write("FILE CREATI:\n")
        f.write("-" * 30 + "\n")
        
        # Raggruppa per tipo
        original_files = [f for f in report_data if f['type'] == 'original']
        obfuscated_files = [f for f in report_data if f['type'] == 'obfuscated']
        
        f.write(f"\nORIGINAL FILES ({len(original_files)}):\n")
        for file_info in original_files:
            f.write(f"  {file_info['path']} ({format_size(file_info['size'])})\n")
            f.write(f"    Source: {file_info['source']}\n")
        
        f.write(f"\nOBFUSCATED FILES ({len(obfuscated_files)}):\n")
        for file_info in obfuscated_files:
            f.write(f"  {file_info['path']} ({format_size(file_info['size'])})\n")
            f.write(f"    Source: {file_info['source']}\n")
        
        f.write(f"\nTOTALE FILE: {len(report_data)}\n")
        f.write(f"TOTALE DIMENSIONE: {format_size(sum(f['size'] for f in report_data))}\n")
        
        if errors:
            f.write(f"\nERRORI ({len(errors)}):\n")
            f.write("-" * 20 + "\n")
            for error in errors:
                f.write(f"  ❌ {error}\n")
        else:
            f.write(f"\n✅ NESSUN ERRORE\n")
    
    print(f"   ✅ Report salvato: {report_path}")
    
    # Riepilogo finale
    print("\n" + "=" * 80)
    print("✅ CONVERSIONE COMPLETATA!")
    print("=" * 80)
    print(f"📊 File processati: {len(AUDIO_FILES)}")
    print(f"📁 File originali creati: {len(original_files)}")
    print(f"🎵 File obfuscated creati: {len(obfuscated_files)}")
    print(f"❌ Errori: {len(errors)}")
    print(f"📄 Report: {report_path}")
    
    if errors:
        print(f"\n⚠️  ERRORI RILEVATI:")
        for error in errors:
            print(f"   • {error}")
    
    print("\n🎯 Prossimi step:")
    print("   1. Verifica i file in dataset/original/ e dataset/obfuscated/")
    print("   2. Esegui extract_features.py per estrarre le MFCC")
    print("   3. Addestra il classificatore con train_classifier.py")


# ==============================================================================
# ENTRY POINT
# ==============================================================================

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Processo interrotto dall'utente.")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ ERRORE CRITICO: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
