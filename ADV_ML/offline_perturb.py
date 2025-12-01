"""
offline_perturb.py
Script per applicare perturbazioni audio offline ai FLAC del collega.

Questo script:
1. Carica FLAC dal dataset del collega
2. Applica una perturbazione specifica (pitch, noise, EQ, ecc.)
3. Estrae le feature nello stesso formato di convert_flac_to_csv.py
4. Genera X_test_pert pronto per l'uso nel modello ML

Uso da linea di comando:
    python offline_perturb.py --dataset-root COLLEAGUE_BSc_Thesis/Data/audio/audio_loopback_flac \\
                              --perturbation pitch \\
                              --mode random_like_client \\
                              --num-samples 100 \\
                              --output-csv ADV_ML/output/X_test_pitch_random.csv

Uso come modulo:
    from offline_perturb import build_X_test_pert, perturb
    
    X_test_pert = build_X_test_pert(flac_paths, "pitch", {"mode": "random", "min_cents": -200, "max_cents": 200})

Autore: Francesco Carcangiu
Data: 2024-11-21
"""

import argparse
import json
from pathlib import Path
from typing import Dict, List, Literal, Optional

import numpy as np
import soundfile as sf

from audio_effects import (
    apply_pitch_shift,
    add_white_noise,
    add_pink_noise,
    apply_eq_tilt,
    apply_highpass,
    apply_lowpass,
    sample_pitch_from_range,
    sample_snr_from_range,
    sample_eq_tilt_from_range,
    sample_filter_cutoff_from_range,
)


# ========================================================================
# Caricamento e estrazione feature (replica convert_flac_to_csv.py)
# ========================================================================

def load_flac_as_features(flac_path: Path) -> np.ndarray:
    """
    Carica un FLAC e lo converte in formato feature (come convert_flac_to_csv.py).
    
    Nel convert_flac_to_csv.py del collega:
        - Carica FLAC con soundfile.read() → array float32
        - Salva direttamente in CSV (8 colonne per 8 canali)
    
    Per ora, restituiamo l'array raw (potrebbe essere necessario flatten o estrarre
    feature statistiche in futuro, ma per ora manteniamo compatibilità con CSV raw).
    
    Args:
        flac_path: Path al file FLAC
    
    Returns:
        Array numpy [frames, channels] o flattened [frames * channels]
    """
    data, samplerate = sf.read(flac_path, dtype="float32")
    
    # Assicurati che sia 2D se multi-canale
    if data.ndim == 1:
        data = data[:, np.newaxis]
    
    return data


def extract_features_from_audio(audio_data: np.ndarray) -> np.ndarray:
    """
    Estrae feature da audio (per ora: raw flatten, come CSV del collega).
    
    Nel futuro, potrebbe essere necessario estrarre feature statistiche o spettrali,
    ma per ora manteniamo compatibilità con il formato CSV raw del collega.
    
    Args:
        audio_data: Array [frames, channels]
    
    Returns:
        Feature vector (flattened o feature estratte)
    """
    # Per ora: flatten semplice (come CSV del collega)
    # In futuro: potrebbe essere necessario estrarre feature statistiche/spettrali
    return audio_data.flatten()


# ========================================================================
# Applicazione perturbazioni
# ========================================================================

