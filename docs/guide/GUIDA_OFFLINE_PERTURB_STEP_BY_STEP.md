# Guida Pratica: Come Usare Offline Perturbation (Fase 1 + Fase 2)

**Autore:** Francesco Carcangiu  
**Data:** 2024-11-21  
**Versione:** 1.0

Questa guida ti spiega passo-passo come usare il sistema di perturbazione audio offline per generare dataset di test e valutare l'efficacia delle perturbazioni sul modello ML.

---

## 1. Prerequisiti

### Attivare l'ambiente virtuale

Prima di tutto, attiva il virtual environment Python:

```bash
cd "/Users/francesco03/Documents/GitHub/AssaultCube Server"
source ADV_ML/venv/bin/activate
```

Dovresti vedere `(venv)` all'inizio della riga di comando.

### Installare i pacchetti Python necessari

Se non li hai già installati, installa le dipendenze:

```bash
cd ADV_ML
pip install -r requirements.txt
```

**Pacchetti principali necessari:**
- `numpy` (>=1.26.0) - Calcoli numerici, generazione white/pink noise
- `scipy` (>=1.16.0) - Filtri audio (EQ tilt, HP/LP filters)
- `librosa` (>=0.11.0) - Pitch shift (solo per questo effetto)
- `soundfile` (>=0.13.1) - Lettura/scrittura file audio FLAC
- `scikit-learn` (>=1.7.0) - Machine Learning (per valutazione)
- `matplotlib` (>=3.10.0) - Grafici (opzionale, per visualizzazione)

**Nota importante:** Gli effetti audio sono implementati così:
- **White noise**: Usa solo `numpy.random.uniform()` per generare rumore casuale
- **Pink noise**: Usa `numpy.random.uniform()` + filtro IIR implementato manualmente (solo numpy)
- **EQ tilt e filtri HP/LP**: Usano `scipy.signal` per i filtri biquad
- **Pitch shift**: Usa `librosa.effects.pitch_shift()` (unica libreria esterna specifica)

Quindi **numpy e scipy sono sufficienti** per tutti gli effetti tranne il pitch shift che richiede librosa.

### Dove devono stare i dati FLAC

I file FLAC del collega devono essere nella cartella:

```
COLLEAGUE_BSc_Thesis/Data/audio/audio_loopback_flac/
```

**Verifica che i file ci siano:**
```bash
ls COLLEAGUE_BSc_Thesis/Data/audio/audio_loopback_flac/*.flac | head -5
```

Dovresti vedere una lista di file `.flac`. Se la cartella è vuota o non esiste, contatta il collega per ottenere i dati.

---

## 2. Effetti Audio Disponibili

Il modulo `audio_effects.py` offre i seguenti effetti, allineati ai range calibrati per la pistola (`weapon/usp`) nel client C++:

| Effetto | Parametro | Range Tipico | Descrizione |
|---------|-----------|--------------|-------------|
| **Pitch Shift** | `cents` | `[-200, -75] ∪ [75, 200]` | Sposta la frequenza mantenendo durata (dead zone ±75 esclusa) |
| **White Noise** | `snr_db` | `[35, 45]` dB | Aggiunge rumore bianco con SNR target |
| **Pink Noise** | `snr_db` | `[16, 24]` dB | Aggiunge rumore rosa (1/f) con SNR target |
| **EQ Tilt** | `tilt_db` | `[-6, -3]` (cut) o `[3, 6]` (boost) | Modifica equalizzazione (brighten/darken) |
| **High-Pass Filter** | `cutoff_hz` | `[150, 250]` Hz | Filtra frequenze basse |
| **Low-Pass Filter** | `cutoff_hz` | `[8000, 10000]` Hz | Filtra frequenze alte |

**Nota:** Questi range sono calibrati per la pistola (`weapon/usp`) nel file `AC/audio_obf_config.csv`. Per altri suoni, i range potrebbero essere diversi.

