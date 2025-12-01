"""
test_audio_pipeline.py
Script per testare completamente la pipeline di perturbazione audio.

Verifica:
1. Caricamento FLAC dal dataset del collega
2. Applicazione delle perturbazioni (pitch, white noise, pink noise)
3. Analisi statistiche (zeri, RMS, SNR reale vs target)
4. Salvataggio esempi audio per verifica manuale
5. Confronto tra diverse perturbazioni

Autore: Francesco Carcangiu
Data: 2024-11-23
"""

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
    calculate_rms,
)


def analyze_audio(audio: np.ndarray, name: str = "Audio") -> dict:
    """
    Analizza statistiche dell'audio.
    
    Returns:
        Dizionario con statistiche
    """
    flat = audio.flatten()
    total_samples = flat.size
    zero_samples = (flat == 0).sum()
    nonzero_samples = (flat != 0).sum()
    
    stats = {
        "name": name,
        "shape": audio.shape,
        "total_samples": total_samples,
        "zero_samples": zero_samples,
        "nonzero_samples": nonzero_samples,
        "zero_percentage": (zero_samples / total_samples * 100) if total_samples > 0 else 0,
        "min": flat.min(),
        "max": flat.max(),
        "mean": flat.mean(),
        "std": flat.std(),
        "rms": calculate_rms(audio),
    }
    
    return stats


def print_stats(stats: dict):
    """Stampa statistiche in modo leggibile."""
    print(f"\n{'='*60}")
    print(f"Statistiche: {stats['name']}")
    print(f"{'='*60}")
    print(f"Shape:             {stats['shape']}")
    print(f"Total samples:     {stats['total_samples']:,}")
    print(f"Zero samples:      {stats['zero_samples']:,} ({stats['zero_percentage']:.2f}%)")
    print(f"Non-zero samples:  {stats['nonzero_samples']:,}")
    print(f"Min:               {stats['min']:.6f}")
    print(f"Max:               {stats['max']:.6f}")
    print(f"Mean:              {stats['mean']:.6f}")
    print(f"Std:               {stats['std']:.6f}")
    print(f"RMS:               {stats['rms']:.6f}")


def calculate_snr(signal: np.ndarray, noisy_signal: np.ndarray) -> float:
    """
    Calcola SNR reale tra segnale originale e segnale con rumore.
    
    SNR = 20 * log10(RMS_signal / RMS_noise)
    dove RMS_noise = RMS(noisy - signal)
    """
    noise = noisy_signal - signal
    rms_signal = calculate_rms(signal)
    rms_noise = calculate_rms(noise)
    
    if rms_noise < 1e-6:
        return float('inf')
    
    snr_db = 20.0 * np.log10(rms_signal / rms_noise)
    return snr_db


