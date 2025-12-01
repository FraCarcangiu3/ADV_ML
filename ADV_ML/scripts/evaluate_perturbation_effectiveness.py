"""
evaluate_perturbation_effectiveness.py
Pipeline completa per valutare efficacia delle perturbazioni su un modello ML.

Questo script:
1. Carica un modello ML addestrato
2. Genera X_test_pert per diversi livelli di perturbazione
3. Valuta l'accuracy del modello su ogni livello
4. Genera grafici di correlazione SNR vs Accuracy
5. Salva risultati in CSV

Uso:
    python scripts/evaluate_perturbation_effectiveness.py \
        --model-path model.pkl \
        --dataset-root COLLEAGUE_BSc_Thesis/Data/audio/audio_loopback_flac \
        --y-test-path y_test.npy \
        --perturbation white_noise \
        --output-dir ADV_ML/output/evaluation_results

Autore: Francesco Carcangiu
Data: 2024-11-21
"""

import argparse
import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.metrics import accuracy_score, classification_report

# Importa funzioni da offline_perturb
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from offline_perturb import build_X_test_pert


def load_model(model_path: Path):
    """
    Carica modello ML (supporta pickle, joblib, o custom loader).
    """
    import pickle
    import joblib
    
    model_path = Path(model_path)
    
    if model_path.suffix == ".pkl":
        try:
            return joblib.load(model_path)
        except:
            with open(model_path, "rb") as f:
                return pickle.load(f)
    else:
        raise ValueError(f"Formato modello non supportato: {model_path.suffix}")


def evaluate_perturbation_levels(
    model,
    flac_paths: List[Path],
    y_test: np.ndarray,
    perturbation_type: str = "white_noise",
    snr_levels: Optional[List[float]] = None,
    verbose: bool = True
) -> pd.DataFrame:
    """
    Valuta efficacia del modello a diversi livelli di perturbazione.
    
    Args:
        model: Modello ML addestrato (deve avere .predict() method)
        flac_paths: Lista di path ai file FLAC (deve corrispondere a y_test)
        y_test: Array con labels di test
        perturbation_type: Tipo di perturbazione
        snr_levels: Lista di livelli SNR da testare
        verbose: Se True, stampa progresso
    
    Returns:
        DataFrame con risultati (snr_db, accuracy, n_samples)
    """
    if snr_levels is None:
        snr_levels = [50, 45, 40, 35, 30, 25, 20, 15, 10]
    
    if len(flac_paths) != len(y_test):
        raise ValueError(
            f"Numero di file FLAC ({len(flac_paths)}) non corrisponde "
            f"al numero di labels ({len(y_test)})"
        )
    
    results = []
    
    print(f"\n{'='*60}")
    print(f"VALUTAZIONE EFFICACIA: {perturbation_type.upper()}")
    print(f"{'='*60}")
    print(f"Livelli SNR da testare: {snr_levels}")
    print(f"Numero campioni: {len(y_test)}")
    print()
    
    for i, snr_db in enumerate(snr_levels, 1):
        if verbose:
            print(f"[{i}/{len(snr_levels)}] 🔬 Valutando SNR = {snr_db:5.1f} dB...", end=" ", flush=True)
        
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
            
            # Valuta modello
            y_pred = model.predict(X_test_pert)
            accuracy = accuracy_score(y_test, y_pred)
            
            results.append({
                "perturbation_type": perturbation_type,
                "snr_db": float(snr_db),
                "accuracy": float(accuracy),
                "n_samples": int(len(y_test))
            })
            
            if verbose:
                print(f"✅ Accuracy: {accuracy:.4f}")
            
        except Exception as e:
            if verbose:
                print(f"❌ ERRORE: {e}")
            continue
    
    df = pd.DataFrame(results)
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"✅ VALUTAZIONE COMPLETATA")
        print(f"{'='*60}")
        print(f"\nRisultati:")
        print(df.to_string(index=False))
    
    return df


def plot_correlation(df: pd.DataFrame, output_path: Path, title: str = None):
    """
    Genera grafico di correlazione SNR vs Accuracy.
    """
    if title is None:
        title = f"Correlazione SNR vs Accuracy: {df['perturbation_type'].iloc[0]}"
    
    plt.figure(figsize=(10, 6))
    plt.plot(df["snr_db"], df["accuracy"], "o-", linewidth=2, markersize=8, label=df['perturbation_type'].iloc[0])
    plt.xlabel("SNR (dB)", fontsize=12)
    plt.ylabel("Accuracy", fontsize=12)
    plt.title(title, fontsize=14)
    plt.grid(True, alpha=0.3)
    plt.ylim([0, 1])
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()
    
    print(f"   📊 Grafico salvato: {output_path}")