**Come vengono implementati:**
- **Pitch shift**: Usa `librosa` (libreria esterna per pitch shifting di qualità)
- **White noise**: Generato con `numpy.random.uniform()` (rumore casuale uniforme)
- **Pink noise**: Generato con `numpy.random.uniform()` + filtro IIR manuale (implementazione custom)
- **EQ tilt e filtri HP/LP**: Usano `scipy.signal` per filtri biquad (Butterworth)

---

## 3. Come Generare un Dataset di Test Perturbato (X_test_pert)

### Esempio 1: Pitch Shift con Valore Fisso

Genera `X_test_pert` con pitch shift fisso a +150 cents su 50 file:

```bash
python ADV_ML/offline_perturb.py \
  --dataset-root COLLEAGUE_BSc_Thesis/Data/audio/audio_loopback_flac \
  --perturbation pitch \
  --mode fixed \
  --cents 150 \
  --num-samples 50 \
  --output-csv ADV_ML/output/pistol_pitch_P2_medium.csv \
  --verbose
```

**Cosa fa questo comando:**
Carica 50 file FLAC dalla cartella specificata, applica a ciascuno un pitch shift di +150 cents (circa 1.5 semitoni più alto), estrae le feature nello stesso formato del collega e salva tutto in un CSV. Il file risultante contiene le feature perturbate pronte per essere usate come `X_test_pert` nel modello ML.

### Esempio 2: White Noise Random (come nel client)

Genera `X_test_pert` con white noise random nel range calibrato:

```bash
python ADV_ML/offline_perturb.py \
  --dataset-root COLLEAGUE_BSc_Thesis/Data/audio/audio_loopback_flac \
  --perturbation white_noise \
  --mode random_like_client \
  --min-snr 35 \
  --max-snr 45 \
  --num-samples 50 \
  --output-csv ADV_ML/output/pistol_noiseW_L1.csv \
  --verbose
```

**Cosa fa questo comando:**
Carica 50 file FLAC, applica a ciascuno white noise con SNR casuale tra 35 e 45 dB (distribuzione uniforme, come nel client quando `AC_AUDIO_OBF_RANDOMIZE=1`), estrae le feature e salva in CSV. Ogni file avrà un livello di rumore diverso, simulando il comportamento reale del client.

### Esempio 3: Pink Noise Random

Genera `X_test_pert` con pink noise random nel range calibrato:

```bash
python ADV_ML/offline_perturb.py \
  --dataset-root COLLEAGUE_BSc_Thesis/Data/audio/audio_loopback_flac \
  --perturbation pink_noise \
  --mode random \
  --min-snr 16 \
  --max-snr 24 \
  --num-samples 50 \
  --output-csv ADV_ML/output/pistol_noiseK_test.csv \
  --verbose
```

**Cosa fa questo comando:**
Carica 50 file FLAC, applica a ciascuno pink noise (rumore rosa, 1/f) con SNR casuale tra 16 e 24 dB, estrae le feature e salva in CSV. Il pink noise ha una distribuzione di frequenza diversa dal white noise (più energia nelle basse frequenze).

### Esempio 4: EQ Tilt Random

Genera `X_test_pert` con EQ tilt random (boost o cut):

```bash
python ADV_ML/offline_perturb.py \
  --dataset-root COLLEAGUE_BSc_Thesis/Data/audio/audio_loopback_flac \
  --perturbation eq_tilt \
  --mode random \
  --boost-min 3 \
  --boost-max 6 \
  --cut-min -6 \
  --cut-max -3 \
  --num-samples 50 \
  --output-csv ADV_ML/output/pistol_eqtilt_test.csv \
  --verbose
```

**Cosa fa questo comando:**
Carica 50 file FLAC, applica a ciascuno un EQ tilt casuale: o boost (3-6 dB, rende il suono più brillante) o cut (-6 a -3 dB, rende il suono più scuro), estrae le feature e salva in CSV. L'effetto modifica l'equalizzazione in modo lineare su tutto lo spettro.

### Esempio 5: High-Pass Filter Random

Genera `X_test_pert` con high-pass filter random:

```bash
python ADV_ML/offline_perturb.py \
  --dataset-root COLLEAGUE_BSc_Thesis/Data/audio/audio_loopback_flac \
  --perturbation highpass \
  --mode random \
  --min-hz 150 \
  --max-hz 250 \
  --num-samples 50 \
  --output-csv ADV_ML/output/pistol_hp_test.csv \
  --verbose
```

