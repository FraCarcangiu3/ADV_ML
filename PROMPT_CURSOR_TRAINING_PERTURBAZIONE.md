# Prompt per Cursor: Training con Perturbazione Audio

**COPIA E INCOLLA QUESTO PROMPT IN CURSOR (dalla root del progetto)**

---

## Contesto

Sto lavorando nella repo: `COLLEAGUE_BSc_Thesis/`

Il mio collega ha già implementato:
- Pipeline di training con **9-fold cross-validation** (8 train / 1 test)
- **3 modelli deep learning**: ResNet18MT, CRNN, Conv1DSeparable
- Logica di feature extraction e CV in `model_classifier/deep_cv.py`

Io ho implementato la parte **anti-cheat con perturbazioni audio** in `ADV_ML/`:
- `ADV_ML/audio_effects.py`: funzioni per pitch shift, white noise, pink noise, EQ tilt, HP/LP filter
- `ADV_ML/offline_perturb.py`: wrapper per perturbazioni
- Range calibrati per replicare il client C++ di AssaultCube

---

## Obiettivo

Voglio fare un **esperimento ML completo** sul progetto del collega:
- Usare il SUO codice di training (9-fold)
- Avere una **seconda versione** con audio perturbato
- **Confrontare accuracies baseline (clean) vs perturbate**

---

## Task per Te (Cursor)

### 1. Analisi del Codice Esistente

Analizza `model_classifier/deep_cv.py` e moduli collegati per capire:
- Dove vengono caricati gli input (waveform o CSV)
- Dove vengono estratte le feature (log-Mel + IPD/ILD o raw waveform)
- Dove viene eseguito il 9-fold cross-validation
- Dove vengono calcolate le metriche (angle accuracy, distance accuracy, joint accuracy, MAE)

### 2. Implementa Soluzione MINIMAMENTE INVASIVA

Voglio poter eseguire **due scenari** usando sempre 9-fold:

**Scenario A – Baseline (già esistente):**
- Training su dati **CLEAN**
- Test su dati **CLEAN**
- Ottengo accuracies baseline (direction, distance, joint)

**Scenario B – Con perturbazione:**
- Stessa cross-validation, stesso modello, stessi hyperparameters
- Con perturbazione applicata all'audio **PRIMA della feature extraction** (a livello waveform)
- Perturbazione controllata da preset (es. `pitch_P2_pos` = pitch +150 cents)
- Valutare:
  - **Opzione 1**: Training CLEAN + Test PERTURBATO (preferito per iniziare)
  - **Opzione 2**: Training PERTURBATO + Test PERTURBATO (per test futuri)

**Vincolo**: Lascia `deep_cv.py` il più possibile intatto e:
- Crea nuovo script `model_classifier/train_with_perturbation.py`, oppure
- Aggiungi flag CLI (`--with-perturbation`, `--perturb-preset`) che abilita versione "noisy"

### 3. Integrazione con Effetti Esistenti

**Riusa funzioni da `ADV_ML/audio_effects.py`**:
- `apply_pitch_shift(signal, sr, cents)`
- `add_white_noise(signal, sr, snr_db)`
- `add_pink_noise(signal, sr, snr_db)`
- `apply_eq_tilt(signal, sr, tilt_db)`
- `apply_highpass(signal, sr, cutoff_hz)`
- `apply_lowpass(signal, sr, cutoff_hz)`

**Crea funzione wrapper**:
```python
from ADV_ML.audio_effects import apply_pitch_shift, add_white_noise, add_pink_noise

def apply_perturbation_waveform(waveform, sr, preset_name):
    """
    Applica perturbazione al waveform prima della feature extraction.
    
    Args:
        waveform: np.ndarray (frames, channels) o (channels, frames)
        sr: sample rate (96000)
        preset_name: 'pitch_P2_pos', 'white_W2', 'pink_K2', etc.
    
    Returns:
        waveform perturbato (stessa shape)
    """
    # Mappa preset → tipo effetto + parametri
    # Usa range calibrati dal client C++ (weapon/usp):
    # - Pitch: [-200, -75] ∪ [75, 200] cents
    # - White noise: [35, 45] dB SNR
    # - Pink noise: [16, 24] dB SNR
    ...
    return waveform_perturbed
```

**Preset da implementare** (almeno questi per pistola):
- `pitch_P1_pos`: +100 cents
- `pitch_P2_pos`: +150 cents (priorità per primo test)
- `pitch_P3_pos`: +200 cents
- `pitch_P1_neg`: -100 cents
- `pitch_P2_neg`: -150 cents
- `pitch_P3_neg`: -200 cents
- `white_W1`: 42 dB SNR (light)
- `white_W2`: 40 dB SNR (medium)
- `white_W3`: 38 dB SNR (strong)
- `pink_K1`: 22 dB SNR (light)
- `pink_K2`: 20 dB SNR (medium)
- `pink_K3`: 18 dB SNR (strong)

