#!/usr/bin/env python3
"""
generate_audible_variants.py - Genera varianti ampie per test manuali
Autore: Francesco Carcangiu
Data: 30 Ottobre 2025

Genera varianti con range più ampi per permettere all'utente di decidere
min_perc e max_ok tramite ascolto guidato.
"""

import os
import sys
import subprocess
import numpy as np
import soundfile as sf
import librosa
from pathlib import Path

# ============================================================================
# CONFIGURAZIONE AUDIBLE VARIANTS
# ============================================================================

SOUNDS = [
    "AC/packages/audio/weapon/auto.ogg",
    "AC/packages/audio/player/footsteps.ogg",
    "AC/packages/audio/voicecom/affirmative.ogg"
]

# Range più ampi per test umani
PITCH_VALUES = [0, 10, 25, 50, 75, 100, 200]  # genera + e - (aggiunto ±200)
NOISE_SNR_VALUES = [40, 35, 30, 25, 20]  # dB (white)
PINK_NOISE_SNR_VALUES = [40, 35, 30]  # dB (pink)
TONE_FREQS = [8000, 9000, 10000, 11000, 12000]  # Hz
TONE_SNR = 35  # dB
EQ_TILTS_DB = [1, 3, 6]  # dB (±)

OUTPUT_DIR = Path("ADV_ML/tests/output/audible_variants")
PITCH_TEST_TOOL = "AC/tools/pitch_test"

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def log(msg):
    print(f"[{__file__}] {msg}")

def check_pitch_test_available():
    if os.path.exists(PITCH_TEST_TOOL) and os.access(PITCH_TEST_TOOL, os.X_OK):
        return True
    return False

def convert_ogg_to_wav(ogg_path, wav_path, sample_rate=44100):
    cmd = ["ffmpeg", "-y", "-i", str(ogg_path), "-ar", str(sample_rate), "-ac", "1", str(wav_path)]
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        return True
    except:
        return False

def apply_pitch_shift(input_wav, output_wav, cents, use_pitch_test=True):
    if use_pitch_test:
        cmd = [PITCH_TEST_TOOL, str(input_wav), str(output_wav), "--cents", str(cents)]
        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            return True
        except:
            pass
    # Fallback librosa
    try:
        y, sr = librosa.load(str(input_wav), sr=44100, mono=True)
        y_shifted = librosa.effects.pitch_shift(y, sr=sr, n_steps=cents/100.0)
        sf.write(str(output_wav), y_shifted, 44100)
        return True
    except Exception as e:
        log(f"ERROR: pitch shift failed: {e}")
        return False

def add_white_noise(input_wav, output_wav, target_snr_db):
    try:
        y, sr = librosa.load(str(input_wav), sr=44100, mono=True)
        rms_signal = np.sqrt(np.mean(y**2))
        if rms_signal < 1e-6:
            return False
        # seed deterministico per file
        np.random.seed(abs(hash(str(output_wav))) % (2**32))
        noise_amplitude = rms_signal / (10**(target_snr_db / 20.0))
        noise = np.random.normal(0, noise_amplitude, len(y))
        y_noisy = np.clip(y + noise, -1.0, 1.0)
        sf.write(str(output_wav), y_noisy, 44100)
        return True
    except Exception as e:
        log(f"ERROR: white noise failed: {e}")
        return False

def add_pink_noise(input_wav, output_wav, target_snr_db):
    try:
        y, sr = librosa.load(str(input_wav), sr=44100, mono=True)
        rms_signal = np.sqrt(np.mean(y**2))
        if rms_signal < 1e-6:
            return False
        n = len(y)
        # seed deterministico per file
        np.random.seed(abs(hash(str(output_wav))) % (2**32))
        # genera rumore bianco in frequenza e scala per 1/sqrt(f)
        white = np.random.normal(0, 1, n)
        # FFT
        Y = np.fft.rfft(white)
        freqs = np.fft.rfftfreq(n, d=1/44100)
        freqs[0] = 1.0  # evita divisione per zero
        shaping = 1.0 / np.sqrt(freqs)
        Y_shaped = Y * shaping
        pink = np.fft.irfft(Y_shaped, n=n)
        # normalizza e scala a SNR target
        pink = pink / (np.sqrt(np.mean(pink**2)) + 1e-12)
        noise_amplitude = rms_signal / (10**(target_snr_db / 20.0))
        pink = pink * noise_amplitude
        y_noisy = np.clip(y + pink, -1.0, 1.0)
        sf.write(str(output_wav), y_noisy, 44100)
        return True
    except Exception as e:
        log(f"ERROR: pink noise failed: {e}")
        return False