def apply_perturbation_to_flac(
    flac_path: Path,
    perturbation_type: str,
    perturbation_config: Dict,
    verbose: bool = False
) -> np.ndarray:
    """
    Applica una perturbazione a un singolo FLAC e restituisce le feature.
    
    Steps:
        1. Carica il FLAC
        2. Applica la perturbazione usando audio_effects.py
        3. Estrae le feature nello stesso formato del collega
        4. Restituisce vettore feature (1 sample)
    
    Args:
        flac_path: Path al file FLAC
        perturbation_type: Tipo di perturbazione ("pitch", "white_noise", "pink_noise", 
                          "eq_tilt", "highpass", "lowpass", "combo")
        perturbation_config: Dizionario con parametri della perturbazione:
            - Per pitch: {"cents": float} o {"mode": "random", "min_cents": float, "max_cents": float}
            - Per noise: {"snr_db": float} o {"mode": "random", "min_snr": float, "max_snr": float}
            - Per EQ: {"tilt_db": float} o {"mode": "random", "boost_min": float, ...}
            - Per filtri: {"cutoff_hz": float} o {"mode": "random", "min_hz": float, "max_hz": float}
        verbose: Se True, stampa info durante processing
    
    Returns:
        Array numpy 1D con feature estratte (compatibile con X del collega)
    """
    # Carica FLAC
    audio_data, samplerate = sf.read(flac_path, dtype="float32")
    
    # Assicurati che sia 2D se multi-canale
    if audio_data.ndim == 1:
        audio_data = audio_data[:, np.newaxis]
    
    if verbose:
        print(f"  Caricato {flac_path.name}: shape={audio_data.shape}, sr={samplerate}")
    
    # Applica perturbazione
    perturbed_audio = audio_data.copy()
    
    if perturbation_type == "pitch":
        # Pitch shift
        if perturbation_config.get("mode") == "random":
            cents = sample_pitch_from_range(
                perturbation_config.get("min_cents", -200),
                perturbation_config.get("max_cents", 200),
                seed=perturbation_config.get("seed")
            )
        else:
            cents = perturbation_config.get("cents", 0.0)
        
        perturbed_audio = apply_pitch_shift(perturbed_audio, samplerate, cents)
        if verbose:
            print(f"    Pitch shift: {cents:.1f} cents")
    
    elif perturbation_type == "white_noise":
        # White noise
        if perturbation_config.get("mode") == "random":
            snr_db = sample_snr_from_range(
                perturbation_config.get("min_snr", 35.0),
                perturbation_config.get("max_snr", 45.0),
                seed=perturbation_config.get("seed")
            )
        else:
            snr_db = perturbation_config.get("snr_db", 40.0)
        
        # Applica rumore SOLO dove c'è segnale (non sul silenzio)
        perturbed_audio = add_white_noise(
            perturbed_audio, 
            snr_db, 
            seed=perturbation_config.get("seed"),
            only_on_signal=True  # Simula comportamento reale: rumore solo durante sparo
        )
        if verbose:
            print(f"    White noise: SNR={snr_db:.1f} dB (solo su segnale)")
    
    elif perturbation_type == "pink_noise":
        # Pink noise
        if perturbation_config.get("mode") == "random":
            snr_db = sample_snr_from_range(
                perturbation_config.get("min_snr", 35.0),
                perturbation_config.get("max_snr", 45.0),
                seed=perturbation_config.get("seed")
            )
        else:
            snr_db = perturbation_config.get("snr_db", 40.0)
        
        # Applica rumore SOLO dove c'è segnale (non sul silenzio)
        perturbed_audio = add_pink_noise(
            perturbed_audio, 
            snr_db, 
            seed=perturbation_config.get("seed"),
            only_on_signal=True  # Simula comportamento reale: rumore solo durante sparo
        )
        if verbose:
            print(f"    Pink noise: SNR={snr_db:.1f} dB (solo su segnale)")
    
    elif perturbation_type == "eq_tilt":
        # EQ tilt
        if perturbation_config.get("mode") == "random":
            tilt_db = sample_eq_tilt_from_range(
                perturbation_config.get("boost_min", 3.0),
                perturbation_config.get("boost_max", 6.0),
                perturbation_config.get("cut_min", -6.0),
                perturbation_config.get("cut_max", -3.0),
                mode="random",
                seed=perturbation_config.get("seed")
            )
        else:
            tilt_db = perturbation_config.get("tilt_db", 0.0)
        
        perturbed_audio = apply_eq_tilt(perturbed_audio, samplerate, tilt_db)
        if verbose:
            print(f"    EQ tilt: {tilt_db:.1f} dB")
    
    elif perturbation_type == "highpass":
        # High-pass filter
        if perturbation_config.get("mode") == "random":
            cutoff_hz = sample_filter_cutoff_from_range(
                perturbation_config.get("min_hz", 100.0),
                perturbation_config.get("max_hz", 500.0),
                seed=perturbation_config.get("seed")
            )
        else:
            cutoff_hz = perturbation_config.get("cutoff_hz", 0.0)
        
        if cutoff_hz > 0:
            perturbed_audio = apply_highpass(perturbed_audio, samplerate, cutoff_hz)
            if verbose:
                print(f"    High-pass: {cutoff_hz:.1f} Hz")
    
    elif perturbation_type == "lowpass":
        # Low-pass filter
        if perturbation_config.get("mode") == "random":
            cutoff_hz = sample_filter_cutoff_from_range(
                perturbation_config.get("min_hz", 8000.0),
                perturbation_config.get("max_hz", 16000.0),
                seed=perturbation_config.get("seed")
            )
        else:
            cutoff_hz = perturbation_config.get("cutoff_hz", 0.0)
        
        if cutoff_hz > 0:
            perturbed_audio = apply_lowpass(perturbed_audio, samplerate, cutoff_hz)
            if verbose:
                print(f"    Low-pass: {cutoff_hz:.1f} Hz")
    
    elif perturbation_type == "combo":
        # Combinazione di più effetti (es. pitch + noise)
        # Applica in ordine: EQ → HP → LP → pitch → noise
        if "eq_tilt" in perturbation_config:
            perturbed_audio = apply_eq_tilt(
                perturbed_audio, samplerate,
                perturbation_config["eq_tilt"].get("tilt_db", 0.0)
            )
        if "highpass" in perturbation_config:
            hp_cfg = perturbation_config["highpass"]
            if hp_cfg.get("cutoff_hz", 0) > 0:
                perturbed_audio = apply_highpass(perturbed_audio, samplerate, hp_cfg["cutoff_hz"])
        if "lowpass" in perturbation_config:
            lp_cfg = perturbation_config["lowpass"]
            if lp_cfg.get("cutoff_hz", 0) > 0:
                perturbed_audio = apply_lowpass(perturbed_audio, samplerate, lp_cfg["cutoff_hz"])
        if "pitch" in perturbation_config:
            pitch_cfg = perturbation_config["pitch"]
            cents = pitch_cfg.get("cents", 0.0)
            perturbed_audio = apply_pitch_shift(perturbed_audio, samplerate, cents)
        if "noise" in perturbation_config:
            noise_cfg = perturbation_config["noise"]
            noise_type = noise_cfg.get("type", "white")
            snr_db = noise_cfg.get("snr_db", 40.0)
            if noise_type == "white":
                perturbed_audio = add_white_noise(perturbed_audio, snr_db, only_on_signal=True)
            elif noise_type == "pink":
                perturbed_audio = add_pink_noise(perturbed_audio, snr_db, only_on_signal=True)
    
    else:
        raise ValueError(f"Tipo di perturbazione sconosciuto: {perturbation_type}")
    
    # Estrai feature (per ora: flatten come CSV del collega)
    features = extract_features_from_audio(perturbed_audio)
    
    return features


