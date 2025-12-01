# 🎧 Fase 1 & 2 - Riepilogo Implementazione

**Data:** 2024-11-21  
**Autore:** Francesco Carcangiu  
**Status:** ✅ Completato

---

## 📋 Obiettivo

Implementare un sistema Python per replicare gli effetti audio del client C++ e applicarli offline ai file FLAC del dataset del collega.

---

## ✅ Fase 1 - Capire e Tradurre i Rumori del Client

### Effetti Implementati

Tutti gli effetti sono implementati in `ADV_ML/audio_effects.py`:

#### 1. **Pitch Shift** (`apply_pitch_shift`)
- **Libreria:** `librosa` (equivalente a SoundTouch nel client C++)
- **Parametro:** `cents` (100 cents = 1 semitono)
- **Range tipico:** `[-200, -75] ∪ [75, 200]` (dead zone ±75 esclusa)
- **Conversione:** `semitones = cents / 100.0`
- **Nota:** Preserva la durata del segnale (a differenza del resampling semplice)

#### 2. **White Noise** (`add_white_noise`)
- **Libreria:** `numpy.random`
- **Parametro:** `snr_db` (Signal-to-Noise Ratio in dB)
- **Range tipico:** `[35, 45]` dB
- **Algoritmo:**
  1. Calcola RMS del segnale
  2. Calcola RMS target del rumore: `RMS_noise = RMS_signal / (10^(SNR/20))`
  3. Genera rumore uniforme `[-1, 1]` con RMS teorico ≈ `1/√3 ≈ 0.577`
  4. Scala il rumore per ottenere SNR corretto
  5. Aggiunge rumore con clipping `[-1, 1]`

#### 3. **Pink Noise** (`add_pink_noise`)
- **Libreria:** `numpy.random` + filtro IIR custom
- **Parametro:** `snr_db` (Signal-to-Noise Ratio in dB)
- **Range tipico:** `[16, 24]` dB
- **Algoritmo:**
  1. Genera white noise uniforme
  2. Applica filtro IIR semplice per approssimare 1/f:
     `y[n] = 0.99 * y[n-1] + (1 - 0.99) * x[n]`
  3. Normalizza per mantenere stessa RMS del white originale
  4. Scala per ottenere SNR target
  5. Aggiunge al segnale con clipping

#### 4. **EQ Tilt** (`apply_eq_tilt`)
- **Libreria:** `scipy.signal` (high-shelf filter)
- **Parametro:** `tilt_db` (positivo = brighten, negativo = darken)
- **Range tipico:** `[-6, -3]` (cut) o `[3, 6]` (boost)
- **Frequenza shelf:** 2000 Hz (fisso, come nel client C++)
- **Gain factor:** `A = 10^(tilt_db / 40.0)`

#### 5. **High-Pass Filter** (`apply_highpass`)
- **Libreria:** `scipy.signal` (Butterworth 2° ordine)
- **Parametro:** `cutoff_hz` (frequenza di taglio in Hz)
- **Range tipico:** `[150, 250]` Hz
- **Q:** 0.707 (Butterworth)

#### 6. **Low-Pass Filter** (`apply_lowpass`)
- **Libreria:** `scipy.signal` (Butterworth 2° ordine)
- **Parametro:** `cutoff_hz` (frequenza di taglio in Hz)
- **Range tipico:** `[8000, 10000]` Hz
- **Q:** 0.707 (Butterworth)

### Funzioni di Randomizzazione

Replicano la logica del client C++ per generare parametri casuali:

- `sample_pitch_from_range()`: Genera pitch con dead zone ±75 esclusa
- `sample_snr_from_range()`: Genera SNR uniforme nel range
- `sample_eq_tilt_from_range()`: Genera EQ tilt (50% boost, 50% cut se mode="random")
- `sample_filter_cutoff_from_range()`: Genera frequenza di taglio uniforme

---

## ✅ Fase 2 - Script Offline per Perturbare Audio (.flac)

### File Principale: `offline_perturb.py`

**Funzione principale:** `apply_perturbation_to_flac()`

Applica una perturbazione a un singolo FLAC e restituisce le feature estratte (non salva WAV, restituisce direttamente il segnale perturbato).