def test_single_file(flac_path: Path, output_dir: Path):
    """
    Testa tutte le perturbazioni su un singolo file FLAC.
    """
    print(f"\n{'#'*60}")
    print(f"# Testing: {flac_path.name}")
    print(f"{'#'*60}")
    
    # Carica FLAC originale
    print("\n[1/5] Caricamento FLAC originale...")
    audio, sr = sf.read(flac_path, dtype='float32')
    
    # Assicurati sia 2D
    if audio.ndim == 1:
        audio = audio[:, np.newaxis]
    
    print(f"   Sample rate: {sr} Hz")
    print(f"   Shape: {audio.shape} (frames, channels)")
    print(f"   Duration: {audio.shape[0] / sr:.2f} seconds")
    
    # Statistiche audio originale
    stats_orig = analyze_audio(audio, "Audio Originale")
    print_stats(stats_orig)
    
    # Test 1: Pitch Shift
    print("\n[2/5] Test Pitch Shift (±150 cents)...")
    pitch_cents = 150.0
    audio_pitch = apply_pitch_shift(audio, sr, pitch_cents)
    stats_pitch = analyze_audio(audio_pitch, f"Pitch Shift (+{pitch_cents} cents)")
    print_stats(stats_pitch)
    
    # Verifica lunghezza
    if audio_pitch.shape != audio.shape:
        print(f"   ⚠️  ATTENZIONE: Shape cambiato da {audio.shape} a {audio_pitch.shape}")
    else:
        print(f"   ✅ Shape mantenuto corretto: {audio_pitch.shape}")
    
    # Verifica zeri aggiunti
    zeros_added = stats_pitch['zero_samples'] - stats_orig['zero_samples']
    if zeros_added > 0:
        print(f"   ⚠️  Zeri aggiunti: {zeros_added:,} ({zeros_added/stats_pitch['total_samples']*100:.2f}%)")
        print(f"   📝 Questo è NORMALE per pitch shift (padding per mantenere lunghezza)")
    
    # Salva audio pitch
    output_pitch = output_dir / f"{flac_path.stem}_pitch_{int(pitch_cents)}.wav"
    sf.write(output_pitch, audio_pitch, sr)
    print(f"   💾 Salvato: {output_pitch.name}")
    
    # Test 2: White Noise
    print("\n[3/5] Test White Noise (SNR target: 40 dB, solo su segnale)...")
    target_snr = 40.0
    audio_white = add_white_noise(audio, target_snr, seed=42, only_on_signal=True)
    stats_white = analyze_audio(audio_white, f"White Noise (target SNR={target_snr} dB, solo su segnale)")
    print_stats(stats_white)
    
    # Calcola SNR reale
    real_snr_white = calculate_snr(audio, audio_white)
    print(f"   Target SNR:  {target_snr:.2f} dB")
    print(f"   Real SNR:    {real_snr_white:.2f} dB")
    print(f"   Differenza:  {abs(real_snr_white - target_snr):.2f} dB")
    
    if abs(real_snr_white - target_snr) < 1.0:
        print(f"   ✅ SNR corretto (differenza < 1 dB)")
    else:
        print(f"   ⚠️  SNR non preciso (differenza > 1 dB)")
    
    # Salva audio white noise
    output_white = output_dir / f"{flac_path.stem}_white_snr{int(target_snr)}.wav"
    sf.write(output_white, audio_white, sr)
    print(f"   💾 Salvato: {output_white.name}")
    
    # Test 3: Pink Noise
    print("\n[4/5] Test Pink Noise (SNR target: 40 dB, solo su segnale)...")
    audio_pink = add_pink_noise(audio, target_snr, seed=42, only_on_signal=True)
    stats_pink = analyze_audio(audio_pink, f"Pink Noise (target SNR={target_snr} dB, solo su segnale)")
    print_stats(stats_pink)
    
    # Calcola SNR reale
    real_snr_pink = calculate_snr(audio, audio_pink)
    print(f"   Target SNR:  {target_snr:.2f} dB")
    print(f"   Real SNR:    {real_snr_pink:.2f} dB")
    print(f"   Differenza:  {abs(real_snr_pink - target_snr):.2f} dB")
    
    if abs(real_snr_pink - target_snr) < 1.0:
        print(f"   ✅ SNR corretto (differenza < 1 dB)")
    else:
        print(f"   ⚠️  SNR non preciso (differenza > 1 dB)")
    
    # Salva audio pink noise
    output_pink = output_dir / f"{flac_path.stem}_pink_snr{int(target_snr)}.wav"
    sf.write(output_pink, audio_pink, sr)
    print(f"   💾 Salvato: {output_pink.name}")
    
    # Test 4: Confronto percentuali zeri
    print("\n[5/5] Confronto Percentuali Zeri...")
    print(f"   Originale:    {stats_orig['zero_percentage']:.2f}%")
    print(f"   Pitch Shift:  {stats_pitch['zero_percentage']:.2f}%")
    print(f"   White Noise:  {stats_white['zero_percentage']:.2f}%")
    print(f"   Pink Noise:   {stats_pink['zero_percentage']:.2f}%")
    print(f"\n   📝 Note: Con only_on_signal=True, i rumori mantengono i silenzi originali!")
    print(f"           Questo simula il comportamento reale: rumore solo durante lo sparo.")
    
    # Ritorna statistiche per analisi aggregata
    return {
        "orig": stats_orig,
        "pitch": stats_pitch,
        "white": stats_white,
        "pink": stats_pink,
        "snr_white": real_snr_white,
        "snr_pink": real_snr_pink,
    }