**Cosa fa questo comando:**
Carica 50 file FLAC, applica a ciascuno un filtro high-pass con cutoff casuale tra 150 e 250 Hz, estrae le feature e salva in CSV. Il filtro rimuove le frequenze basse, lasciando passare solo quelle sopra il cutoff.

### Esempio 6: Low-Pass Filter Random

Genera `X_test_pert` con low-pass filter random:

```bash
python ADV_ML/offline_perturb.py \
  --dataset-root COLLEAGUE_BSc_Thesis/Data/audio/audio_loopback_flac \
  --perturbation lowpass \
  --mode random \
  --min-hz 8000 \
  --max-hz 10000 \
  --num-samples 50 \
  --output-csv ADV_ML/output/pistol_lp_test.csv \
  --verbose
```

**Cosa fa questo comando:**
Carica 50 file FLAC, applica a ciascuno un filtro low-pass con cutoff casuale tra 8000 e 10000 Hz, estrae le feature e salva in CSV. Il filtro rimuove le frequenze alte, lasciando passare solo quelle sotto il cutoff.

### Verificare il CSV Generato

Dopo aver generato un CSV, verifica dimensioni e contenuto:

```python
import numpy as np

# Carica il CSV
X_test_pert = np.loadtxt("ADV_ML/output/pistol_pitch_P2_medium.csv", delimiter=",")

# Verifica dimensioni
print(f"Shape: {X_test_pert.shape}")
print(f"Numero campioni: {X_test_pert.shape[0]}")
print(f"Numero feature per campione: {X_test_pert.shape[1]}")

# Verifica range valori
print(f"Min: {X_test_pert.min():.6f}")
print(f"Max: {X_test_pert.max():.6f}")
print(f"Media: {X_test_pert.mean():.6f}")
print(f"Std: {X_test_pert.std():.6f}")
```

**Output atteso:**
```
Shape: (50, 123456)  # Esempio: 50 campioni, 123456 feature ciascuno
Numero campioni: 50
Numero feature per campione: 123456
Min: -1.234567
Max: 1.234567
Media: 0.000123
Std: 0.123456
```

---

## 4. Come Definire "Livelli di Rumore" per gli Esperimenti

Per valutare la correlazione tra livello di perturbazione e efficacia nel confondere il modello, definiamo livelli progressivi.

### Tabella Livelli per la Pistola

| Livello | Tipo | Parametri | Descrizione |
|---------|------|-----------|-------------|
| **P1** | Pitch | `±100` cents | Pitch shift leggero |
| **P2** | Pitch | `±150` cents | Pitch shift medio |
| **P3** | Pitch | `±200` cents | Pitch shift forte |
| **W1** | White Noise | `[35-38]` dB | Rumore bianco leggero |
| **W2** | White Noise | `[38-42]` dB | Rumore bianco medio |
| **W3** | White Noise | `[42-45]` dB | Rumore bianco forte |
| **K1** | Pink Noise | `[16-20]` dB | Rumore rosa leggero |
| **K2** | Pink Noise | `[20-24]` dB | Rumore rosa forte |
| **E1** | EQ Tilt | `[-6, -4]` dB cut o `[3, 4]` dB boost | EQ tilt leggero (50% boost, 50% cut) |
| **E2** | EQ Tilt | `[-4, -3]` dB cut o `[4, 5]` dB boost | EQ tilt medio (50% boost, 50% cut) |
| **E3** | EQ Tilt | `[-5, -3]` dB cut o `[5, 6]` dB boost | EQ tilt forte (50% boost, 50% cut) |
| **H1** | High-Pass | `[150, 200]` Hz | Filtro HP leggero |
| **H2** | High-Pass | `[200, 250]` Hz | Filtro HP forte |
| **L1** | Low-Pass | `[8000, 9000]` Hz | Filtro LP leggero |
| **L2** | Low-Pass | `[9000, 10000]` Hz | Filtro LP forte |

### Comandi per Generare Ogni Livello