### Uso da Linea di Comando

```bash
python offline_perturb.py \
    --dataset-root COLLEAGUE_BSc_Thesis/Data/audio/audio_loopback_flac \
    --perturbation pitch \
    --mode random \
    --min-cents -200 \
    --max-cents 200 \
    --num-samples 100 \
    --output-csv ADV_ML/output/X_test_pitch_random.csv \
    --verbose
```

**Parametri:**
- `--dataset-root`: Percorso alla cartella con FLAC
- `--perturbation`: Tipo di perturbazione (`pitch`, `white_noise`, `pink_noise`, `eq_tilt`, `highpass`, `lowpass`, `combo`)
- `--mode`: Modalità (`fixed`, `random`, `random_like_client`)
- `--num-samples`: Numero di file da processare (None = tutti)
- `--output-csv`: Path CSV di output (opzionale)
- `--verbose`: Stampa info dettagliate

**Parametri specifici per perturbazione:**

**Pitch:**
- `--cents`: Valore fisso (se `mode=fixed`)
- `--min-cents`, `--max-cents`: Range (se `mode=random`)

**Noise (white/pink):**
- `--snr-db`: Valore fisso (se `mode=fixed`)
- `--min-snr`, `--max-snr`: Range (se `mode=random`)

**EQ Tilt:**
- `--tilt-db`: Valore fisso (se `mode=fixed`)
- `--boost-min`, `--boost-max`, `--cut-min`, `--cut-max`: Range (se `mode=random`)

**Filtri (highpass/lowpass):**
- `--cutoff-hz`: Valore fisso (se `mode=fixed`)
- `--min-hz`, `--max-hz`: Range (se `mode=random`)

### Uso come Modulo

```python
from pathlib import Path
from offline_perturb import apply_perturbation_to_flac, build_X_test_pert

# Applica perturbazione a un singolo file
flac_path = Path("path/to/file.flac")
features = apply_perturbation_to_flac(
    flac_path,
    perturbation_type="pitch",
    perturbation_config={
        "mode": "random",
        "min_cents": -200,
        "max_cents": 200
    },
    verbose=True
)

# Applica perturbazione a tutti i file
flac_paths = list(Path("dataset/").glob("*.flac"))
X_test_pert = build_X_test_pert(
    flac_paths,
    perturbation_type="pitch",
    perturbation_config={
        "mode": "random",
        "min_cents": -200,
        "max_cents": 200
    },
    verbose=True
)
```

### Funzione `perturb()` per Integrazione ML

Funzione principale per integrazione nel codice ML del collega:

```python
from offline_perturb import perturb

X_test_pert = perturb(
    flac_paths,
    perturbation_config={
        "type": "pitch",
        "mode": "random_like_client",
        "min_cents": -200,
        "max_cents": 200
    }
)
```

---

## 📊 Range Parametri dal CSV di Configurazione

Dal file `AC/audio_obf_config.csv`:

### Esempio: `weapon/usp`

```csv
weapon/usp,-200,200,random,35,45,16,24,random,2,6,-9,-3,150,250,8000,10000
```

**Parametri:**
- **Pitch:** `[-200, 200]` cents (dead zone ±75 esclusa)
- **Noise:** 
  - Tipo: `random` (50% white, 50% pink)
  - White SNR: `[35, 45]` dB
  - Pink SNR: `[16, 24]` dB
- **EQ:**
  - Mode: `random` (50% boost, 50% cut)
  - Boost: `[2, 6]` dB
  - Cut: `[-9, -3]` dB
- **High-pass:** `[150, 250]` Hz
- **Low-pass:** `[8000, 10000]` Hz

### Configurazioni di Test Singole

Per testare ogni effetto singolarmente:

**TEST 1: Solo WHITE NOISE**
```python
perturbation_config = {
    "type": "white_noise",
    "mode": "random",
    "min_snr": 35.0,
    "max_snr": 45.0
}
```

**TEST 2: Solo PINK NOISE**
```python
perturbation_config = {
    "type": "pink_noise",
    "mode": "random",
    "min_snr": 16.0,
    "max_snr": 24.0
}
```

