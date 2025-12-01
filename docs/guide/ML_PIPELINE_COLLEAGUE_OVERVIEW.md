# Panoramica Pipeline ML del Collega

> **Data creazione**: 2024-11-21  
> **Repository analizzato**: `COLLEAGUE_BSc_Thesis/` (clonato da https://github.com/GiovanniCasula3/BSc_Thesis.git)

---

## 1. Panoramica Alta della Pipeline ML

### 1.1 Flusso Generale

La pipeline del collega segue questo percorso:

```
FLAC (8 canali, 96kHz) 
  ↓
[Feature Extraction] → CSV audio (8 colonne)
  ↓
[Preparazione Dataset] → X_train/X_test (features), y_train/y_test (angle_deg, distance_rel)
  ↓
[RandomForest Training] → Modello addestrato
  ↓
[Prediction] → y_pred (angolo e distanza stimati)
  ↓
[Accuracy] → Metriche di performance
```

### 1.2 Descrizione Dettagliata

1. **Input Audio (FLAC)**
   - Formato: 8 canali, 96 kHz, ~1.9 secondi per clip
   - Posizione: `Data/audio/audio_loopback_flac/audio_event_<uuid>.flac`
   - Ogni file contiene audio multicanale catturato durante uno sparo nel gioco

2. **Feature Extraction**
   - Conversione FLAC → CSV: script `fix_dataset/convert_flac_to_csv.py`
   - Output: CSV con 8 colonne (una per canale), ogni riga rappresenta un campione audio
   - Posizione output: `Data/csv/audio_loopback_csv/audio_event_<uuid>.csv`

3. **Preparazione Labels**
   - Estrazione coordinate polari dai JSON: script `fix_dataset/export_polar_to_csv.py`
   - Output: CSV con `angle_deg` e `distance_rel` per ogni UUID
   - Posizione output: `Data/csv/merged_samples_csv/<uuid>.csv`

4. **Training/Test del Modello**
   - **NOTA**: Il codice ML (RandomForest training/test) **NON è presente** nel repository principale analizzato
   - Dovrebbe essere presente uno script che:
     - Carica i CSV audio e li converte in features (X)
     - Carica i CSV delle labels (y: angle_deg, distance_rel)
     - Divide in train/test split
     - Addestra RandomForestClassifier
     - Valuta accuracy

5. **Prediction e Accuracy**
   - Il modello RandomForest dovrebbe predire `angle_deg` e `distance_rel` dall'audio
   - Accuracy viene calcolata confrontando predizioni con ground truth

---

## 2. Percorsi e File Chiave

### 2.1 Dataset Audio (FLAC)

- **Path**: `COLLEAGUE_BSc_Thesis/Data/audio/audio_loopback_flac/`
- **Formato**: File `.flac` con nome `audio_event_<uuid>.flac`
- **Caratteristiche**:
  - 8 canali audio
  - Sample rate: 96 kHz
  - Durata: ~1.9 secondi per clip (0.5s pre-shot + 1.4s post-shot)
  - ~1,516 file FLAC disponibili

### 2.2 Script di Feature Extraction

- **Script principale**: `COLLEAGUE_BSc_Thesis/fix_dataset/convert_flac_to_csv.py`
  - Converte FLAC → CSV (8 colonne, una per canale)
  - Output: `Data/csv/audio_loopback_csv/audio_event_<uuid>.csv`
  
- **Script di preprocessing**: `COLLEAGUE_BSc_Thesis/fix_dataset/remove_unecessary_data.py`
  - Taglia i FLAC per mantenere solo finestra rilevante (sample 40k-140k)
  - Utile per ridurre rumore iniziale/finale

### 2.3 Script di Preparazione Labels

- **Script principale**: `COLLEAGUE_BSc_Thesis/fix_dataset/export_polar_to_csv.py`
  - Legge `merged_fixed_*.json` da `Data/Json/merged_samples/`
  - Estrae `angle_deg` e `distance_rel`
  - Output: `Data/csv/merged_samples_csv/<uuid>.csv` con formato:
    ```csv
    angle_deg,distance_rel
    308.4,0.894
    ```

### 2.4 Script di Training/Test (MANCANTE)

- **Status**: Il codice ML non è presente nel repository principale
- **Dovrebbe contenere**:
  - Caricamento CSV audio → features X (shape: `[n_samples, n_features]`)
  - Caricamento CSV labels → y (shape: `[n_samples, 2]` per angle + distance)
  - Train/test split
  - Istanziamento RandomForestClassifier
  - Training: `rf.fit(X_train, y_train)`
  - Prediction: `y_pred = rf.predict(X_test)`
  - Accuracy: `accuracy_score(y_test, y_pred)`

### 2.5 Dataset Processati

- **CSV Audio**: `COLLEAGUE_BSc_Thesis/Data/csv/audio_loopback_csv/`
  - ~1,524 file CSV, ognuno con 8 colonne (canali audio)
  
- **CSV Labels**: `COLLEAGUE_BSc_Thesis/Data/csv/merged_samples_csv/`
  - ~1,690 file CSV, ognuno con `angle_deg` e `distance_rel`

- **JSON Merged**: `COLLEAGUE_BSc_Thesis/Data/Json/merged_samples/`
  - File `merged_fixed_<uuid>.json` con metadati completi

---

## 3. Punto di Attacco Anti-Cheat

### 3.1 Effetti Audio Implementati nel Client C++

Gli effetti audio implementati in `AC/source/src/audio_runtime_obf.cpp` sono stati replicati in Python:

| Effetto | Parametri | Range Tipico | Implementazione Python |
|---------|-----------|--------------|------------------------|
| **Pitch Shift** | `cents` (100 cents = 1 semitono) | `[-200, -75]` ∪ `[75, 200]` | `audio_effects.py:apply_pitch_shift()` (librosa) |
| **White Noise** | `snr_db` (Signal-to-Noise Ratio in dB) | `[35, 45]` dB | `audio_effects.py:add_white_noise()` |
| **Pink Noise** | `snr_db` (SNR in dB) | `[35, 45]` dB | `audio_effects.py:add_pink_noise()` (filtro 1/f) |
| **EQ Tilt** | `tilt_db` (tilt in dB) | `[-6, -3]` (cut) o `[3, 6]` (boost) | `audio_effects.py:apply_eq_tilt()` (high-shelf @ 2kHz) |
| **High-Pass** | `cutoff_hz` (frequenza taglio) | `[100, 500]` Hz | `audio_effects.py:apply_highpass()` (Butterworth 2°) |
| **Low-Pass** | `cutoff_hz` (frequenza taglio) | `[8000, 16000]` Hz | `audio_effects.py:apply_lowpass()` (Butterworth 2°) |

**Randomizzazione** (replica client C++ Step 3):
- Pitch: Uniforme in `[-200..-75]` ∪ `[75..200]` (dead zone ±75 esclusa)
- SNR: Uniforme nel range `[min, max]`
- EQ: 50% boost, 50% cut se `mode="random"`

**File Python creati**:
- `ADV_ML/audio_effects.py`: Funzioni pure per effetti audio
- `ADV_ML/offline_perturb.py`: Script per applicare effetti ai FLAC e generare `X_test_pert`
- `ADV_ML/README_OFFLINE_PERTURB.md`: Documentazione completa

### 3.2 Dove Inserire `perturb()`

Il punto migliore per inserire la funzione `perturb()` è **dopo il caricamento di X_test e prima della prediction**.

**Pseudo-codice proposto**:

```python
# Caricamento dataset
X_train, X_test, y_train, y_test = load_and_split_dataset()

# Addestramento modello (baseline)
rf = RandomForestClassifier()
rf.fit(X_train, y_train)

# Prediction baseline
y_pred_baseline = rf.predict(X_test)
accuracy_baseline = accuracy_score(y_test, y_pred_baseline)

# ===== PUNTO DI ATTACCO: PERTURBAZIONE =====
# Applica perturbazione al test set
X_test_pert = perturb(X_test, perturbation_params)

# Prediction su dati perturbati
y_pred_pert = rf.predict(X_test_pert)
accuracy_pert = accuracy_score(y_test, y_pred_pert)

# Calcolo degradazione
error = accuracy_baseline - accuracy_pert
print(f"Accuracy baseline: {accuracy_baseline:.4f}")
print(f"Accuracy perturbata: {accuracy_pert:.4f}")
print(f"Degradazione: {error:.4f}")
```

### 3.3 Firma Implementata per `perturb()`

```python
def perturb(flac_paths: List[Path], perturbation_config: Dict) -> np.ndarray:
    """
    Applica perturbazione ai FLAC e restituisce X_test_pert.
    
    Args:
        flac_paths: Lista di path ai FLAC originali (deve corrispondere a X_test)
        perturbation_config: Dizionario con configurazione:
            {
                "type": "pitch" | "white_noise" | "pink_noise" | "eq_tilt" | "highpass" | "lowpass",
                "mode": "fixed" | "random" | "random_like_client",
                ... altri parametri specifici per tipo ...
            }
    
    Returns:
        X_test_pert: Array numpy [n_samples, n_features] con feature perturbate
    """
    # Implementato in ADV_ML/offline_perturb.py
```

**Esempio di uso**:
```python
from offline_perturb import perturb
from pathlib import Path

flac_paths = [Path("...") for ...]  # Lista FLAC corrispondente a X_test

perturbation_config = {
    "type": "pitch",
    "mode": "random_like_client",
    "min_cents": -200,
    "max_cents": 200
}

X_test_pert = perturb(flac_paths, perturbation_config)
```

### 3.4 Posizione File (IMPLEMENTATO)

**File creati in `ADV_ML/`**:
- `audio_effects.py`: Funzioni pure per effetti audio (pitch, noise, EQ, filtri)
- `offline_perturb.py`: Script principale con `perturb()` e `build_X_test_pert()`
- `README_OFFLINE_PERTURB.md`: Documentazione completa con esempi

**Uso nel codice ML del collega**:
```python
# Nel codice ML del collega, importa:
from offline_perturb import perturb

# Oppure se il collega preferisce importare direttamente:
import sys
sys.path.append("ADV_ML")
from offline_perturb import perturb
```

### 3.4 Esempio di Integrazione Completa

```python
# ml_pipeline/train_and_test.py (da creare)

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from perturbations import perturb  # nostra libreria

# Caricamento dati
X, y = load_dataset()  # da implementare
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

# Training baseline
rf = RandomForestClassifier()
rf.fit(X_train, y_train)
y_pred = rf.predict(X_test)
accuracy_baseline = accuracy_score(y_test, y_pred)

# Test con perturbazione
perturbation = {'type': 'gaussian_noise', 'strength': 0.1}
X_test_pert = perturb(X_test, perturbation)
y_pred_pert = rf.predict(X_test_pert)
accuracy_pert = accuracy_score(y_test, y_pred_pert)

print(f"Baseline: {accuracy_baseline:.4f}, Perturbato: {accuracy_pert:.4f}")
```

---

## 4. Cosa è Stato Considerato "Superfluo"

### 4.1 File/Cartelle da Archiviare (NON ancora spostati)

I seguenti componenti sono **utili per la raccolta dati** ma **non essenziali** per la pipeline ML di base:

1. **`audio_loopback/record_audio.py`** e utilities audio
   - Utili per catturare nuovi dati, non necessari per ML
   - **Status**: Mantenere (potrebbe servire per generare nuovi test set)

2. **`gathering_data/automator.py`** e script di automazione
   - Utili per raccolta dati, non per ML
   - **Status**: Mantenere (utile per dataset futuri)

3. **`player_positions/grab_player_position.py`**
   - Estrazione ground truth da minimap, già fatto
   - **Status**: Mantenere (potrebbe servire per validazione)

4. **`game_overlay/arrow_widget.py`**
   - Overlay PySide6 per visualizzazione, non necessario per ML
   - **Status**: Mantenere (utile per demo/visualizzazione)

5. **`fix_dataset/check_uuid_alignment.py`**
   - Utility di validazione dataset, non essenziale per ML
   - **Status**: Mantenere (utile per QA)

6. **`fix_dataset/analyze_csv_report.py`** e `find_first_nonzero_csv.py`
   - Analisi qualità dataset, non necessari per training
   - **Status**: Mantenere (utili per debugging)

### 4.2 File Essenziali per Pipeline ML

**MANTENERE** questi file:
- `fix_dataset/convert_flac_to_csv.py` → Feature extraction
- `fix_dataset/export_polar_to_csv.py` → Label extraction
- `fix_dataset/remove_unecessary_data.py` → Preprocessing opzionale
- Dataset: `Data/csv/audio_loopback_csv/` e `Data/csv/merged_samples_csv/`

### 4.3 Note

**Nessun file è stato ancora spostato in `archive_unused/`** perché:
- La maggior parte degli script potrebbe essere utile per debugging/validazione
- Il codice ML non è ancora presente, quindi è difficile determinare cosa è davvero superfluo
- Si consiglia di archiviare solo dopo aver implementato la pipeline ML completa

---

## 5. TODO per i Prossimi Step

### Step 1: Creare Libreria Python di Perturbazioni
- [ ] Creare `COLLEAGUE_BSc_Thesis/ml_pipeline/perturbations.py`
- [ ] Implementare `perturb()` con supporto per vari tipi:
  - Rumore gaussiano
  - Quantizzazione
  - Delay/echo
  - Filtri passa-basso/alta
  - Altri tipi basati su logiche del client C++
- [ ] Test unitari per ogni tipo di perturbazione

### Step 2: Implementare Pipeline ML Base (se mancante)
- [ ] Creare script di caricamento dataset:
  - `load_audio_features()`: carica CSV audio → X
  - `load_labels()`: carica CSV labels → y
- [ ] Creare script di training/test:
  - `train_and_test.py`: pipeline completa con RandomForest
  - Include train/test split, training, evaluation

### Step 3: Integrare Perturbazioni nella Pipeline
- [ ] Modificare script di test per includere `perturb()`
- [ ] Eseguire test con vari tipi/intensità di perturbazione
- [ ] Salvare risultati (accuracy baseline vs perturbata) in CSV/JSON

### Step 4: Generare Dataset Perturbato Temporaneo
- [ ] Creare script che applica perturbazioni a X_test
- [ ] Salvare X_test_pert in formato temporaneo (non sovrascrivere originali)
- [ ] Misurare accuracy su dataset perturbato

### Step 5: Ripetere per Vari Tipi di Rumore
- [ ] Loop su diversi tipi di perturbazione
- [ ] Loop su diverse intensità (strength)
- [ ] Salvare solo risultati (accuracy, error) in file di riepilogo
- [ ] Non salvare dataset perturbati completi (troppo spazio)

### Step 6: Analisi Risultati
- [ ] Creare script di visualizzazione risultati
- [ ] Grafici: accuracy vs tipo/intensità perturbazione
- [ ] Identificare perturbazioni più efficaci per degradare il modello

---

## 6. Struttura Dataset

### 6.1 Formato X (Features Audio)

- **Shape**: `[n_samples, n_features]`
- **n_samples**: ~1,516-1,690 (numero di clip audio)
- **n_features**: Da definire in base a feature extraction
  - Se si usano i CSV raw: 8 colonne × numero di righe per clip
  - Se si estraggono feature statistiche: numero di feature estratte

### 6.2 Formato y (Labels)

- **Shape**: `[n_samples, 2]` oppure due array separati
- **Colonne**:
  - `angle_deg`: angolo in gradi (0-360)
  - `distance_rel`: distanza relativa (0-1)

### 6.3 Esempio Caricamento

```python
import numpy as np
import pandas as pd
from pathlib import Path

def load_audio_features(csv_dir: Path) -> np.ndarray:
    """Carica tutti i CSV audio e li concatena."""
    csv_files = sorted(csv_dir.glob("audio_event_*.csv"))
    features = []
    for csv_file in csv_files:
        df = pd.read_csv(csv_file, header=None)
        # Flatten o estrai feature statistiche
        features.append(df.values.flatten())  # esempio semplice
    return np.array(features)

def load_labels(csv_dir: Path) -> np.ndarray:
    """Carica tutti i CSV labels."""
    csv_files = sorted(csv_dir.glob("*.csv"))
    labels = []
    for csv_file in csv_files:
        df = pd.read_csv(csv_file)
        labels.append([df['angle_deg'].iloc[0], df['distance_rel'].iloc[0]])
    return np.array(labels)
```

---

## 7. Note Finali

### 7.1 Stato Attuale

- ✅ Dataset audio FLAC disponibile (~1,516 file)
- ✅ Script di conversione FLAC → CSV disponibili
- ✅ Labels (angle, distance) disponibili in CSV
- ❌ Codice ML (RandomForest training/test) **NON presente** nel repository principale
- ❌ Feature extraction avanzata non implementata (solo conversione raw CSV)

### 7.2 Prossimi Passi Immediati

1. **Verificare se il codice ML esiste in un'altra branch o repository separato**
2. **Se mancante, implementare pipeline ML base**:
   - Caricamento dataset
   - Feature extraction (se necessario)
   - RandomForest training/test
3. **Integrare `perturb()` nella pipeline di test**

### 7.3 Dipendenze Aggiuntive Necessarie

Per la pipeline ML, aggiungere a `requirements.txt`:
```
scikit-learn>=1.0.0
pandas>=1.3.0
```

---

## 8. Riferimenti File Chiave

| File | Path | Descrizione |
|------|------|-------------|
| Convert FLAC→CSV | `fix_dataset/convert_flac_to_csv.py` | Converte audio FLAC in CSV |
| Export Labels | `fix_dataset/export_polar_to_csv.py` | Estrae angle/distance da JSON |
| Dataset Audio | `Data/audio/audio_loopback_flac/` | FLAC originali |
| CSV Audio | `Data/csv/audio_loopback_csv/` | CSV audio processati |
| CSV Labels | `Data/csv/merged_samples_csv/` | CSV labels (angle, distance) |
| JSON Merged | `Data/Json/merged_samples/` | JSON completi con metadati |

---

**Fine documento**