def add_tone(input_wav, output_wav, freq_hz, target_snr_db):
    try:
        y, sr = librosa.load(str(input_wav), sr=44100, mono=True)
        rms_signal = np.sqrt(np.mean(y**2))
        if rms_signal < 1e-6:
            return False
        # seed deterministico per file (fase random opzionale)
        np.random.seed(abs(hash(str(output_wav))) % (2**32))
        tone_amplitude = rms_signal / (10**(target_snr_db / 20.0))
        t = np.arange(len(y)) / 44100
        phase = np.random.uniform(0, 2*np.pi)
        tone = tone_amplitude * np.sin(2 * np.pi * freq_hz * t + phase)
        y_toned = np.clip(y + tone, -1.0, 1.0)
        sf.write(str(output_wav), y_toned, 44100)
        return True
    except Exception as e:
        log(f"ERROR: tone injection failed: {e}")
        return False

def apply_eq_tilt_fft(input_wav, output_wav, tilt_db: float):
    """Applica un tilt (shelving lineare) in dB tra 0 Hz e Nyquist via FFT."""
    try:
        y, sr = librosa.load(str(input_wav), sr=44100, mono=True)
        n = len(y)
        Y = np.fft.rfft(y)
        freqs = np.fft.rfftfreq(n, d=1/sr)
        # curva lineare in dB: -tilt a DC, +tilt a Nyquist (o viceversa)
        slope_db = np.linspace(-tilt_db, tilt_db, len(freqs))
        gain = 10 ** (slope_db / 20.0)
        Y_tilt = Y * gain
        y_tilt = np.fft.irfft(Y_tilt, n=n)
        y_tilt = np.clip(y_tilt, -1.0, 1.0)
        sf.write(str(output_wav), y_tilt, sr)
        return True
    except Exception as e:
        log(f"ERROR: EQ tilt failed: {e}")
        return False

# ============================================================================
# MAIN GENERATION
# ============================================================================

