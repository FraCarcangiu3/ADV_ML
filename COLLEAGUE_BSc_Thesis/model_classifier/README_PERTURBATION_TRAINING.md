# Guida: Training e Valutazione con Perturbazione Audio

## Panoramica

Questo sistema permette di valutare i modelli del collega con perturbazioni audio applicate **solo al test set**, mantenendo il training su dati clean.

**Strategia implementata**:
- Training baseline: usa `deep_cv.py` originale (dati clean)
- Valutazione con perturbazione: usa `eval_perturbation_cv.py` (applica rumore solo al test set)

---

## File Creati/Modificati

### Nuovi File
1. **`perturbation_utils.py`**: Wrapper per preset di perturbazione
2. **`eval_perturbation_cv.py`**: Script per valutazione 9-fold con perturbazione
3. **`README_PERTURBATION_TRAINING.md`**: Questa guida

### File Modificati
1. **`deep_cv.py`**: Aggiunto salvataggio checkpoint per ogni fold (modifica minimale, compatibile)

---

## Workflow Completo

### STEP 1: Training Baseline (9-fold CV)

```bash
cd COLLEAGUE_BSc_Thesis

# Training normale (usa codice originale)
python -m model_classifier.deep_cv
```

**Cosa fa**:
- Addestra 3 modelli (ResNet18MT, CRNN, Conv1DSeparable) con 9-fold CV
- Salva checkpoint per ogni fold in: `model_classifier/checkpoints/<model>_fold<N>.pth`
- Genera risultati baseline in: `model_classifier/results_<timestamp>.txt`

**Tempo stimato**: 1-3 ore (dipende da dataset e hardware)

**Output checkpoint**:
```
model_classifier/checkpoints/
├── resnet18_mel96_fold1.pth
├── resnet18_mel96_fold2.pth
├── ...
├── resnet18_mel96_fold9.pth
├── crnn_mel80_fold1.pth
├── ...
└── conv1d_sep_ds48k_fold1.pth
```

---

### STEP 2: Valutazione con Perturbazione

```bash
cd COLLEAGUE_BSc_Thesis

# Valutazione con perturbazione pitch +150 cents
python -m model_classifier.eval_perturbation_cv \
    --model resnet18_mel96 \
    --perturb-preset pitch_P2_pos \
    --results-csv results/perturb_pitch_P2_pos.csv
```

**Cosa fa**:
- Carica checkpoint salvati in STEP 1
- Per ogni fold:
  - Valuta baseline (test set clean)
  - Applica perturbazione al test set
  - Valuta con perturbazione
  - Calcola degradazione
- Salva risultati aggregati in CSV

**Tempo stimato**: 5-15 minuti (dipende da dataset)

**Output CSV**:
```csv
fold,preset,n_test,angle_base,angle_pert,angle_drop,dist_base,dist_pert,dist_drop,joint_base,joint_pert,joint_drop,mae_base,mae_pert,mae_increase
1,pitch_P2_pos,108,0.6200,0.4500,+0.1700,0.7100,0.6300,+0.0800,0.4800,0.3200,+0.1600,28.34,42.56,+14.22
2,pitch_P2_pos,108,0.6100,0.4400,+0.1700,0.7000,0.6200,+0.0800,0.4700,0.3100,+0.1600,29.12,43.01,+13.89
...
mean,pitch_P2_pos,972,0.6150,0.4450,+0.1700,0.7050,0.6250,+0.0800,0.4750,0.3150,+0.1600,28.73,42.79,+14.06
```

---

## Preset Disponibili

### Pitch Shift
- `pitch_P1_pos`: +100 cents (light, positivo)
- `pitch_P2_pos`: +150 cents (medium, positivo) ⭐ **Raccomandato per primo test**
- `pitch_P3_pos`: +200 cents (strong, positivo)
- `pitch_P1_neg`: -100 cents (light, negativo)
- `pitch_P2_neg`: -150 cents (medium, negativo)
- `pitch_P3_neg`: -200 cents (strong, negativo)