**TEST 3: Solo PITCH SHIFT**
```python
perturbation_config = {
    "type": "pitch",
    "mode": "random",
    "min_cents": -200,
    "max_cents": 200
}
```

**TEST 4: PITCH + WHITE NOISE**
```python
perturbation_config = {
    "type": "combo",
    "pitch": {"cents": 150.0},  # o mode="random" con range
    "noise": {"type": "white", "snr_db": 40.0}
}
```

---

## 🎲 Randomicità e Strategie di Test per Valutare Correlazione con Efficacia del Modello

### Panoramica: Perché Testare Diversi Livelli di Rumore?

Come suggerito dal professore, è importante testare **diversi livelli di rumore** per valutare se esiste una **correlazione tra l'intensità della perturbazione e l'efficacia nel confondere il modello ML**.

**Domande da rispondere:**
- A quale livello di SNR il modello inizia a degradare significativamente?
- C'è una soglia critica oltre la quale l'accuracy crolla?
- Il modello è più sensibile a white noise o pink noise?
- La combinazione di più effetti (pitch + noise) è più efficace?

### Modalità di Randomicità Disponibili

Il sistema supporta tre modalità principali:

#### 1. **Modalità `fixed`** (Valore Fisso)
Usa un valore fisso per tutti i campioni. Utile per test controllati e riproducibili.

```python
perturbation_config = {
    "type": "white_noise",
    "mode": "fixed",
    "snr_db": 40.0  # Stesso valore per tutti i file
}
```

**Quando usarla:**
- Test iniziali per capire l'effetto di un livello specifico
- Benchmark per confrontare con altri livelli
- Test riproducibili per validazione

#### 2. **Modalità `random`** (Random Uniforme)
Genera valori casuali uniformemente distribuiti nel range specificato. Replica il comportamento del client C++ quando `AC_AUDIO_OBF_RANDOMIZE=1`.

```python
perturbation_config = {
    "type": "white_noise",
    "mode": "random",
    "min_snr": 35.0,
    "max_snr": 45.0  # Valore casuale tra 35 e 45 per ogni file
}
```

**Quando usarla:**
- Test realistici che simulano il comportamento del client
- Valutazione della robustezza del modello a variabilità
- Test per vedere se il modello si adatta a diversi livelli

#### 3. **Modalità `random_like_client`** (Alias di `random`)
Identica a `random`, ma semanticamente più chiara per indicare che replica il comportamento del client.

### Strategia di Test: Sweep Parametrico

Per valutare la correlazione tra livello di rumore e efficacia, si consiglia di eseguire un **sweep parametrico** con valori fissi a intervalli regolari.

#### Esempio: Test White Noise con Livelli Crescenti

```python
from pathlib import Path
from offline_perturb import build_X_test_pert
import numpy as np

flac_paths = list(Path("dataset/").glob("*.flac"))
results = []

# Test con diversi livelli di SNR (da molto debole a molto forte)
snr_levels = [50, 45, 40, 35, 30, 25, 20, 15, 10]  # dB

for snr_db in snr_levels:
    print(f"\n🔬 Testando SNR = {snr_db} dB...")
    
    # Genera X_test_pert con questo livello di rumore
    X_test_pert = build_X_test_pert(
        flac_paths,
        perturbation_type="white_noise",
        perturbation_config={
            "mode": "fixed",
            "snr_db": snr_db
        },
        verbose=False
    )
    
    # Qui il collega valuta il modello con X_test_pert
    # Esempio: accuracy = model.evaluate(X_test_pert, y_test)
    # results.append({"snr_db": snr_db, "accuracy": accuracy})
    
    print(f"   ✅ Completato: SNR={snr_db} dB")

# Analizza risultati
# import matplotlib.pyplot as plt
# snr_values = [r["snr_db"] for r in results]
# accuracies = [r["accuracy"] for r in results]
# plt.plot(snr_values, accuracies, 'o-')
# plt.xlabel("SNR (dB)")
# plt.ylabel("Accuracy")
# plt.title("Correlazione SNR vs Accuracy")
# plt.show()
```

#### Esempio: Test Pink Noise vs White Noise

