# Guida all'Uso delle Perturbazioni Audio Offline

> **Per studenti**: Questa guida spiega come usare le funzioni di perturbazione audio per testare la robustezza del modello ML del collega.

---

## 📋 Indice

1. [Panoramica](#panoramica)
2. [Effetti Disponibili](#effetti-disponibili)
3. [Come Usare da Linea di Comando](#come-usare-da-linea-di-comando)
4. [Come Usare nel Codice ML](#come-usare-nel-codice-ml)
5. [Esempi Pratici](#esempi-pratici)
6. [Corrispondenza con Client C++](#corrispondenza-con-client-c)

---

## Panoramica

Il sistema di perturbazione offline replica gli stessi effetti audio implementati nel client C++ (`AC/source/src/audio_runtime_obf.cpp`) ma applicati offline ai FLAC del collega.

**File principali**:
- `audio_effects.py`: Funzioni pure per applicare effetti audio (pitch, noise, EQ, filtri)
- `offline_perturb.py`: Script per applicare effetti ai FLAC e generare `X_test_pert`

**Obiettivo**: Generare `X_test_pert` (dati di test perturbati) per misurare come la perturbazione degrada l'accuracy del modello RandomForest.

---

## Effetti Disponibili

### 1. **Pitch Shift** (`pitch`)
Sposta la frequenza del segnale mantenendo la durata.

- **Parametri**:
  - `cents`: Pitch shift in cents (100 cents = 1 semitono)
  - Range tipico: `[-200, -75]` ∪ `[75, 200]` (dead zone ±75 esclusa)
- **Esempio client C++**: `pitch_cents = randomize_pitch_uniform(-200, 200)`
- **Implementazione Python**: Usa `librosa.effects.pitch_shift()` (equivalente a SoundTouch nel client)

### 2. **White Noise** (`white_noise`)
Aggiunge rumore bianco con SNR target.

- **Parametri**:
  - `snr_db`: Signal-to-Noise Ratio in dB (es. 35, 40, 45)
  - Range tipico: `[35, 45]` dB
  - `only_on_signal`: Se True (default), applica rumore SOLO dove c'è segnale (non sul silenzio)
    - ✅ Simula comportamento reale: rumore solo durante lo sparo
    - ❌ Se False: rumore anche sul silenzio (non realistico)
- **Esempio client C++**: `noise_snr_db = randomize_snr_uniform(35.0, 45.0)`
- **Implementazione Python**: Genera rumore uniforme `[-1, 1]` e scala per ottenere SNR corretto
- **⚠️ Importante**: Con `only_on_signal=True`, i silenzi originali vengono preservati

### 3. **Pink Noise** (`pink_noise`)
Aggiunge rumore rosa (1/f) con SNR target.

- **Parametri**:
  - `snr_db`: SNR in dB (es. 35, 40, 45)
  - Range tipico: `[35, 45]` dB
  - `only_on_signal`: Se True (default), applica rumore SOLO dove c'è segnale (non sul silenzio)
    - ✅ Simula comportamento reale: rumore solo durante lo sparo
    - ❌ Se False: rumore anche sul silenzio (non realistico)
- **Esempio client C++**: Filtro IIR `y[n] = 0.99 * y[n-1] + 0.01 * x[n]`
- **Implementazione Python**: Replica lo stesso filtro IIR
- **⚠️ Importante**: Con `only_on_signal=True`, i silenzi originali vengono preservati

### 4. **EQ Tilt** (`eq_tilt`)
Equalizzatore high-shelf @ 2kHz per modificare il timbro.

- **Parametri**:
  - `tilt_db`: Tilt in dB (positivo = brighten, negativo = darken)
  - Range tipico: `[-6, -3]` (cut) o `[3, 6]` (boost)
- **Esempio client C++**: High-shelf filter con `A = 10^(tilt_db / 40.0)`
- **Implementazione Python**: Replica filtro biquad high-shelf

### 5. **High-Pass Filter** (`highpass`)
Filtro passa-alto Butterworth 2° ordine.

- **Parametri**:
  - `cutoff_hz`: Frequenza di taglio in Hz
  - Range tipico: `[100, 500]` Hz
- **Esempio client C++**: Butterworth HP con `Q = 0.707`
- **Implementazione Python**: Replica coefficienti Butterworth

### 6. **Low-Pass Filter** (`lowpass`)
Filtro passa-basso Butterworth 2° ordine.

- **Parametri**:
  - `cutoff_hz`: Frequenza di taglio in Hz
  - Range tipico: `[8000, 16000]` Hz
- **Esempio client C++**: Butterworth LP con `Q = 0.707`
- **Implementazione Python**: Replica coefficienti Butterworth

---

## Come Usare da Linea di Comando

### Esempio 1: Pitch Shift Fisso

Applica pitch shift di +150 cents a 10 file FLAC:

```bash
python ADV_ML/offline_perturb.py \
  --dataset-root COLLEAGUE_BSc_Thesis/Data/audio/audio_loopback_flac \
  --perturbation pitch \
  --mode fixed \
  --cents 150 \
  --num-samples 10 \
  --output-csv ADV_ML/output/X_test_pitch_150.csv \
  --verbose
```

### Esempio 2: White Noise Random (come Client C++)

Applica white noise con SNR random tra 35-45 dB (come nel client):

```bash
python ADV_ML/offline_perturb.py \
  --dataset-root COLLEAGUE_BSc_Thesis/Data/audio/audio_loopback_flac \
  --perturbation white_noise \
  --mode random_like_client \
  --min-snr 35.0 \
  --max-snr 45.0 \
  --num-samples 100 \
  --output-csv ADV_ML/output/X_test_white_random.csv
```

### Esempio 3: Pink Noise SNR Fisso

Applica pink noise con SNR fisso di 40 dB:

```bash
python ADV_ML/offline_perturb.py \
  --dataset-root COLLEAGUE_BSc_Thesis/Data/audio/audio_loopback_flac \
  --perturbation pink_noise \
  --mode fixed \
  --snr-db 40.0 \
  --num-samples 50 \
  --output-csv ADV_ML/output/X_test_pink_40db.csv
```

### Esempio 4: EQ Tilt Random

Applica EQ tilt random (50% boost, 50% cut):

```bash
python ADV_ML/offline_perturb.py \
  --dataset-root COLLEAGUE_BSc_Thesis/Data/audio/audio_loopback_flac \
  --perturbation eq_tilt \
  --mode random \
  --boost-min 3.0 \
  --boost-max 6.0 \
  --cut-min -6.0 \
  --cut-max -3.0 \
  --num-samples 100 \
  --output-csv ADV_ML/output/X_test_eq_random.csv
```

### Esempio 5: High-Pass Filter

Applica high-pass filter a 300 Hz:

```bash
python ADV_ML/offline_perturb.py \
  --dataset-root COLLEAGUE_BSc_Thesis/Data/audio/audio_loopback_flac \
  --perturbation highpass \
  --mode fixed \
  --cutoff-hz 300 \
  --num-samples 50 \
  --output-csv ADV_ML/output/X_test_hp_300hz.csv
```

---

## Come Usare nel Codice ML

### Funzione `perturb()`

La funzione principale per integrazione nel codice ML del collega:

```python
from offline_perturb import perturb
from pathlib import Path

# Lista di path ai FLAC (deve corrispondere a X_test)
flac_paths = [
    Path("COLLEAGUE_BSc_Thesis/Data/audio/audio_loopback_flac/audio_event_xxx.flac"),
    Path("COLLEAGUE_BSc_Thesis/Data/audio/audio_loopback_flac/audio_event_yyy.flac"),
    # ... altri FLAC corrispondenti a X_test
]

# Config perturbazione
perturbation_config = {
    "type": "pitch",
    "mode": "random_like_client",  # o "fixed", "random"
    "min_cents": -200,
    "max_cents": 200
}

# Genera X_test_pert
X_test_pert = perturb(flac_paths, perturbation_config)

# Ora puoi usare X_test_pert nel modello:
# y_pred_pert = rf.predict(X_test_pert)
# accuracy_pert = accuracy_score(y_test, y_pred_pert)
```

### Esempio Completo (Pseudo-codice ML)

```python
import numpy as np
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from offline_perturb import perturb

# 1. Carica dataset originale (il collega fa questo)
X_train, X_test, y_train, y_test = load_and_split_dataset()
flac_paths_test = get_flac_paths_for_X_test(X_test)  # Funzione del collega

# 2. Addestra modello baseline
rf = RandomForestClassifier()
rf.fit(X_train, y_train)
y_pred_baseline = rf.predict(X_test)
accuracy_baseline = accuracy_score(y_test, y_pred_baseline)

# 3. Applica perturbazione
perturbation_config = {
    "type": "pitch",
    "mode": "random_like_client",
    "min_cents": -200,
    "max_cents": 200
}

X_test_pert = perturb(flac_paths_test, perturbation_config)

# 4. Valuta su dati perturbati
y_pred_pert = rf.predict(X_test_pert)
accuracy_pert = accuracy_score(y_test, y_pred_pert)

# 5. Calcola degradazione
error = accuracy_baseline - accuracy_pert
print(f"Accuracy baseline: {accuracy_baseline:.4f}")
print(f"Accuracy perturbata: {accuracy_pert:.4f}")
print(f"Degradazione: {error:.4f}")
```

---

## Esempi Pratici

### Test 1: Pitch Shift Fisso +150 cents

```bash
# Genera X_test_pert
python ADV_ML/offline_perturb.py \
  --dataset-root COLLEAGUE_BSc_Thesis/Data/audio/audio_loopback_flac \
  --perturbation pitch \
  --mode fixed \
  --cents 150 \
  --num-samples 100 \
  --output-csv ADV_ML/output/X_test_pitch_150.csv
```

**Risultato**: CSV con 100 sample perturbati con pitch +150 cents.

### Test 2: White Noise Random (SNR 35-45 dB)

```bash
python ADV_ML/offline_perturb.py \
  --dataset-root COLLEAGUE_BSc_Thesis/Data/audio/audio_loopback_flac \
  --perturbation white_noise \
  --mode random_like_client \
  --min-snr 35.0 \
  --max-snr 45.0 \
  --num-samples 100 \
  --output-csv ADV_ML/output/X_test_white_random.csv
```

**Risultato**: CSV con 100 sample perturbati con white noise random (SNR tra 35-45 dB).

### Test 3: Combinazione Pitch + Noise (da codice Python)

```python
from offline_perturb import build_X_test_pert
from pathlib import Path

flac_paths = list(Path("COLLEAGUE_BSc_Thesis/Data/audio/audio_loopback_flac").glob("*.flac"))[:100]

# Config combo: pitch + white noise
perturbation_config = {
    "type": "combo",
    "pitch": {"cents": 150},
    "noise": {"type": "white", "snr_db": 40.0}
}

X_test_pert = build_X_test_pert(flac_paths, "combo", perturbation_config)
```

---

## Corrispondenza con Client C++

### Pitch Shift

**Client C++** (`audio_runtime_obf.cpp:108-161`):
- Usa SoundTouch library
- Converte cents in semitoni: `semitones = cents / 100.0`
- Applica pitch shift preservando durata

**Python** (`audio_effects.py:apply_pitch_shift`):
- Usa `librosa.effects.pitch_shift()` (equivalente a SoundTouch)
- Stessa conversione cents → semitoni
- Stesso comportamento (preserva durata, zero-pad se necessario)

### White Noise

**Client C++** (`audio_runtime_obf.cpp:182-214`):
- Calcola RMS segnale
- RMS rumore target: `RMS_noise = RMS_signal / (10^(SNR/20))`
- Genera rumore uniforme `[-1, 1]` con RMS teorico `1/√3 ≈ 0.577`
- Scala rumore: `noise_amplitude = target_rms_noise / rms_uniform_noise`

**Python** (`audio_effects.py:add_white_noise`):
- Stessa formula SNR
- Stesso calcolo RMS
- Stesso scaling del rumore
- Stesso clipping `[-1, 1]`

### Pink Noise

**Client C++** (`audio_runtime_obf.cpp:261-308`):
- Filtro IIR: `y[n] = 0.99 * y[n-1] + 0.01 * x[n]`
- Normalizza per mantenere RMS

**Python** (`audio_effects.py:add_pink_noise`):
- Stesso filtro IIR con `alpha = 0.99`
- Stessa normalizzazione

### Randomizzazione

**Client C++** (`audio_runtime_obf.cpp:658-715`):
- Pitch: Uniforme in `[-200..-75]` ∪ `[75..200]` (dead zone ±75)
- SNR: Uniforme in `[min, max]`
- EQ: 50% boost, 50% cut se `mode="random"`

**Python** (`audio_effects.py:sample_*`):
- Stessa logica di randomizzazione
- Stesse distribuzioni uniformi
- Stesso dead zone per pitch

---

## Note Importanti

1. **Formato Feature**: Per ora, le feature sono il raw audio flatten (come CSV del collega). In futuro potrebbe essere necessario estrarre feature statistiche/spettrali.

2. **Ordine Applicazione**: Nel client C++, l'ordine è: EQ → HP → LP → pitch → tone → noise. Lo script Python rispetta lo stesso ordine per combo.

3. **⚠️ Rumore Solo sul Segnale (IMPORTANTE!)**: 
   - **Default**: `only_on_signal=True` (raccomandato)
   - Il rumore viene applicato **SOLO dove c'è segnale**, non sul silenzio
   - Questo simula il comportamento reale del gioco: rumore solo durante lo sparo
   - I silenzi originali vengono preservati (~77% dell'audio è silenzio)
   - **Vedi**: `ADV_ML/CORREZIONE_RUMORE_SOLO_SEGNALE.md` per dettagli

4. **Seed Random**: Per riproducibilità, puoi passare `seed` nella config:
   ```python
   perturbation_config = {
       "type": "pitch",
       "mode": "random",
       "min_cents": -200,
       "max_cents": 200,
       "seed": 12345  # Seed fisso per riproducibilità
   }
   ```

5. **CSV Temporanei**: I CSV generati sono temporanei e possono essere cancellati dopo i test. Servono solo per verificare che `X_test_pert` sia generato correttamente.

6. **Dipendenze**: Assicurati di avere installato:
   ```bash
   pip install numpy scipy soundfile librosa
   ```

---

## Troubleshooting

### Errore: "librosa non trovato"
```bash
pip install librosa
```

### Errore: "Nessun file FLAC trovato"
Verifica che il path sia corretto:
```bash
ls COLLEAGUE_BSc_Thesis/Data/audio/audio_loopback_flac/*.flac | head -5
```

### Errore: "Shape mismatch"
Assicurati che `flac_paths` corrisponda esattamente a `X_test` (stesso ordine, stesso numero di file).

---

**Fine guida**

