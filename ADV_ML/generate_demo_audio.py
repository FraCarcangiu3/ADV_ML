"""
generate_demo_audio.py
Script per generare esempi audio per i professori.

Crea una cartella con:
- Audio originali (FLAC)
- Audio modificati con tutte le perturbazioni (WAV)
- Organizzati per tipo di perturbazione

Uso:
    python ADV_ML/generate_demo_audio.py --num-samples 5

Autore: Francesco Carcangiu
Data: 2024-11-23
"""

import argparse
import sys
from pathlib import Path
import numpy as np
import soundfile as sf

# Aggiungi path per importare moduli locali
sys.path.insert(0, str(Path(__file__).parent))

from audio_effects import (
    apply_pitch_shift,
    add_white_noise,
    add_pink_noise,
    apply_eq_tilt,
    apply_highpass,
    apply_lowpass,
)


def generate_demo_audio(flac_path: Path, output_dir: Path, sample_rate: int = 96000):
    """
    Genera tutti gli esempi audio per un singolo FLAC.
    
    Args:
        flac_path: Path al file FLAC originale
        output_dir: Directory dove salvare gli esempi
        sample_rate: Sample rate per salvare i WAV (default: 96000)
    """
    print(f"\n{'='*60}")
    print(f"Processing: {flac_path.name}")
    print(f"{'='*60}")
    
    # Carica FLAC originale
    audio, sr = sf.read(flac_path, dtype='float32')
    
    # Assicurati sia 2D
    if audio.ndim == 1:
        audio = audio[:, np.newaxis]
    
    # Crea sottocartelle
    base_name = flac_path.stem
    (output_dir / "00_ORIGINALI").mkdir(parents=True, exist_ok=True)
    (output_dir / "01_PITCH").mkdir(parents=True, exist_ok=True)
    (output_dir / "02_WHITE_NOISE").mkdir(parents=True, exist_ok=True)
    (output_dir / "03_PINK_NOISE").mkdir(parents=True, exist_ok=True)
    (output_dir / "04_EQ_TILT").mkdir(parents=True, exist_ok=True)
    (output_dir / "05_HIGHPASS").mkdir(parents=True, exist_ok=True)
    (output_dir / "06_LOWPASS").mkdir(parents=True, exist_ok=True)
    
    # 1. Salva originale (converti FLAC → WAV)
    print("\n[1/7] Salvataggio originale...")
    orig_path = output_dir / "00_ORIGINALI" / f"{base_name}_ORIGINALE.wav"
    sf.write(orig_path, audio, sr)
    print(f"   ✅ Salvato: {orig_path.name}")
    
    # 2. Pitch Shift - vari livelli
    print("\n[2/7] Generazione Pitch Shift...")
    pitch_levels = [
        ("P1_light", 100),
        ("P2_medium", 150),
        ("P3_strong", 200),
        ("P_neg_light", -100),
        ("P_neg_medium", -150),
        ("P_neg_strong", -200),
    ]
    
    for name, cents in pitch_levels:
        audio_pitch = apply_pitch_shift(audio.copy(), sr, cents)
        pitch_path = output_dir / "01_PITCH" / f"{base_name}_pitch_{name}_{cents:+d}cents.wav"
        sf.write(pitch_path, audio_pitch, sr)
        print(f"   ✅ {name}: {cents:+d} cents")
    
    # 3. White Noise - vari livelli SNR
    print("\n[3/7] Generazione White Noise...")
    white_levels = [
        ("W1_light", 38),
        ("W2_medium", 40),
        ("W3_strong", 42),
    ]
    
    for name, snr in white_levels:
        audio_white = add_white_noise(audio.copy(), snr, seed=42, only_on_signal=True)
        white_path = output_dir / "02_WHITE_NOISE" / f"{base_name}_white_{name}_SNR{snr}dB.wav"
        sf.write(white_path, audio_white, sr)
        print(f"   ✅ {name}: SNR={snr} dB")
    
    # 4. Pink Noise - vari livelli SNR
    print("\n[4/7] Generazione Pink Noise...")
    pink_levels = [
        ("K1_light", 18),
        ("K2_strong", 22),
    ]
    
    for name, snr in pink_levels:
        audio_pink = add_pink_noise(audio.copy(), snr, seed=42, only_on_signal=True)
        pink_path = output_dir / "03_PINK_NOISE" / f"{base_name}_pink_{name}_SNR{snr}dB.wav"
        sf.write(pink_path, audio_pink, sr)
        print(f"   ✅ {name}: SNR={snr} dB")
    
    # 5. EQ Tilt - boost e cut
    print("\n[5/7] Generazione EQ Tilt...")
    eq_levels = [
        ("boost_light", 3.0),
        ("boost_medium", 4.5),
        ("boost_strong", 6.0),
        ("cut_light", -3.0),
        ("cut_medium", -4.5),
        ("cut_strong", -6.0),
    ]
    
    for name, tilt in eq_levels:
        audio_eq = apply_eq_tilt(audio.copy(), sr, tilt)
        eq_path = output_dir / "04_EQ_TILT" / f"{base_name}_eq_{name}_{tilt:+.1f}dB.wav"
        sf.write(eq_path, audio_eq, sr)
        print(f"   ✅ {name}: {tilt:+.1f} dB")
    
    # 6. High-Pass Filter
    print("\n[6/7] Generazione High-Pass Filter...")
    hp_levels = [
        ("HP_150Hz", 150),
        ("HP_200Hz", 200),
        ("HP_250Hz", 250),
    ]
    
    for name, cutoff in hp_levels:
        audio_hp = apply_highpass(audio.copy(), sr, cutoff)
        hp_path = output_dir / "05_HIGHPASS" / f"{base_name}_highpass_{name}.wav"
        sf.write(hp_path, audio_hp, sr)
        print(f"   ✅ {name}: {cutoff} Hz")
    
    # 7. Low-Pass Filter
    print("\n[7/7] Generazione Low-Pass Filter...")
    lp_levels = [
        ("LP_8000Hz", 8000),
        ("LP_10000Hz", 10000),
        ("LP_12000Hz", 12000),
    ]
    
    for name, cutoff in lp_levels:
        audio_lp = apply_lowpass(audio.copy(), sr, cutoff)
        lp_path = output_dir / "06_LOWPASS" / f"{base_name}_lowpass_{name}.wav"
        sf.write(lp_path, audio_lp, sr)
        print(f"   ✅ {name}: {cutoff} Hz")
    
    print(f"\n✅ Completato: {base_name}")
    print(f"   Totale file generati: {1 + len(pitch_levels) + len(white_levels) + len(pink_levels) + len(eq_levels) + len(hp_levels) + len(lp_levels)}")