```python
# Confronta efficacia di white vs pink noise
noise_types = ["white_noise", "pink_noise"]
snr_levels = [40, 35, 30, 25, 20]

for noise_type in noise_types:
    for snr_db in snr_levels:
        X_test_pert = build_X_test_pert(
            flac_paths,
            perturbation_type=noise_type,
            perturbation_config={
                "mode": "fixed",
                "snr_db": snr_db
            }
        )
        # Valuta modello...
```

#### Esempio: Test Combinazioni (Pitch + Noise)

```python
# Test combinazione pitch + noise con diversi livelli
pitch_values = [0, 50, 100, 150, 200]  # cents
snr_values = [40, 35, 30, 25]  # dB

for pitch_cents in pitch_values:
    for snr_db in snr_values:
        X_test_pert = build_X_test_pert(
            flac_paths,
            perturbation_type="combo",
            perturbation_config={
                "pitch": {
                    "mode": "fixed",
                    "cents": pitch_cents
                },
                "noise": {
                    "type": "white",
                    "mode": "fixed",
                    "snr_db": snr_db
                }
            }
        )
        # Valuta modello...
```

### Script Pronti per Sweep Parametrico

Sono disponibili due script pronti all'uso:

#### 1. `scripts/sweep_noise_levels.py` - Genera X_test_pert per diversi livelli

Genera `X_test_pert` per diversi livelli di SNR e li salva in file `.npy` separati.

**Uso:**
```bash
python ADV_ML/scripts/sweep_noise_levels.py \
    --dataset-root COLLEAGUE_BSc_Thesis/Data/audio/audio_loopback_flac \
    --perturbation white_noise \
    --snr-levels 50 45 40 35 30 25 20 15 10 \
    --output-dir ADV_ML/output/sweep_results
```

**Output:**
- `X_test_white_noise_snr50.0dB.npy`
- `X_test_white_noise_snr45.0dB.npy`
- ...
- `metadata_white_noise.json` (metadati)

#### 2. `scripts/evaluate_perturbation_effectiveness.py` - Valuta modello e genera grafici

Carica un modello ML, valuta su diversi livelli di perturbazione e genera grafici di correlazione.

**Uso:**
```bash
python ADV_ML/scripts/evaluate_perturbation_effectiveness.py \
    --model-path model.pkl \
    --dataset-root COLLEAGUE_BSc_Thesis/Data/audio/audio_loopback_flac \
    --y-test-path y_test.npy \
    --perturbation white_noise \
    --output-dir ADV_ML/output/evaluation_results
```

**Output:**
- `results_white_noise.csv` (tabella risultati)
- `correlation_white_noise.png` (grafico correlazione)
- `metadata_white_noise.json` (metadati)

### Esempio: Script Completo per Sweep Parametrico (Custom)

Se preferisci creare uno script custom, ecco un template completo:

```python
"""
sweep_noise_levels.py
Script per testare diversi livelli di rumore e valutare correlazione con efficacia.
"""

from pathlib import Path
from offline_perturb import build_X_test_pert
import numpy as np
import json
from datetime import datetime

def sweep_noise_levels(
    flac_paths,
    perturbation_type="white_noise",
    snr_levels=None,
    output_dir="ADV_ML/output/sweep_results"
):
    """
    Esegue sweep parametrico su livelli di rumore.
    
    Args:
        flac_paths: Lista di path ai file FLAC
        perturbation_type: Tipo di perturbazione ("white_noise", "pink_noise", ecc.)
        snr_levels: Lista di livelli SNR da testare (default: [50, 45, 40, ..., 10])
        output_dir: Directory dove salvare i risultati
    """
    if snr_levels is None:
        snr_levels = list(range(50, 9, -5))  # [50, 45, 40, ..., 10]
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    results = []
    
    for snr_db in snr_levels:
        print(f"\n🔬 Testando {perturbation_type} con SNR = {snr_db} dB...")
        
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
            output_file = output_dir / f"X_test_{perturbation_type}_snr{snr_db:02d}dB.npy"
            np.save(output_file, X_test_pert)
            
            results.append({
                "perturbation_type": perturbation_type,
                "snr_db": snr_db,
                "n_samples": X_test_pert.shape[0],
                "n_features": X_test_pert.shape[1],
                "output_file": str(output_file)
            })
            
            print(f"   ✅ Salvato: {output_file}")
            print(f"      Shape: {X_test_pert.shape}")
            
        except Exception as e:
            print(f"   ❌ ERRORE: {e}")
            continue
    
    # Salva metadati
    metadata = {
        "timestamp": datetime.now().isoformat(),
        "perturbation_type": perturbation_type,
        "snr_levels": snr_levels,
        "results": results
    }
    
    metadata_file = output_dir / f"metadata_{perturbation_type}.json"
    with open(metadata_file, "w") as f:
        json.dump(metadata, f, indent=2)
    
    print(f"\n✅ Sweep completato!")
    print(f"   Metadati salvati: {metadata_file}")
    print(f"   File generati: {len(results)}")
    
    return results


if __name__ == "__main__":
    # Esempio d'uso
    dataset_root = Path("COLLEAGUE_BSc_Thesis/Data/audio/audio_loopback_flac")
    flac_paths = sorted(list(dataset_root.glob("*.flac")))
    
    if not flac_paths:
        print(f"❌ Nessun file FLAC trovato in {dataset_root}")
        exit(1)
    
    print(f"📁 Trovati {len(flac_paths)} file FLAC")
    
    # Test white noise
    print("\n" + "="*60)
    print("TEST 1: White Noise")
    print("="*60)
    sweep_noise_levels(
        flac_paths,
        perturbation_type="white_noise",
        snr_levels=[50, 45, 40, 35, 30, 25, 20, 15, 10],
        output_dir="ADV_ML/output/sweep_results/white_noise"
    )
    
    # Test pink noise
    print("\n" + "="*60)
    print("TEST 2: Pink Noise")
    print("="*60)
    sweep_noise_levels(
        flac_paths,
        perturbation_type="pink_noise",
        snr_levels=[50, 45, 40, 35, 30, 25, 20, 15, 10],
        output_dir="ADV_ML/output/sweep_results/pink_noise"
    )
```

### Valutazione della Correlazione

Dopo aver generato `X_test_pert` per diversi livelli, il collega può:

1. **Valutare il modello** su ogni `X_test_pert`:
   ```python
   from sklearn.metrics import accuracy_score
   
   # Carica X_test_pert per un livello specifico
   X_test_pert = np.load("ADV_ML/output/sweep_results/white_noise/X_test_white_noise_snr40dB.npy")
   
   # Valuta modello
   y_pred = model.predict(X_test_pert)
   accuracy = accuracy_score(y_test, y_pred)
   ```

2. **Analizzare i risultati** per trovare correlazioni:
   ```python
   import pandas as pd
   import matplotlib.pyplot as plt
   
   # Carica risultati
   results = []
   for snr in [50, 45, 40, 35, 30, 25, 20, 15, 10]:
       X_test_pert = np.load(f"X_test_white_noise_snr{snr:02d}dB.npy")
       accuracy = evaluate_model(X_test_pert, y_test)
       results.append({"snr_db": snr, "accuracy": accuracy})
   
   df = pd.DataFrame(results)
   
   # Plot correlazione
   plt.figure(figsize=(10, 6))
   plt.plot(df["snr_db"], df["accuracy"], "o-", linewidth=2, markersize=8)
   plt.xlabel("SNR (dB)", fontsize=12)
   plt.ylabel("Accuracy", fontsize=12)
   plt.title("Correlazione SNR vs Accuracy del Modello", fontsize=14)
   plt.grid(True, alpha=0.3)
   plt.ylim([0, 1])
   plt.savefig("correlation_snr_vs_accuracy.png", dpi=150)
   plt.show()
   
   # Trova soglia critica (es. accuracy < 0.5)
   threshold = 0.5
   critical_snr = df[df["accuracy"] < threshold]["snr_db"].min()
   print(f"⚠️  Soglia critica (accuracy < {threshold}): SNR < {critical_snr} dB")
   ```

### Considerazioni sulla Randomicità

#### Quando Usare `fixed` vs `random`