#### Livelli Pitch (P1, P2, P3)

**P1 - Pitch ±100 cents (random):**
```bash
python ADV_ML/offline_perturb.py \
  --dataset-root COLLEAGUE_BSc_Thesis/Data/audio/audio_loopback_flac \
  --perturbation pitch \
  --mode random \
  --min-cents -100 \
  --max-cents 100 \
  --num-samples 50 \
  --output-csv ADV_ML/output/pistol_pitch_P1_light.csv \
  --verbose
```

**P2 - Pitch ±150 cents (random):**
```bash
python ADV_ML/offline_perturb.py \
  --dataset-root COLLEAGUE_BSc_Thesis/Data/audio/audio_loopback_flac \
  --perturbation pitch \
  --mode random \
  --min-cents -150 \
  --max-cents 150 \
  --num-samples 50 \
  --output-csv ADV_ML/output/pistol_pitch_P2_medium.csv \
  --verbose
```

**P3 - Pitch ±200 cents (random):**
```bash
python ADV_ML/offline_perturb.py \
  --dataset-root COLLEAGUE_BSc_Thesis/Data/audio/audio_loopback_flac \
  --perturbation pitch \
  --mode random \
  --min-cents -200 \
  --max-cents 200 \
  --num-samples 50 \
  --output-csv ADV_ML/output/pistol_pitch_P3_strong.csv \
  --verbose
```

#### Livelli White Noise (W1, W2, W3)

**W1 - White Noise [35-38] dB:**
```bash
python ADV_ML/offline_perturb.py \
  --dataset-root COLLEAGUE_BSc_Thesis/Data/audio/audio_loopback_flac \
  --perturbation white_noise \
  --mode random \
  --min-snr 35 \
  --max-snr 38 \
  --num-samples 50 \
  --output-csv ADV_ML/output/pistol_noiseW_W1_light.csv \
  --verbose
```

**W2 - White Noise [38-42] dB:**
```bash
python ADV_ML/offline_perturb.py \
  --dataset-root COLLEAGUE_BSc_Thesis/Data/audio/audio_loopback_flac \
  --perturbation white_noise \
  --mode random \
  --min-snr 38 \
  --max-snr 42 \
  --num-samples 50 \
  --output-csv ADV_ML/output/pistol_noiseW_W2_medium.csv \
  --verbose
```

**W3 - White Noise [42-45] dB:**
```bash
python ADV_ML/offline_perturb.py \
  --dataset-root COLLEAGUE_BSc_Thesis/Data/audio/audio_loopback_flac \
  --perturbation white_noise \
  --mode random \
  --min-snr 42 \
  --max-snr 45 \
  --num-samples 50 \
  --output-csv ADV_ML/output/pistol_noiseW_W3_strong.csv \
  --verbose
```

#### Livelli Pink Noise (K1, K2)

**K1 - Pink Noise [16-20] dB:**
```bash
python ADV_ML/offline_perturb.py \
  --dataset-root COLLEAGUE_BSc_Thesis/Data/audio/audio_loopback_flac \
  --perturbation pink_noise \
  --mode random \
  --min-snr 16 \
  --max-snr 20 \
  --num-samples 50 \
  --output-csv ADV_ML/output/pistol_noiseK_K1_light.csv \
  --verbose
```

**K2 - Pink Noise [20-24] dB:**
```bash
python ADV_ML/offline_perturb.py \
  --dataset-root COLLEAGUE_BSc_Thesis/Data/audio/audio_loopback_flac \
  --perturbation pink_noise \
  --mode random \
  --min-snr 20 \
  --max-snr 24 \
  --num-samples 50 \
  --output-csv ADV_ML/output/pistol_noiseK_K2_strong.csv \
  --verbose
```

#### Livelli EQ Tilt (E1, E2, E3)

**Nota:** Con `--mode random`, ogni file avrà casualmente boost (50%) o cut (50%). I livelli differiscono per i range di valori.