def create_readme(output_dir: Path):
    """Crea un README nella cartella output."""
    readme_content = """# 🎵 Esempi Audio per Professori

Questa cartella contiene esempi di audio originali e modificati per dimostrare le perturbazioni applicate.

## 📁 Struttura Cartelle

- **00_ORIGINALI/** - Audio FLAC originali convertiti in WAV
- **01_PITCH/** - Pitch shift (modifica frequenza)
- **02_WHITE_NOISE/** - Rumore bianco aggiunto
- **03_PINK_NOISE/** - Rumore rosa aggiunto
- **04_EQ_TILT/** - Equalizzazione (boost/cut)
- **05_HIGHPASS/** - Filtro passa-alto
- **06_LOWPASS/** - Filtro passa-basso

## 🎯 Come Ascoltare

1. **Inizia con 00_ORIGINALI/** - Ascolta l'audio originale
2. **Poi confronta con le modifiche** - Ogni cartella contiene vari livelli
3. **Nomi file** - Contengono i parametri usati (es. `+150cents`, `SNR40dB`)

## 📊 Livelli di Perturbazione

### Pitch Shift
- **P1_light**: ±100 cents (leggero)
- **P2_medium**: ±150 cents (medio)
- **P3_strong**: ±200 cents (forte)
- **P_neg_***: Pitch negativo (più grave)

### White Noise
- **W1_light**: SNR 38 dB (rumore leggero)
- **W2_medium**: SNR 40 dB (rumore medio)
- **W3_strong**: SNR 42 dB (rumore forte)

### Pink Noise
- **K1_light**: SNR 18 dB (rumore leggero)
- **K2_strong**: SNR 22 dB (rumore forte)

### EQ Tilt
- **boost_***: Aumenta frequenze alte (più brillante)
- **cut_***: Riduce frequenze alte (più scuro)

### Filtri
- **High-Pass**: Rimuove frequenze basse
- **Low-Pass**: Rimuove frequenze alte

## ⚠️ Nota Importante

Il rumore (white/pink noise) viene applicato **SOLO durante lo sparo**, non sul silenzio.
Questo simula il comportamento reale del gioco.

## 📝 Formato

Tutti i file sono in formato WAV a 96 kHz per compatibilità con tutti i player audio.

---
Generato automaticamente con `generate_demo_audio.py`
"""
    
    readme_path = output_dir / "README.md"
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    print(f"\n📝 README creato: {readme_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Genera esempi audio per i professori"
    )
    parser.add_argument(
        "--dataset-root",
        type=Path,
        default=Path("COLLEAGUE_BSc_Thesis/Data/audio/audio_loopback_flac"),
        help="Percorso alla cartella con FLAC originali"
    )
    parser.add_argument(
        "--num-samples",
        type=int,
        default=5,
        help="Numero di file FLAC da processare (default: 5)"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("ADV_ML/demo_audio_for_professors"),
        help="Cartella dove salvare gli esempi (default: ADV_ML/demo_audio_for_professors)"
    )
    
    args = parser.parse_args()
    
    print("="*60)
    print("GENERAZIONE ESEMPI AUDIO PER PROFESSORI")
    print("="*60)
    
    # Verifica dataset
    if not args.dataset_root.exists():
        print(f"\n❌ ERRORE: Dataset non trovato in {args.dataset_root}")
        print("   Assicurati di essere nella root del progetto.")
        return
    
    # Trova FLAC
    flac_files = sorted(args.dataset_root.glob("*.flac"))
    
    if not flac_files:
        print(f"\n❌ ERRORE: Nessun file FLAC trovato in {args.dataset_root}")
        return
    
    print(f"\n✅ Trovati {len(flac_files)} file FLAC nel dataset")
    print(f"📝 Processeremo i primi {args.num_samples} file...")
    
    # Crea directory output
    args.output_dir.mkdir(parents=True, exist_ok=True)
    
    # Processa file
    num_to_process = min(args.num_samples, len(flac_files))
    processed = 0
    
    for flac_path in flac_files[:num_to_process]:
        try:
            generate_demo_audio(flac_path, args.output_dir)
            processed += 1
        except Exception as e:
            print(f"\n❌ ERRORE su {flac_path.name}: {e}")
            import traceback
            traceback.print_exc()
    
    # Crea README
    create_readme(args.output_dir)
    
    # Riepilogo
    print("\n" + "="*60)
    print("RIEPILOGO")
    print("="*60)
    print(f"✅ File processati: {processed}/{num_to_process}")
    print(f"📁 Cartella output: {args.output_dir}")
    print(f"\n📂 Struttura creata:")
    print(f"   {args.output_dir}/00_ORIGINALI/")
    print(f"   {args.output_dir}/01_PITCH/")
    print(f"   {args.output_dir}/02_WHITE_NOISE/")
    print(f"   {args.output_dir}/03_PINK_NOISE/")
    print(f"   {args.output_dir}/04_EQ_TILT/")
    print(f"   {args.output_dir}/05_HIGHPASS/")
    print(f"   {args.output_dir}/06_LOWPASS/")
    print(f"\n🎧 Puoi ora aprire la cartella e far ascoltare i file ai professori!")
    print("="*60)


if __name__ == "__main__":
    main()

