"""
sweep_noise_levels.py
Script per testare diversi livelli di rumore e valutare correlazione con efficacia.

Questo script genera X_test_pert per diversi livelli di SNR (Signal-to-Noise Ratio)
per permettere al collega di valutare la correlazione tra livello di perturbazione
e efficacia nel confondere il modello ML.

Uso:
    python scripts/sweep_noise_levels.py \
        --dataset-root COLLEAGUE_BSc_Thesis/Data/audio/audio_loopback_flac \
        --perturbation white_noise \
        --snr-levels 50 45 40 35 30 25 20 15 10 \
        --output-dir ADV_ML/output/sweep_results

Autore: Francesco Carcangiu
Data: 2024-11-21
"""

import argparse
import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional

import numpy as np

# Importa funzioni da offline_perturb
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from offline_perturb import build_X_test_pert


def sweep_noise_levels(
    flac_paths: List[Path],
    perturbation_type: str = "white_noise",
    snr_levels: Optional[List[float]] = None,
    output_dir: Path = Path("ADV_ML/output/sweep_results"),
    verbose: bool = True
) -> List[dict]:
    """
    Esegue sweep parametrico su livelli di rumore.
    
    Args:
        flac_paths: Lista di path ai file FLAC
        perturbation_type: Tipo di perturbazione ("white_noise", "pink_noise", ecc.)
        snr_levels: Lista di livelli SNR da testare (default: [50, 45, 40, ..., 10])
        output_dir: Directory dove salvare i risultati
        verbose: Se True, stampa progresso
    
    Returns:
        Lista di dizionari con risultati per ogni livello
    """
    if snr_levels is None:
        snr_levels = list(range(50, 9, -5))  # [50, 45, 40, ..., 10]
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    results = []
    
    print(f"\n{'='*60}")
    print(f"SWEEP PARAMETRICO: {perturbation_type.upper()}")
    print(f"{'='*60}")
    print(f"Livelli SNR da testare: {snr_levels}")
    print(f"Numero file FLAC: {len(flac_paths)}")
    print(f"Output directory: {output_dir}")
    print()
    
    for i, snr_db in enumerate(snr_levels, 1):
        if verbose:
            print(f"[{i}/{len(snr_levels)}] 🔬 Testando SNR = {snr_db:5.1f} dB...", end=" ", flush=True)
        
        try:
            # Genera X_test_pert
            X_test_pert = build_X_test_pert(
                flac_paths,
                perturbation_type=perturbation_type,
                perturbation_config={
                    "mode": "fixed",
                    "snr_db": float(snr_db)
                },
                verbose=False
            )
            
            # Salva X_test_pert per questo livello
            output_file = output_dir / f"X_test_{perturbation_type}_snr{snr_db:05.1f}dB.npy"
            np.save(output_file, X_test_pert)
            
            result = {
                "perturbation_type": perturbation_type,
                "snr_db": float(snr_db),
                "n_samples": int(X_test_pert.shape[0]),
                "n_features": int(X_test_pert.shape[1]),
                "output_file": str(output_file.relative_to(Path.cwd()))
            }
            results.append(result)
            
            if verbose:
                print(f"✅ Shape: {X_test_pert.shape}")
            
        except Exception as e:
            if verbose:
                print(f"❌ ERRORE: {e}")
            continue
    
    # Salva metadati
    metadata = {
        "timestamp": datetime.now().isoformat(),
        "perturbation_type": perturbation_type,
        "snr_levels": snr_levels,
        "n_flac_files": len(flac_paths),
        "results": results
    }
    
    metadata_file = output_dir / f"metadata_{perturbation_type}.json"
    with open(metadata_file, "w") as f:
        json.dump(metadata, f, indent=2)
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"✅ SWEEP COMPLETATO")
        print(f"{'='*60}")
        print(f"   Metadati salvati: {metadata_file}")
        print(f"   File generati: {len(results)}/{len(snr_levels)}")
        print(f"   Output directory: {output_dir}")
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Esegue sweep parametrico su livelli di rumore per valutare correlazione con efficacia del modello"
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
        default="white_noise",
        choices=["white_noise", "pink_noise"],
        help="Tipo di perturbazione da testare"
    )
    parser.add_argument(
        "--snr-levels",
        type=float,
        nargs="+",
        default=None,
        help="Lista di livelli SNR da testare (es. 50 45 40 35 30). Default: [50, 45, 40, ..., 10]"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("ADV_ML/output/sweep_results"),
        help="Directory dove salvare i risultati"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Non stampa output verboso"
    )
    
    args = parser.parse_args()
    
    # Trova tutti i FLAC
    flac_files = sorted(list(args.dataset_root.glob("*.flac")))
    if not flac_files:
        print(f"❌ ERRORE: Nessun file FLAC trovato in {args.dataset_root}")
        return 1
    
    # Esegui sweep
    results = sweep_noise_levels(
        flac_files,
        perturbation_type=args.perturbation,
        snr_levels=args.snr_levels,
        output_dir=args.output_dir,
        verbose=not args.quiet
    )
    
    if not results:
        print("❌ ERRORE: Nessun risultato generato!")
        return 1
    
    print(f"\n💡 Prossimi passi:")
    print(f"   1. Valuta il modello su ogni X_test_pert generato")
    print(f"   2. Analizza la correlazione tra SNR e accuracy")
    print(f"   3. Trova la soglia critica dove l'accuracy degrada significativamente")
    
    return 0


if __name__ == "__main__":
    exit(main())