**E1 - EQ Tilt Leggero [-6, -4] dB cut o [3, 4] dB boost:**
```bash
python ADV_ML/offline_perturb.py \
  --dataset-root COLLEAGUE_BSc_Thesis/Data/audio/audio_loopback_flac \
  --perturbation eq_tilt \
  --mode random \
  --cut-min -6 \
  --cut-max -4 \
  --boost-min 3 \
  --boost-max 4 \
  --num-samples 50 \
  --output-csv ADV_ML/output/pistol_eqtilt_E1_light.csv \
  --verbose
```

**E2 - EQ Tilt Medio [-4, -3] dB cut o [4, 5] dB boost:**
```bash
python ADV_ML/offline_perturb.py \
  --dataset-root COLLEAGUE_BSc_Thesis/Data/audio/audio_loopback_flac \
  --perturbation eq_tilt \
  --mode random \
  --cut-min -4 \
  --cut-max -3 \
  --boost-min 4 \
  --boost-max 5 \
  --num-samples 50 \
  --output-csv ADV_ML/output/pistol_eqtilt_E2_medium.csv \
  --verbose
```

**E3 - EQ Tilt Forte [-5, -3] dB cut o [5, 6] dB boost:**
```bash
python ADV_ML/offline_perturb.py \
  --dataset-root COLLEAGUE_BSc_Thesis/Data/audio/audio_loopback_flac \
  --perturbation eq_tilt \
  --mode random \
  --cut-min -5 \
  --cut-max -3 \
  --boost-min 5 \
  --boost-max 6 \
  --num-samples 50 \
  --output-csv ADV_ML/output/pistol_eqtilt_E3_strong.csv \
  --verbose
```

#### Livelli High-Pass Filter (H1, H2)

**H1 - High-Pass [150, 200] Hz:**
```bash
python ADV_ML/offline_perturb.py \
  --dataset-root COLLEAGUE_BSc_Thesis/Data/audio/audio_loopback_flac \
  --perturbation highpass \
  --mode random \
  --min-hz 150 \
  --max-hz 200 \
  --num-samples 50 \
  --output-csv ADV_ML/output/pistol_hp_H1_light.csv \
  --verbose
```

**H2 - High-Pass [200, 250] Hz:**
```bash
python ADV_ML/offline_perturb.py \
  --dataset-root COLLEAGUE_BSc_Thesis/Data/audio/audio_loopback_flac \
  --perturbation highpass \
  --mode random \
  --min-hz 200 \
  --max-hz 250 \
  --num-samples 50 \
  --output-csv ADV_ML/output/pistol_hp_H2_strong.csv \
  --verbose
```

#### Livelli Low-Pass Filter (L1, L2)

**L1 - Low-Pass [8000, 9000] Hz:**
```bash
python ADV_ML/offline_perturb.py \
  --dataset-root COLLEAGUE_BSc_Thesis/Data/audio/audio_loopback_flac \
  --perturbation lowpass \
  --mode random \
  --min-hz 8000 \
  --max-hz 9000 \
  --num-samples 50 \
  --output-csv ADV_ML/output/pistol_lp_L1_light.csv \
  --verbose
```

**L2 - Low-Pass [9000, 10000] Hz:**
```bash
python ADV_ML/offline_perturb.py \
  --dataset-root COLLEAGUE_BSc_Thesis/Data/audio/audio_loopback_flac \
  --perturbation lowpass \
  --mode random \
  --min-hz 9000 \
  --max-hz 10000 \
  --num-samples 50 \
  --output-csv ADV_ML/output/pistol_lp_L2_strong.csv \
  --verbose
```

### Verificare Tutti i File Generati

Dopo aver generato tutti i livelli, verifica che siano stati creati:

```bash
ls -lh ADV_ML/output/pistol_*.csv
```

Dovresti vedere tutti i file CSV con le loro dimensioni. I file possono essere grandi (centinaia di MB o GB), quindi assicurati di avere spazio su disco sufficiente.

---

## 5. Come Ripulire gli Output quando Non Servono Più

I file CSV generati possono essere molto grandi (centinaia di MB o GB). Quando non ti servono più, puoi cancellarli per liberare spazio.

### Cancellare un Singolo File

```bash
rm ADV_ML/output/pistol_pitch_P2_medium.csv
```