### White Noise (SNR in dB)
- `white_W1`: 42 dB (light)
- `white_W2`: 40 dB (medium)
- `white_W3`: 38 dB (strong)

### Pink Noise (SNR in dB)
- `pink_K1`: 22 dB (light)
- `pink_K2`: 20 dB (medium)
- `pink_K3`: 18 dB (strong)

### EQ Tilt
- `eq_boost_light`: +3.0 dB
- `eq_boost_medium`: +4.5 dB
- `eq_boost_strong`: +6.0 dB
- `eq_cut_light`: -3.0 dB
- `eq_cut_medium`: -6.0 dB
- `eq_cut_strong`: -9.0 dB

### Filtri
- `hp_150`: High-pass 150 Hz
- `hp_200`: High-pass 200 Hz
- `hp_250`: High-pass 250 Hz
- `lp_8000`: Low-pass 8000 Hz
- `lp_10000`: Low-pass 10000 Hz
- `lp_12000`: Low-pass 12000 Hz

---

## Parametri Script

### `eval_perturbation_cv.py`

```bash
python -m model_classifier.eval_perturbation_cv \
    --model <nome_modello> \
    --perturb-preset <preset> \
    [--results-csv <path>] \
    [--max-samples <N>]
```

**Parametri**:
- `--model`: Modello da valutare (`resnet18_mel96`, `crnn_mel80`, `conv1d_sep_ds48k`)
- `--perturb-preset`: **Obbligatorio**. Nome preset (es. `pitch_P2_pos`)
- `--results-csv`: Path CSV output (default: `model_classifier/perturbation_cv_<preset>.csv`)
- `--max-samples`: Limita numero sample per test rapido (default: tutti)

---

## Esempi Completi

### Test Singolo Preset

```bash
cd COLLEAGUE_BSc_Thesis

# 1. Training baseline (se non già fatto)
python -m model_classifier.deep_cv

# 2. Valutazione con pitch +150 cents
python -m model_classifier.eval_perturbation_cv \
    --model resnet18_mel96 \
    --perturb-preset pitch_P2_pos

# 3. Visualizza risultati
cat model_classifier/perturbation_cv_pitch_P2_pos.csv
```

### Test Tutti i Preset Pitch

```bash
cd COLLEAGUE_BSc_Thesis

for preset in pitch_P1_pos pitch_P2_pos pitch_P3_pos pitch_P1_neg pitch_P2_neg pitch_P3_neg; do
    echo "Testing $preset..."
    python -m model_classifier.eval_perturbation_cv \
        --model resnet18_mel96 \
        --perturb-preset $preset \
        --results-csv results/perturb_${preset}.csv
done
```

### Test con Subset Ridotto (per debug)

```bash
# Test rapido con 200 sample
python -m model_classifier.eval_perturbation_cv \
    --model resnet18_mel96 \
    --perturb-preset pitch_P2_pos \
    --max-samples 200
```

---

## Interpretazione Risultati CSV

### Colonne CSV

- `fold`: Numero fold (1-9) o "mean" per media
- `preset`: Nome preset perturbazione
- `n_test`: Numero sample nel test set
- `angle_base`: Accuracy direzione baseline (clean)
- `angle_pert`: Accuracy direzione con perturbazione
- `angle_drop`: Degradazione direzione (`angle_base - angle_pert`)
- `dist_base`: Accuracy distanza baseline
- `dist_pert`: Accuracy distanza con perturbazione
- `dist_drop`: Degradazione distanza
- `joint_base`: Accuracy congiunta baseline
- `joint_pert`: Accuracy congiunta con perturbazione
- `joint_drop`: Degradazione congiunta
- `mae_base`: Mean Absolute Error angolare baseline (°)
- `mae_pert`: MAE angolare con perturbazione (°)
- `mae_increase`: Aumento MAE (`mae_pert - mae_base`)

### Valori Attesi