def build_X_test_pert(
    flac_paths: List[Path],
    perturbation_type: str,
    perturbation_config: Dict,
    verbose: bool = False
) -> np.ndarray:
    """
    Costruisce X_test_pert applicando perturbazione a tutti i FLAC.
    
    Args:
        flac_paths: Lista di path ai file FLAC
        perturbation_type: Tipo di perturbazione
        perturbation_config: Configurazione perturbazione
        verbose: Se True, stampa progresso
    
    Returns:
        Array numpy [n_samples, n_features] con feature perturbate
    """
    features_list = []
    
    for i, flac_path in enumerate(flac_paths):
        if verbose and (i + 1) % 10 == 0:
            print(f"Processing {i + 1}/{len(flac_paths)}: {flac_path.name}")
        
        try:
            features = apply_perturbation_to_flac(
                flac_path,
                perturbation_type,
                perturbation_config,
                verbose=verbose and (i < 3)  # Verbose solo per primi 3
            )
            features_list.append(features)
        except Exception as e:
            print(f"  ERRORE su {flac_path.name}: {e}")
            continue
    
    if not features_list:
        raise ValueError("Nessuna feature estratta con successo!")
    
    # Concatena in matrice
    X_test_pert = np.array(features_list)
    
    if verbose:
        print(f"\nX_test_pert shape: {X_test_pert.shape}")
        print(f"  Samples: {X_test_pert.shape[0]}")
        print(f"  Features per sample: {X_test_pert.shape[1]}")
    
    return X_test_pert