### Cancellare Tutti i File di un Tipo

**⚠️ ATTENZIONE:** Controlla sempre con `ls` prima di fare `rm` per evitare di cancellare file importanti!

**Cancellare tutti i file pitch:**
```bash
# Prima verifica cosa verrà cancellato
ls ADV_ML/output/pistol_pitch_*.csv

# Se va bene, cancella
rm ADV_ML/output/pistol_pitch_*.csv
```

**Cancellare tutti i file noise:**
```bash
# Prima verifica
ls ADV_ML/output/pistol_noise*.csv

# Se va bene, cancella
rm ADV_ML/output/pistol_noise*.csv
```

**Cancellare tutti i file CSV nella cartella output:**
```bash
# Prima verifica (attenzione: questo mostra TUTTI i CSV!)
ls ADV_ML/output/*.csv

# Se va bene, cancella
rm ADV_ML/output/*.csv
```

### Cancellare con Pattern più Specifici

Se in futuro userai altre cartelle (es. `output/random_variants/`), usa pattern più specifici:

```bash
# Verifica prima
ls ADV_ML/output/random_variants/*.csv

# Cancella solo quelli
rm ADV_ML/output/random_variants/*.csv
```

**Suggerimento:** Se lavori con molti file, considera di usare un sistema di versioning o di salvare solo i file più importanti, cancellando gli altri dopo averli usati.

---

## 6. Integrazione con il Codice ML (Pseudocodice)

Questa sezione spiega il flusso di integrazione senza implementare tutto il codice. Il collega userà i CSV generati per valutare l'efficacia delle perturbazioni.

### Flusso Generale

```
1. Il collega carica i dati originali (X_train, X_test, y_train, y_test)
2. Tu generi X_test_pert usando offline_perturb.py (salvi in CSV)
3. Il collega carica X_test_pert dal CSV
4. Il collega valuta il modello su X_test_pert e confronta accuracy
```

### Pseudocodice Python

```python
# ============================================
# STEP 1: Il collega carica i dati originali
# ============================================
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score

# Carica dataset originale
X_train = np.load("features/X_train.npy")
X_test = np.load("features/X_test.npy")
y_train = np.load("features/y_train.npy")
y_test = np.load("features/y_test.npy")

# ============================================
# STEP 2: Il collega addestra il modello (baseline)
# ============================================
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# Valuta baseline (senza perturbazioni)
y_pred_baseline = model.predict(X_test)
accuracy_baseline = accuracy_score(y_test, y_pred_baseline)
print(f"Accuracy baseline: {accuracy_baseline:.4f}")

# ============================================
# STEP 3: Tu generi X_test_pert (già fatto con offline_perturb.py)
# ============================================
# Hai già eseguito:
# python ADV_ML/offline_perturb.py ... --output-csv ADV_ML/output/pistol_pitch_P2_medium.csv

# ============================================
# STEP 4: Il collega carica X_test_pert dal CSV
# ============================================
X_test_pert = np.loadtxt("ADV_ML/output/pistol_pitch_P2_medium.csv", delimiter=",")

# Verifica che le dimensioni siano corrette
assert X_test_pert.shape[0] == len(y_test), "Numero campioni non corrisponde!"
print(f"X_test_pert shape: {X_test_pert.shape}")

# ============================================
# STEP 5: Il collega valuta il modello su X_test_pert
# ============================================
y_pred_pert = model.predict(X_test_pert)
accuracy_pert = accuracy_score(y_test, y_pred_pert)
print(f"Accuracy con perturbazione: {accuracy_pert:.4f}")

# ============================================
# STEP 6: Confronto risultati
# ============================================
degradation = accuracy_baseline - accuracy_pert
degradation_percent = (degradation / accuracy_baseline) * 100

print(f"\n{'='*50}")
print(f"Risultati:")
print(f"  Accuracy baseline:     {accuracy_baseline:.4f}")
print(f"  Accuracy perturbata:   {accuracy_pert:.4f}")
print(f"  Degradazione:          {degradation:.4f} ({degradation_percent:.1f}%)")
print(f"{'='*50}")
```