def find_critical_threshold(df: pd.DataFrame, threshold: float = 0.5) -> Optional[float]:
    """
    Trova la soglia critica (SNR) dove l'accuracy scende sotto threshold.
    """
    below_threshold = df[df["accuracy"] < threshold]
    if len(below_threshold) > 0:
        return float(below_threshold["snr_db"].max())
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Valuta efficacia delle perturbazioni su un modello ML"
    )
    parser.add_argument(
        "--model-path",
        type=Path,
        required=True,
        help="Percorso al modello ML addestrato (.pkl o .joblib)"
    )
    parser.add_argument(
        "--dataset-root",
        type=Path,
        required=True,
        help="Percorso alla cartella con FLAC"
    )
    parser.add_argument(
        "--y-test-path",
        type=Path,
        required=True,
        help="Percorso a file con labels di test (.npy o .csv)"
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
        default=Path("ADV_ML/output/evaluation_results"),
        help="Directory dove salvare i risultati"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.5,
        help="Soglia di accuracy per trovare punto critico (default: 0.5)"
    )
    
    args = parser.parse_args()
    
    # Carica modello
    print(f"📦 Caricamento modello: {args.model_path}")
    try:
        model = load_model(args.model_path)
        print(f"   ✅ Modello caricato: {type(model).__name__}")
    except Exception as e:
        print(f"   ❌ ERRORE nel caricamento modello: {e}")
        return 1
    
    # Carica labels di test
    print(f"📦 Caricamento labels: {args.y_test_path}")
    try:
        if args.y_test_path.suffix == ".npy":
            y_test = np.load(args.y_test_path)
        elif args.y_test_path.suffix == ".csv":
            y_test = pd.read_csv(args.y_test_path).values.flatten()
        else:
            raise ValueError(f"Formato non supportato: {args.y_test_path.suffix}")
        print(f"   ✅ Labels caricate: {len(y_test)} campioni")
    except Exception as e:
        print(f"   ❌ ERRORE nel caricamento labels: {e}")
        return 1
    
    # Trova tutti i FLAC
    flac_files = sorted(list(args.dataset_root.glob("*.flac")))
    if not flac_files:
        print(f"❌ ERRORE: Nessun file FLAC trovato in {args.dataset_root}")
        return 1
    
    if len(flac_files) != len(y_test):
        print(f"⚠️  WARNING: Numero file FLAC ({len(flac_files)}) != numero labels ({len(y_test)})")
        print(f"   Usando solo i primi {min(len(flac_files), len(y_test))} file")
        flac_files = flac_files[:len(y_test)]
        y_test = y_test[:len(flac_files)]
    
    # Crea output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)
    
    # Valuta perturbazione
    df = evaluate_perturbation_levels(
        model,
        flac_files,
        y_test,
        perturbation_type=args.perturbation,
        snr_levels=args.snr_levels,
        verbose=True
    )
    
    if df.empty:
        print("❌ ERRORE: Nessun risultato generato!")
        return 1
    
    # Salva risultati CSV
    csv_path = args.output_dir / f"results_{args.perturbation}.csv"
    df.to_csv(csv_path, index=False)
    print(f"\n💾 Risultati salvati: {csv_path}")
    
    # Genera grafico
    plot_path = args.output_dir / f"correlation_{args.perturbation}.png"
    plot_correlation(df, plot_path)
    
    # Trova soglia critica
    critical_snr = find_critical_threshold(df, threshold=args.threshold)
    if critical_snr is not None:
        print(f"\n⚠️  Soglia critica (accuracy < {args.threshold}): SNR < {critical_snr:.1f} dB")
    else:
        print(f"\n✅ Il modello mantiene accuracy >= {args.threshold} per tutti i livelli testati")
    
    # Salva metadati
    metadata = {
        "timestamp": datetime.now().isoformat(),
        "model_path": str(args.model_path),
        "perturbation_type": args.perturbation,
        "snr_levels": args.snr_levels if args.snr_levels else list(range(50, 9, -5)),
        "n_samples": len(y_test),
        "critical_threshold_snr": critical_snr,
        "results_file": str(csv_path),
        "plot_file": str(plot_path)
    }
    
    metadata_path = args.output_dir / f"metadata_{args.perturbation}.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)
    
    print(f"💾 Metadati salvati: {metadata_path}")
    
    return 0


if __name__ == "__main__":
    exit(main())