**Baseline (clean)**:
- Direction accuracy: ~0.50-0.70 (random = 0.25)
- Distance accuracy: ~0.55-0.75 (random = 0.33)
- Joint accuracy: ~0.30-0.50

**Con perturbazione pitch +150 cents**:
- Direction accuracy: ~0.35-0.55 (drop ~0.10-0.20)
- Distance accuracy: ~0.45-0.65 (drop ~0.05-0.15)
- Joint accuracy: ~0.20-0.35 (drop ~0.10-0.20)

**Degradazione positiva** = perturbazione efficace (modello confuso dal rumore)

---

## Come Funziona Internamente

### 1. Caricamento Waveform

Il waveform viene caricato da CSV in `AudioFeatureDataset.__getitem__()`:
```python
audio_mat = pd.read_csv(audio_path, dtype=np.float32).values  # Shape: (frames, 8 channels)
```

### 2. Applicazione Perturbazione

In `AudioFeatureDatasetWithPerturbation.__getitem__()`:
```python
if perturbation_config is not None:
    audio_mat = apply_perturbation_waveform(audio_mat, AUDIO_SR, preset_name)
```

La perturbazione viene applicata **PRIMA** della feature extraction (log-Mel o raw1d).

### 3. Feature Extraction

Dopo la perturbazione, le feature vengono estratte normalmente:
- `mel_ipd`: log-Mel + IPD/ILD
- `raw1d`: waveform downsampled

### 4. Valutazione

Il modello addestrato valuta sia baseline che perturbato sullo stesso test set.

---

## Troubleshooting

### Errore: "Checkpoint non trovato"

**Causa**: Non hai ancora eseguito il training baseline.

**Soluzione**:
```bash
python -m model_classifier.deep_cv
```

### Errore: "Preset non riconosciuto"

**Causa**: Nome preset errato.

**Soluzione**: Verifica preset disponibili:
```python
from model_classifier.perturbation_utils import list_available_presets
print(list_available_presets())
```

### Errore: "Cannot import ADV_ML/audio_effects"

**Causa**: ADV_ML non trovato nel path.

**Soluzione**: Verifica struttura progetto:
```
AssaultCube Server/
├── ADV_ML/
│   └── audio_effects.py
└── COLLEAGUE_BSc_Thesis/
    └── model_classifier/
        └── eval_perturbation_cv.py
```

### Performance Lente

**Soluzioni**:
- Usa `--max-samples` per test rapido
- Usa GPU se disponibile (rilevamento automatico)
- Riduci `num_workers` nel DataLoader se necessario

---

## Prossimi Passi

### 1. Sweep Completo Preset

Testare tutti i 18 preset su tutti i 3 modelli:
```bash
for model in resnet18_mel96 crnn_mel80 conv1d_sep_ds48k; do
    for preset in pitch_P1_pos pitch_P2_pos ...; do
        python -m model_classifier.eval_perturbation_cv \
            --model $model --perturb-preset $preset
    done
done
```

### 2. Analisi Risultati

- Creare grafici degradazione vs intensità perturbazione
- Confrontare robustezza dei 3 modelli
- Identificare perturbazioni più efficaci

### 3. Training con Perturbazione (Futuro)

Per testare training su dati perturbati, creare variante di `deep_cv.py` che applica perturbazione anche al training set.

---

## Note Tecniche

### Compatibilità

- ✅ **deep_cv.py**: Modificato minimamente (solo salvataggio checkpoint)
- ✅ **Backward compatible**: Funziona anche senza checkpoint (skip fold)
- ✅ **Nessuna dipendenza nuova**: Riusa librerie esistenti

### Memoria

- Tutto on-the-fly: nessun CSV temporaneo gigante
- Perturbazione applicata al volo durante DataLoader
- Solo output finale aggregato in CSV

### Riproducibilità

- Stesso seed (`SEED=42`) per split CV
- Stesso split train/test del training originale
- Perturbazione deterministica (preset fissi)

---

**Fine guida** 🎯