### Spiegazione del Flusso

1. **Il collega carica i dati:** Usa i suoi file `.npy` o `.csv` con `X_train`, `X_test`, `y_train`, `y_test`.

2. **Tu generi X_test_pert:** Esegui `offline_perturb.py` che carica i FLAC, applica la perturbazione, estrae le feature e salva in CSV. Il CSV ha lo stesso formato delle feature originali (stesso numero di colonne).

3. **Il collega carica X_test_pert:** Usa `np.loadtxt()` o `pd.read_csv()` per caricare il CSV. **Importante:** `X_test_pert` deve avere lo stesso numero di righe di `y_test` (stesso numero di campioni).

4. **Il collega valuta:** Usa `model.predict(X_test_pert)` per ottenere le predizioni sul dataset perturbato, poi calcola l'accuracy con `accuracy_score(y_test, y_pred_pert)`.

5. **Confronto:** Confronta `accuracy_baseline` (senza perturbazioni) con `accuracy_pert` (con perturbazioni). Se `accuracy_pert < accuracy_baseline`, la perturbazione ha degradato le performance del modello.

### Esempio con Più Livelli

Se hai generato più livelli (P1, P2, P3, W1, W2, W3, ecc.), puoi valutare tutti:

```python
# Lista di tutti i CSV generati
perturbation_files = [
    ("P1 (pitch ±100c)", "ADV_ML/output/pistol_pitch_P1_light.csv"),
    ("P2 (pitch ±150c)", "ADV_ML/output/pistol_pitch_P2_medium.csv"),
    ("P3 (pitch ±200c)", "ADV_ML/output/pistol_pitch_P3_strong.csv"),
    ("W1 (white 35-38dB)", "ADV_ML/output/pistol_noiseW_W1_light.csv"),
    ("W2 (white 38-42dB)", "ADV_ML/output/pistol_noiseW_W2_medium.csv"),
    ("W3 (white 42-45dB)", "ADV_ML/output/pistol_noiseW_W3_strong.csv"),
    ("K1 (pink 16-20dB)", "ADV_ML/output/pistol_noiseK_K1_light.csv"),
    ("K2 (pink 20-24dB)", "ADV_ML/output/pistol_noiseK_K2_strong.csv"),
    ("E1 (EQ tilt cut)", "ADV_ML/output/pistol_eqtilt_E1_light.csv"),
    ("E2 (EQ tilt mixed)", "ADV_ML/output/pistol_eqtilt_E2_medium.csv"),
    ("E3 (EQ tilt boost)", "ADV_ML/output/pistol_eqtilt_E3_strong.csv"),
    ("H1 (HP 150-200Hz)", "ADV_ML/output/pistol_hp_H1_light.csv"),
    ("H2 (HP 200-250Hz)", "ADV_ML/output/pistol_hp_H2_strong.csv"),
    ("L1 (LP 8000-9000Hz)", "ADV_ML/output/pistol_lp_L1_light.csv"),
    ("L2 (LP 9000-10000Hz)", "ADV_ML/output/pistol_lp_L2_strong.csv"),
]

results = []

for name, filepath in perturbation_files:
    X_test_pert = np.loadtxt(filepath, delimiter=",")
    y_pred_pert = model.predict(X_test_pert)
    accuracy_pert = accuracy_score(y_test, y_pred_pert)
    
    results.append({
        "perturbation": name,
        "accuracy": accuracy_pert,
        "degradation": accuracy_baseline - accuracy_pert
    })
    
    print(f"{name:25s} | Accuracy: {accuracy_pert:.4f} | Degradazione: {accuracy_baseline - accuracy_pert:.4f}")

# Trova la perturbazione più efficace (maggiore degradazione)
best_perturbation = max(results, key=lambda x: x["degradation"])
print(f"\nPerturbazione più efficace: {best_perturbation['perturbation']} (degradazione: {best_perturbation['degradation']:.4f})")
```

---

## 7. Troubleshooting

### Problema: "No module named 'librosa'"

**Soluzione:** Installa le dipendenze:
```bash
cd ADV_ML
pip install -r requirements.txt
```