# ========================================================================
# Funzione perturb() per integrazione ML
# ========================================================================

def perturb(
    flac_paths: List[Path],
    perturbation_config: Dict
) -> np.ndarray:
    """
    Funzione principale per integrazione nel codice ML del collega.
    
    Questa è la funzione che il collega chiamerà nel suo codice:
        X_test_pert = perturb(flac_paths, perturbation_config)
    
    Args:
        flac_paths: Lista di path ai FLAC originali (deve corrispondere a X_test)
        perturbation_config: Dizionario con configurazione:
            {
                "type": "pitch" | "white_noise" | "pink_noise" | "eq_tilt" | "highpass" | "lowpass" | "combo",
                "mode": "fixed" | "random" | "random_like_client",
                ... altri parametri specifici per tipo ...
            }
    
    Returns:
        X_test_pert: Array numpy [n_samples, n_features] con feature perturbate
    """
    perturbation_type = perturbation_config.get("type", "pitch")
    
    # Se mode="random_like_client", usa randomizzazione come nel client C++
    if perturbation_config.get("mode") == "random_like_client":
        perturbation_config["mode"] = "random"
        # Aggiungi seed se non presente (per riproducibilità opzionale)
        if "seed" not in perturbation_config:
            perturbation_config["seed"] = None
    
    return build_X_test_pert(
        flac_paths,
        perturbation_type,
        perturbation_config,
        verbose=False  # Silenzioso per uso in pipeline ML
    )