### 4. Nuovo Flusso di Training + Valutazione

**Esempi di comandi che voglio poter lanciare**:

```bash
cd COLLEAGUE_BSc_Thesis

# 1) Training baseline (clean) - usa codice originale
python -m model_classifier.deep_cv

# 2) Valutazione con perturbazione sul test set (stessi checkpoint)
python -m model_classifier.eval_perturbation_cv \
    --checkpoint-dir model_classifier/checkpoints \
    --perturb-preset pitch_P2_pos \
    --results-csv results/perturb_pitch_P2_pos.csv

# Oppure (se preferisci):
# 3) Training + valutazione tutto in uno con perturbazione
python -m model_classifier.deep_cv \
    --with-perturbation \
    --perturb-preset pitch_P2_pos \
    --results-csv results/perturb_pitch_P2_pos.csv
```

**Strategia preferita**: 
- Mantieni training baseline intatto (usa `deep_cv.py` normale)
- Crea script separato per applicare perturbazione al **test set di ogni fold**
- Ricarica checkpoint già addestrati e valuta con audio perturbato

### 5. Output Richiesto

**File da creare**:
1. `model_classifier/eval_perturbation_cv.py`: Script per valutazione 9-fold con perturbazione
2. `model_classifier/perturbation_utils.py`: Funzioni di utilità per applicare preset
3. `model_classifier/README_PERTURBATION_TRAINING.md`: Guida uso

**Nel README includi**:
- Quali script usare
- Parametri supportati (`--model`, `--perturb-preset`, `--max-samples`)
- Come vengono calcolate le metriche
- Come confrontare accuracies baseline vs perturbate
- Esempio output CSV

**Output CSV** (una riga per fold, più una riga di media):
```csv
fold,preset,n_test,angle_base,angle_pert,angle_drop,dist_base,dist_pert,dist_drop,joint_base,joint_pert,joint_drop,mae_base,mae_pert,mae_increase
1,pitch_P2_pos,108,0.6200,0.4500,+0.1700,0.7100,0.6300,+0.0800,0.4800,0.3200,+0.1600,28.34,42.56,+14.22
2,pitch_P2_pos,108,0.6100,0.4400,+0.1700,0.7000,0.6200,+0.0800,0.4700,0.3100,+0.1600,29.12,43.01,+13.89
...
mean,pitch_P2_pos,972,0.6150,0.4450,+0.1700,0.7050,0.6250,+0.0800,0.4750,0.3150,+0.1600,28.73,42.79,+14.06
```

---

## Vincoli Importanti

1. **NON modificare deep_cv.py in modo distruttivo**
   - Se devi modificare, fallo in modo compatibile e ben commentato
   - Preferisci creare nuovi script

2. **Nessune dipendenze nuove**
   - Riusa: numpy, torch, librosa, scipy, pandas, sklearn
   - Già presenti nel progetto

3. **Nessun CSV temporaneo gigante**
   - Tutto on-the-fly in memoria
   - Solo output finale aggregato in CSV

4. **Focus**: UN PRIMO ESPERIMENTO COMPLETO
   - Misurare quanto una perturbazione (es. pitch +150c) abbatte l'accuracy
   - Rispetto al training e test originali

---

## Passi Operativi per Te

1. **Analizza** `model_classifier/deep_cv.py` e dataset in `Data/csv/`

2. **Proponi brevemente** (nei commenti o README) quale strategia hai scelto:
   - Rumore solo su test (preferito)
   - Training + test rumoroso
   - Entrambe le opzioni con flag

3. **Implementa** versione funzionante per **almeno UN preset**: `pitch_P2_pos`
   - Coerente con range del client C++
   - Applicato a livello waveform prima feature extraction

4. **Testa** che funzioni su subset piccolo (es. 100 sample, 2 fold)

5. **Fornisci riepilogo**:
   - File creati/modificati
   - Comandi per lanciare training baseline
   - Comandi per valutare con perturbazione
   - Come leggere CSV risultati

---

## Domande Guida per Te

- Dove nel codice del collega viene caricato il waveform dal CSV?
- Dove posso inserire la perturbazione PRIMA della feature extraction?
- Come posso riusare la logica di 9-fold senza duplicare codice?
- Come salvo i checkpoint di ogni fold per poterli ricaricare?

---

**IMPORTANTE**: Lavora in modalità auto, ma mantieni il codice del collega il più possibile intatto. Preferisco nuovi script separati piuttosto che modifiche invasive.

**INIZIA L'ANALISI E IMPLEMENTAZIONE ORA.** 🚀