def generate_variants_for_sound(sound_path):
    log(f"Generating audible variants for: {sound_path}")
    
    base_name = Path(sound_path).stem
    sound_dir = OUTPUT_DIR / base_name
    sound_dir.mkdir(parents=True, exist_ok=True)
    
    # Convert reference
    ref_wav = sound_dir / f"{base_name}_ref.wav"
    if not convert_ogg_to_wav(sound_path, ref_wav):
        log(f"ERROR: Failed to convert {sound_path}")
        return []
    
    use_pitch_test = check_pitch_test_available()
    generated = []
    
    # 1. Pitch variants
    for pitch_cents in PITCH_VALUES:
        # Positive
        output_name = f"{base_name}_pitch_p{pitch_cents}.wav"
        output_wav = sound_dir / output_name
        if apply_pitch_shift(ref_wav, output_wav, pitch_cents, use_pitch_test):
            generated.append(output_name)
            log(f"  Created: {output_name}")
        
        # Negative
        if pitch_cents != 0:
            output_name = f"{base_name}_pitch_n{pitch_cents}.wav"
            output_wav = sound_dir / output_name
            if apply_pitch_shift(ref_wav, output_wav, -pitch_cents, use_pitch_test):
                generated.append(output_name)
                log(f"  Created: {output_name}")
    
    # 2. Noise variants (white)
    for snr_db in NOISE_SNR_VALUES:
        output_name = f"{base_name}_noise_snr{snr_db}.wav"
        output_wav = sound_dir / output_name
        if add_white_noise(ref_wav, output_wav, snr_db):
            generated.append(output_name)
            log(f"  Created: {output_name}")

    # 2b. Noise variants (pink)
    for snr_db in PINK_NOISE_SNR_VALUES:
        output_name = f"{base_name}_noise_pink_snr{snr_db}.wav"
        output_wav = sound_dir / output_name
        if add_pink_noise(ref_wav, output_wav, snr_db):
            generated.append(output_name)
            log(f"  Created: {output_name}")
    
    # 3. Tone variants
    for freq in TONE_FREQS:
        output_name = f"{base_name}_tone_{freq}hz.wav"
        output_wav = sound_dir / output_name
        if add_tone(ref_wav, output_wav, freq, TONE_SNR):
            generated.append(output_name)
            log(f"  Created: {output_name}")

    # 4. EQ tilt variants (±1, ±3, ±6 dB)
    for tilt in EQ_TILTS_DB:
        for sign, tag in [(+1, "p"), (-1, "m")]:
            val = sign * tilt
            output_name = f"{base_name}_eq_tilt_{tag}{tilt}dB.wav"
            output_wav = sound_dir / output_name
            if apply_eq_tilt_fft(ref_wav, output_wav, val):
                generated.append(output_name)
                log(f"  Created: {output_name}")

    # 5. Simple combinations
    # (a) pitch ±25 + white noise 35 dB
    for sign, tag in [(+1, "p"), (-1, "n")]:
        output_name = f"{base_name}_combo_pitch{tag}25_noise35.wav"
        temp = sound_dir / f"._tmp_{base_name}_p{tag}25.wav"
        out = sound_dir / output_name
        if apply_pitch_shift(ref_wav, temp, sign * 25, use_pitch_test) and add_white_noise(temp, out, 35):
            try:
                os.remove(temp)
            except Exception:
                pass
            generated.append(output_name)
            log(f"  Created: {output_name}")
    # (b) pitch ±10 + tone 10kHz @ 35 dB
    for sign, tag in [(+1, "p"), (-1, "n")]:
        output_name = f"{base_name}_combo_pitch{tag}10_tone10khz.wav"
        temp = sound_dir / f"._tmp_{base_name}_p{tag}10.wav"
        out = sound_dir / output_name
        if apply_pitch_shift(ref_wav, temp, sign * 10, use_pitch_test) and add_tone(temp, out, 10000, 35):
            try:
                os.remove(temp)
            except Exception:
                pass
            generated.append(output_name)
            log(f"  Created: {output_name}")
    # (c) EQ ±3 dB + white noise 35 dB
    for sign, tag in [(+1, "p"), (-1, "m")]:
        output_name = f"{base_name}_combo_eq{tag}3_noise35.wav"
        temp = sound_dir / f"._tmp_{base_name}_eq{tag}3.wav"
        out = sound_dir / output_name
        if apply_eq_tilt_fft(ref_wav, temp, sign * 3) and add_white_noise(temp, out, 35):
            try:
                os.remove(temp)
            except Exception:
                pass
            generated.append(output_name)
            log(f"  Created: {output_name}")

    # 6. Sidecar .txt per tracciabilità
    for name in generated:
        sidecar = sound_dir / (Path(name).stem + ".txt")
        try:
            with open(sidecar, "w") as fh:
                fh.write(f"source={sound_path}\n")
                fh.write(f"output={name}\n")
                if "_pitch_" in name:
                    fh.write("type=pitch\n")
                elif "_noise_pink_" in name:
                    fh.write("type=noise_pink\n")
                elif "_noise_" in name:
                    fh.write("type=noise_white\n")
                elif "_tone_" in name:
                    fh.write("type=tone\n")
                elif "_eq_tilt_" in name:
                    fh.write("type=eq_tilt\n")
                elif "_combo_" in name:
                    fh.write("type=combo\n")
                else:
                    fh.write("type=unknown\n")
                fh.write(f"seed={(abs(hash(str(sound_dir/name))) % (2**32))}\n")
        except Exception:
            pass
    
    log(f"Generated {len(generated)} variants for {base_name}")
    return generated

def main():
    log("Starting audible variants generation...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    all_files = {}
    for sound_path in SOUNDS:
        if os.path.exists(sound_path):
            files = generate_variants_for_sound(sound_path)
            all_files[Path(sound_path).stem] = files
        else:
            log(f"WARNING: Sound not found: {sound_path}")
    
    log("=" * 50)
    log("Generation complete!")
    for sound, files in all_files.items():
        log(f"{sound}: {len(files)} files")
    
    return all_files

if __name__ == "__main__":
    main()