# ========================================================================
# Entrypoint CLI
# ========================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Applica perturbazioni audio offline ai FLAC del collega"
    )
    parser.add_argument(
        "--dataset-root",
        type=Path,
        required=True,
        help="Percorso alla cartella con FLAC (es. COLLEAGUE_BSc_Thesis/Data/audio/audio_loopback_flac)"
    )
    parser.add_argument(
        "--perturbation",
        type=str,
        required=True,
        choices=["pitch", "white_noise", "pink_noise", "eq_tilt", "highpass", "lowpass", "combo"],
        help="Tipo di perturbazione da applicare"
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="fixed",
        choices=["fixed", "random", "random_like_client"],
        help="Modalità: fixed (valore fisso), random (random come client), random_like_client (alias di random)"
    )
    parser.add_argument(
        "--num-samples",
        type=int,
        default=None,
        help="Numero di file da processare (None = tutti)"
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=None,
        help="Path CSV di output (opzionale, salva feature perturbate)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Stampa info dettagliate durante processing"
    )
    
    # Parametri specifici per perturbazione
    parser.add_argument("--cents", type=float, help="Pitch shift in cents (se mode=fixed)")
    parser.add_argument("--min-cents", type=float, default=-200, help="Min pitch (se mode=random)")
    parser.add_argument("--max-cents", type=float, default=200, help="Max pitch (se mode=random)")
    
    parser.add_argument("--snr-db", type=float, help="SNR in dB (se mode=fixed)")
    parser.add_argument("--min-snr", type=float, default=35.0, help="Min SNR (se mode=random)")
    parser.add_argument("--max-snr", type=float, default=45.0, help="Max SNR (se mode=random)")
    
    parser.add_argument("--tilt-db", type=float, help="EQ tilt in dB (se mode=fixed)")
    parser.add_argument("--boost-min", type=float, default=3.0, help="Min boost (se mode=random)")
    parser.add_argument("--boost-max", type=float, default=6.0, help="Max boost (se mode=random)")
    parser.add_argument("--cut-min", type=float, default=-6.0, help="Min cut (se mode=random)")
    parser.add_argument("--cut-max", type=float, default=-3.0, help="Max cut (se mode=random)")
    
    parser.add_argument("--cutoff-hz", type=float, help="Cutoff in Hz (se mode=fixed)")
    parser.add_argument("--min-hz", type=float, help="Min cutoff (se mode=random)")
    parser.add_argument("--max-hz", type=float, help="Max cutoff (se mode=random)")
    
    args = parser.parse_args()
    
    # Trova tutti i FLAC
    flac_files = sorted(args.dataset_root.glob("*.flac"))
    if not flac_files:
        print(f"ERRORE: Nessun file FLAC trovato in {args.dataset_root}")
        return
    
    # Limita numero di file se richiesto
    if args.num_samples:
        flac_files = flac_files[:args.num_samples]
    
    print(f"Trovati {len(flac_files)} file FLAC")
    print(f"Perturbazione: {args.perturbation}, Mode: {args.mode}")
    
    # Costruisci config perturbazione
    perturbation_config = {"mode": args.mode}
    
    if args.perturbation == "pitch":
        if args.mode == "fixed":
            perturbation_config["cents"] = args.cents if args.cents is not None else 150.0
        else:
            perturbation_config["min_cents"] = args.min_cents
            perturbation_config["max_cents"] = args.max_cents
    
    elif args.perturbation in ["white_noise", "pink_noise"]:
        if args.mode == "fixed":
            perturbation_config["snr_db"] = args.snr_db if args.snr_db is not None else 40.0
        else:
            perturbation_config["min_snr"] = args.min_snr
            perturbation_config["max_snr"] = args.max_snr
    
    elif args.perturbation == "eq_tilt":
        if args.mode == "fixed":
            perturbation_config["tilt_db"] = args.tilt_db if args.tilt_db is not None else 3.0
        else:
            perturbation_config["boost_min"] = args.boost_min
            perturbation_config["boost_max"] = args.boost_max
            perturbation_config["cut_min"] = args.cut_min
            perturbation_config["cut_max"] = args.cut_max
    
    elif args.perturbation in ["highpass", "lowpass"]:
        if args.mode == "fixed":
            perturbation_config["cutoff_hz"] = args.cutoff_hz if args.cutoff_hz is not None else 0.0
        else:
            if args.min_hz is None or args.max_hz is None:
                print(f"ERRORE: --min-hz e --max-hz richiesti per {args.perturbation} in modalità random")
                return
            perturbation_config["min_hz"] = args.min_hz
            perturbation_config["max_hz"] = args.max_hz
    
    # Genera X_test_pert
    print("\nGenerando X_test_pert...")
    X_test_pert = build_X_test_pert(
        flac_files,
        args.perturbation,
        perturbation_config,
        verbose=args.verbose
    )
    
    print(f"\n✅ X_test_pert generato: shape={X_test_pert.shape}")
    
    # Salva CSV se richiesto
    if args.output_csv:
        args.output_csv.parent.mkdir(parents=True, exist_ok=True)
        np.savetxt(args.output_csv, X_test_pert, delimiter=",", fmt="%.8f")
        print(f"✅ CSV salvato: {args.output_csv}")
        print(f"   (Puoi cancellarlo dopo i test)")


if __name__ == "__main__":
    main()