def main():
    """Funzione principale."""
    print("="*60)
    print("TEST PIPELINE PERTURBAZIONE AUDIO")
    print("="*60)
    
    # Path dataset
    dataset_root = Path("COLLEAGUE_BSc_Thesis/Data/audio/audio_loopback_flac")
    output_dir = Path("ADV_ML/tests/audio_samples")
    
    # Crea directory output
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Verifica esistenza dataset
    if not dataset_root.exists():
        print(f"\n❌ ERRORE: Dataset non trovato in {dataset_root}")
        print("   Assicurati di essere nella root del progetto.")
        return
    
    # Trova alcuni file FLAC per test
    flac_files = sorted(dataset_root.glob("*.flac"))
    
    if not flac_files:
        print(f"\n❌ ERRORE: Nessun file FLAC trovato in {dataset_root}")
        return
    
    print(f"\n✅ Trovati {len(flac_files)} file FLAC nel dataset")
    
    # Testa primi 3 file
    num_test_files = min(3, len(flac_files))
    print(f"📝 Testeremo i primi {num_test_files} file...")
    
    all_results = []
    
    for i, flac_path in enumerate(flac_files[:num_test_files]):
        try:
            results = test_single_file(flac_path, output_dir)
            all_results.append(results)
        except Exception as e:
            print(f"\n❌ ERRORE su {flac_path.name}: {e}")
            import traceback
            traceback.print_exc()
    
    # Statistiche aggregate
    if all_results:
        print("\n" + "="*60)
        print("STATISTICHE AGGREGATE")
        print("="*60)
        
        avg_zero_orig = np.mean([r['orig']['zero_percentage'] for r in all_results])
        avg_zero_pitch = np.mean([r['pitch']['zero_percentage'] for r in all_results])
        avg_zero_white = np.mean([r['white']['zero_percentage'] for r in all_results])
        avg_zero_pink = np.mean([r['pink']['zero_percentage'] for r in all_results])
        
        print(f"\nMedia Percentuale Zeri:")
        print(f"  Originale:    {avg_zero_orig:.2f}%")
        print(f"  Pitch Shift:  {avg_zero_pitch:.2f}%")
        print(f"  White Noise:  {avg_zero_white:.2f}%")
        print(f"  Pink Noise:   {avg_zero_pink:.2f}%")
        
        avg_snr_white = np.mean([r['snr_white'] for r in all_results])
        avg_snr_pink = np.mean([r['snr_pink'] for r in all_results])
        
        print(f"\nMedia SNR Reale:")
        print(f"  White Noise:  {avg_snr_white:.2f} dB (target: 40 dB)")
        print(f"  Pink Noise:   {avg_snr_pink:.2f} dB (target: 40 dB)")
        
        # Valutazione finale
        print("\n" + "="*60)
        print("VALUTAZIONE FINALE")
        print("="*60)
        
        issues = []
        
        # Check 1: Zeri nel pitch shift
        if avg_zero_pitch > 50:
            issues.append("⚠️  Pitch shift aggiunge molti zeri (>50%)")
            issues.append("   Questo è NORMALE ma potrebbe influenzare il modello ML")
            issues.append("   Soluzione: il modello deve gestire padding/silenzio")
        
        # Check 2: SNR precision
        if abs(avg_snr_white - 40.0) > 2.0:
            issues.append("⚠️  White noise SNR non preciso (>2 dB di differenza)")
        
        if abs(avg_snr_pink - 40.0) > 2.0:
            issues.append("⚠️  Pink noise SNR non preciso (>2 dB di differenza)")
        
        # Check 3: Zeri nel rumore (con only_on_signal=True, DOVREBBERO avere zeri!)
        if avg_zero_white < 50.0:
            issues.append("⚠️  White noise ha pochi zeri - verifica only_on_signal=True")
        
        if avg_zero_pink < 50.0:
            issues.append("⚠️  Pink noise ha pochi zeri - verifica only_on_signal=True")
        
        if not issues:
            print("✅ Tutti i test passati! Il sistema funziona correttamente.")
            print("\n📝 Note:")
            print("   - I molti zeri nel pitch shift sono NORMALI (mantenuti dall'originale)")
            print("   - I rumori mantengono gli zeri perché applicati SOLO sul segnale")
            print("   - Questo simula il comportamento reale: rumore solo durante lo sparo")
            print("   - Gli SNR sono precisi entro limiti accettabili")
        else:
            print("⚠️  Alcuni problemi rilevati:")
            for issue in issues:
                print(f"   {issue}")
        
        print(f"\n💾 Esempi audio salvati in: {output_dir}")
        print("   Puoi ascoltarli per verifica manuale.")
    
    print("\n" + "="*60)
    print("Test completato!")
    print("="*60)


if __name__ == "__main__":
    main()