**Usa `fixed` quando:**
- Vuoi testare un livello specifico in modo controllato
- Stai facendo sweep parametrico per trovare correlazioni
- Vuoi risultati riproducibili
- Stai facendo benchmark

**Usa `random` quando:**
- Vuoi simulare il comportamento reale del client
- Vuoi testare la robustezza del modello a variabilità
- Stai facendo test di generalizzazione
- Vuoi vedere se il modello si adatta a diversi livelli

#### Strategia Ibrida: Fixed + Random

Puoi anche combinare approcci:

```python
# Test con range ristretto (es. solo livelli alti)
perturbation_config = {
    "type": "white_noise",
    "mode": "random",
    "min_snr": 35.0,  # Range ristretto
    "max_snr": 45.0
}

# Oppure test con range ampio (es. tutti i livelli)
perturbation_config = {
    "type": "white_noise",
    "mode": "random",
    "min_snr": 10.0,  # Range ampio
    "max_snr": 50.0
}
```

### Esempio: Pipeline Completa di Valutazione

```python
"""
evaluate_perturbation_effectiveness.py
Pipeline completa per valutare efficacia delle perturbazioni.
"""

from pathlib import Path
from offline_perturb import build_X_test_pert
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.metrics import accuracy_score, classification_report

def evaluate_perturbation_levels(
    model,
    flac_paths,
    y_test,
    perturbation_type="white_noise",
    snr_levels=None
):
    """
    Valuta efficacia del modello a diversi livelli di perturbazione.
    
    Returns:
        DataFrame con risultati (snr_db, accuracy, n_samples)
    """
    if snr_levels is None:
        snr_levels = [50, 45, 40, 35, 30, 25, 20, 15, 10]
    
    results = []
    
    for snr_db in snr_levels:
        print(f"🔬 Valutando {perturbation_type} @ SNR = {snr_db} dB...")
        
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
            "snr_db": snr_db,
            "accuracy": accuracy,
            "n_samples": len(y_test)
        })
        
        print(f"   ✅ Accuracy: {accuracy:.4f}")
    
    return pd.DataFrame(results)


# Esempio d'uso
if __name__ == "__main__":
    # Carica modello (esempio)
    # model = joblib.load("model.pkl")
    
    # Carica dataset
    flac_paths = list(Path("dataset/").glob("*.flac"))
    # y_test = ...  # Labels di test
    
    # Valuta white noise
    df_white = evaluate_perturbation_levels(
        model, flac_paths, y_test,
        perturbation_type="white_noise",
        snr_levels=[50, 45, 40, 35, 30, 25, 20, 15, 10]
    )
    
    # Valuta pink noise
    df_pink = evaluate_perturbation_levels(
        model, flac_paths, y_test,
        perturbation_type="pink_noise",
        snr_levels=[50, 45, 40, 35, 30, 25, 20, 15, 10]
    )
    
    # Plot confronto
    plt.figure(figsize=(12, 6))
    plt.plot(df_white["snr_db"], df_white["accuracy"], "o-", label="White Noise", linewidth=2)
    plt.plot(df_pink["snr_db"], df_pink["accuracy"], "s-", label="Pink Noise", linewidth=2)
    plt.xlabel("SNR (dB)", fontsize=12)
    plt.ylabel("Accuracy", fontsize=12)
    plt.title("Confronto Efficacia: White Noise vs Pink Noise", fontsize=14)
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.ylim([0, 1])
    plt.savefig("comparison_white_vs_pink.png", dpi=150)
    plt.show()
    
    # Salva risultati
    df_white.to_csv("results_white_noise.csv", index=False)
    df_pink.to_csv("results_pink_noise.csv", index=False)
```

### Domande da Rispondere con i Test

1. **Soglia critica:** A quale livello di SNR l'accuracy scende sotto una soglia accettabile (es. 0.5)?
2. **Sensibilità:** Il modello è più sensibile a white noise o pink noise?
3. **Robustezza:** Il modello mantiene buone performance anche con rumore moderato (SNR > 30 dB)?
4. **Combinazioni:** La combinazione di più effetti (pitch + noise) è più efficace del singolo effetto?
5. **Variabilità:** Il modello si comporta meglio con valori fissi o random?