### Problema: "File FLAC non trovati"

**Soluzione:** Verifica il percorso:
```bash
ls COLLEAGUE_BSc_Thesis/Data/audio/audio_loopback_flac/*.flac | head -5
```

Se la cartella non esiste o è vuota, contatta il collega per ottenere i dati.

### Problema: "CSV troppo grande, non posso caricarlo"

**Soluzione:** Usa `np.loadtxt()` con `max_rows` o carica in chunks:
```python
# Carica solo prime N righe (per test)
X_test_pert = np.loadtxt("file.csv", delimiter=",", max_rows=100)

# Oppure carica in chunks (per file molto grandi)
# (richiede implementazione custom)
```

### Problema: "Shape mismatch tra X_test_pert e y_test"

**Soluzione:** Verifica che stai usando lo stesso numero di file:
```python
print(f"X_test_pert shape: {X_test_pert.shape}")
print(f"y_test shape: {y_test.shape}")

# Se non corrispondono, usa solo i primi N
min_samples = min(X_test_pert.shape[0], len(y_test))
X_test_pert = X_test_pert[:min_samples]
y_test = y_test[:min_samples]
```

---

## 8. Riepilogo Comandi Rapidi

### Generare X_test_pert

```bash
# Pitch shift fisso
python ADV_ML/offline_perturb.py \
  --dataset-root COLLEAGUE_BSc_Thesis/Data/audio/audio_loopback_flac \
  --perturbation pitch \
  --mode fixed \
  --cents 150 \
  --num-samples 50 \
  --output-csv ADV_ML/output/pistol_pitch_P2_medium.csv

# White noise random
python ADV_ML/offline_perturb.py \
  --dataset-root COLLEAGUE_BSc_Thesis/Data/audio/audio_loopback_flac \
  --perturbation white_noise \
  --mode random \
  --min-snr 35 \
  --max-snr 45 \
  --num-samples 50 \
  --output-csv ADV_ML/output/pistol_noiseW_L1.csv

# Pink noise random
python ADV_ML/offline_perturb.py \
  --dataset-root COLLEAGUE_BSc_Thesis/Data/audio/audio_loopback_flac \
  --perturbation pink_noise \
  --mode random \
  --min-snr 16 \
  --max-snr 24 \
  --num-samples 50 \
  --output-csv ADV_ML/output/pistol_noiseK_test.csv

# EQ tilt random
python ADV_ML/offline_perturb.py \
  --dataset-root COLLEAGUE_BSc_Thesis/Data/audio/audio_loopback_flac \
  --perturbation eq_tilt \
  --mode random \
  --boost-min 3 \
  --boost-max 6 \
  --cut-min -6 \
  --cut-max -3 \
  --num-samples 50 \
  --output-csv ADV_ML/output/pistol_eqtilt_test.csv

# High-pass filter random
python ADV_ML/offline_perturb.py \
  --dataset-root COLLEAGUE_BSc_Thesis/Data/audio/audio_loopback_flac \
  --perturbation highpass \
  --mode random \
  --min-hz 150 \
  --max-hz 250 \
  --num-samples 50 \
  --output-csv ADV_ML/output/pistol_hp_test.csv

# Low-pass filter random
python ADV_ML/offline_perturb.py \
  --dataset-root COLLEAGUE_BSc_Thesis/Data/audio/audio_loopback_flac \
  --perturbation lowpass \
  --mode random \
  --min-hz 8000 \
  --max-hz 10000 \
  --num-samples 50 \
  --output-csv ADV_ML/output/pistol_lp_test.csv
```

### Verificare CSV

```python
import numpy as np
X = np.loadtxt("ADV_ML/output/pistol_pitch_P2_medium.csv", delimiter=",")
print(f"Shape: {X.shape}, Min: {X.min():.3f}, Max: {X.max():.3f}")
```

### Caricare e Valutare

```python
X_test_pert = np.loadtxt("ADV_ML/output/pistol_pitch_P2_medium.csv", delimiter=",")
y_pred = model.predict(X_test_pert)
accuracy = accuracy_score(y_test, y_pred)
```

---

**Fine guida**