---

## 🔧 Dipendenze

**File:** `ADV_ML/requirements.txt`

```txt
numpy>=1.20.0
scipy>=1.7.0
librosa>=0.9.0
soundfile>=0.10.0
```

**Installazione:**
```bash
cd ADV_ML
pip install -r requirements.txt
```

---

## 📝 Note Implementative

### Compatibilità con Client C++

- **Pitch shift:** Usa `librosa` invece di SoundTouch, ma produce risultati equivalenti
- **White noise:** Replica esattamente la logica RMS del client C++
- **Pink noise:** Usa lo stesso filtro IIR semplice (`alpha=0.99`)
- **EQ tilt:** Usa lo stesso high-shelf filter @ 2kHz
- **Filtri HP/LP:** Usa gli stessi coefficienti Butterworth 2° ordine

### Gestione Multi-Canale

Tutte le funzioni supportano:
- **Mono:** Array 1D `[frames]`
- **Multi-canale:** Array 2D `[frames, channels]`

### Clipping

Tutti gli effetti applicano clipping `[-1.0, 1.0]` come nel client C++.

### Riproducibilità

Tutte le funzioni di randomizzazione accettano un parametro `seed` opzionale per riproducibilità.

---

## 🧪 Esempi di Test

### Test 1: Pitch Shift Fisso

```bash
python offline_perturb.py \
    --dataset-root COLLEAGUE_BSc_Thesis/Data/audio/audio_loopback_flac \
    --perturbation pitch \
    --mode fixed \
    --cents 150 \
    --num-samples 10 \
    --verbose
```

### Test 2: White Noise Random

```bash
python offline_perturb.py \
    --dataset-root COLLEAGUE_BSc_Thesis/Data/audio/audio_loopback_flac \
    --perturbation white_noise \
    --mode random \
    --min-snr 35 \
    --max-snr 45 \
    --num-samples 10 \
    --verbose
```

### Test 3: Combinazione Pitch + Noise

```python
from offline_perturb import apply_perturbation_to_flac
from pathlib import Path

flac_path = Path("path/to/file.flac")

# Applica pitch + white noise
features = apply_perturbation_to_flac(
    flac_path,
    perturbation_type="combo",
    perturbation_config={
        "pitch": {
            "mode": "random",
            "min_cents": -200,
            "max_cents": 200
        },
        "noise": {
            "type": "white",
            "mode": "random",
            "min_snr": 35.0,
            "max_snr": 45.0
        }
    },
    verbose=True
)
```

---

## ✅ Checklist Completamento

- [x] Implementazione pitch shift con librosa
- [x] Implementazione white noise con RMS corretto
- [x] Implementazione pink noise con filtro 1/f
- [x] Implementazione EQ tilt (high-shelf)
- [x] Implementazione high-pass filter
- [x] Implementazione low-pass filter
- [x] Funzioni di randomizzazione (replica client C++)
- [x] Script `offline_perturb.py` per perturbare FLAC
- [x] Funzione `apply_perturbation_to_flac()` per singolo file
- [x] Funzione `build_X_test_pert()` per batch processing
- [x] Funzione `perturb()` per integrazione ML
- [x] Supporto modalità `fixed`, `random`, `random_like_client`
- [x] Supporto combinazioni di effetti (`combo`)
- [x] Gestione multi-canale
- [x] Clipping come nel client C++
- [x] Documentazione completa

---

## 🚀 Prossimi Passi

1. **Test con dataset reale:** Applicare perturbazioni ai FLAC del collega
2. **Validazione percettiva:** Verificare che gli effetti siano equivalenti al client C++
3. **Sweep parametrico:** Usare `scripts/sweep_noise_levels.py` per generare X_test_pert a diversi livelli
4. **Valutazione correlazione:** Usare `scripts/evaluate_perturbation_effectiveness.py` per valutare efficacia
5. **Analisi risultati:** Trovare soglie critiche e correlazioni tra livello di rumore e efficacia
6. **Integrazione ML:** Usare `perturb()` nel codice di training/testing del collega
7. **Ottimizzazione:** Se necessario, ottimizzare per dataset molto grandi

---

**Fine documento**

