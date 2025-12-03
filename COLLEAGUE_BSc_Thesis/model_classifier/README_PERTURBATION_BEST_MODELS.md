# Valutazione Perturbazioni su Modelli Migliori

Questo documento descrive il sistema di testing completo per valutare l'effetto delle perturbazioni audio sui due modelli migliori del collega.

## 🎯 Modelli Testati

Usiamo **SOLO** i due checkpoint migliori (NO retraining):

| Modello | Checkpoint | Ottimizzato per | Feature Type |
|---------|-----------|-----------------|--------------|
| **CRNN MEL80** | `crnn_mel80_best_angle.pt` | Direzione (angle) | MEL+IPD/ILD (80 bins) |
| **ResNet18 MEL96** | `resnet18_mel96_best_dist_angle_weighted.pt` | Distanza (+ angle weighted) | MEL+IPD/ILD (96 bins) |

## 🔊 Perturbazioni Testate

Ogni perturbazione viene testata a **3 livelli di intensità**: LOW, MEDIUM, HIGH.

### Perturbazioni Singole

| Tipo | LOW | MEDIUM | HIGH | Note |
|------|-----|--------|------|------|
| **Pitch Shift (positivo)** | +75 cents | +150 cents | +200 cents | ~0.75-2 semitoni |
| **Pitch Shift (negativo)** | -75 cents | -150 cents | -200 cents | ~0.75-2 semitoni |
| **White Noise** | SNR 42 dB | SNR 40 dB | SNR 38 dB | Più basso SNR = più rumore |
| **Pink Noise** | SNR 22 dB | SNR 20 dB | SNR 18 dB | Filtro 1/f, disturba fase |
| **EQ Tilt (boost)** | +3 dB | +4.5 dB | +6 dB | Brighten (high-shelf @ 2kHz) |
| **EQ Tilt (cut)** | -3 dB | -6 dB | -9 dB | Darken (high-shelf @ 2kHz) |
| **High-Pass Filter** | 150 Hz | 200 Hz | 250 Hz | Taglia basse frequenze |
| **Low-Pass Filter** | 12 kHz | 10 kHz | 8 kHz | Taglia alte frequenze |

### Nuovi Effetti Spaziali (disturbare IPD/ILD)

| Tipo | LOW | MEDIUM | HIGH | Note |
|------|-----|--------|------|------|
| **Spatial Delay** | ±2 samples | ±5 samples | ±10 samples | Micro-delay tra canali (~0.02-0.1ms @ 96kHz), disturba IPD |
| **Channel Gain Jitter** | ±0.5 dB | ±1.0 dB | ±1.5 dB | Variazioni gain per canale, disturba ILD |
| **Multi-Channel White Noise** | SNR 42 dB | SNR 40 dB | SNR 38 dB | Rumore indipendente per canale |
| **Multi-Channel Pink Noise** | SNR 22 dB | SNR 20 dB | SNR 18 dB | Pink noise indipendente per canale |

### Perturbazioni Combo

Combinazioni di più perturbazioni applicate in sequenza:

| Combo | MEDIUM | HIGH |
|-------|--------|------|
| **Pink + EQ Boost** | Pink 20dB + EQ +4.5dB | Pink 18dB + EQ +6dB |
| **Pink + High-Pass** | Pink 20dB + HP 200Hz | Pink 18dB + HP 250Hz |

## 🚀 Come Eseguire i Test

### Prerequisiti

```bash
cd /Users/francesco03/Documents/GitHub/AssaultCube\ Server/COLLEAGUE_BSc_Thesis
conda activate ac_ml  # o il tuo env Python
```

### Comando Completo

Esegui tutti i test (circa 10-20 minuti, dipende dal numero di sample):

```bash
python -m model_classifier.run_best_models_perturb_sweep
```

**Opzioni:**
- `--max-samples N`: limita a N campioni del test set (default: tutti ~194 = 20% di 970)

Esempio con test rapido (100 sample):

```bash
python -m model_classifier.run_best_models_perturb_sweep --max-samples 100
```

## 📈 Analisi Risultati (dopo il run)

Dopo aver eseguito il sweep, analizza i risultati con:

```bash
python -m model_classifier.analyze_perturbation_results
```

Questo script genera:
- Statistiche per modello
- Top 10 perturbazioni più efficaci
- Ranking per tipo perturbazione
- Effetto dei livelli (LOW/MED/HIGH)
- Raccomandazioni per la tesi

## 📊 Output Generati

Tutti i risultati vengono salvati in `model_classifier/results/`:

### 1. CSV Riassuntivo

**File:** `results/summary_perturbations_best_models.csv`

Contiene una riga per ogni combinazione (modello × perturbazione × livello).

**Colonne principali:**
- `model`: identificativo modello (`crnn_angle`, `resnet_dist`)
- `model_desc`: descrizione leggibile
- `perturbation`: tipo perturbazione (es. `pink_noise`, `pitch_pos`, `combo_pink_eq`)
- `level`: intensità (`LOW`, `MEDIUM`, `HIGH`)
- `config`: parametri effettivi usati
- `n_test`: numero campioni test set
- **Metriche baseline (senza rumore):**
  - `angle_base`: accuracy direzione baseline
  - `dist_base`: accuracy distanza baseline
  - `joint_base`: accuracy congiunta (direzione+distanza) baseline
  - `mae_base`: Mean Absolute Error angolare baseline (gradi)
- **Metriche con perturbazione:**
  - `angle_pert`: accuracy direzione con rumore
  - `dist_pert`: accuracy distanza con rumore
  - `joint_pert`: accuracy congiunta con rumore
  - `mae_pert`: MAE angolare con rumore
- **Degradazione (drop):**
  - `angle_drop`: quanto cala accuracy direzione (positivo = peggiora)
  - `dist_drop`: quanto cala accuracy distanza
  - `joint_drop`: quanto cala accuracy congiunta
  - `mae_increase`: quanto aumenta MAE (positivo = peggiora)

### 2. Confusion Matrices

**Cartella:** `results/confusion_matrices/`

Per ogni test viene salvata la confusion matrix in formato CSV:
- `{model}_{perturbation}_{level}_cm_angle.csv`: confusione classi direzione
- `{model}_{perturbation}_{level}_cm_dist.csv`: confusione classi distanza
- `{model}_baseline_cm_angle.csv`: baseline direzione
- `{model}_baseline_cm_dist.csv`: baseline distanza

**Formato:** matrice NxN dove `matrix[i][j]` = numero di sample con label vera `i` predetti come `j`.

## 📖 Come Interpretare i Risultati

### Leggere i Drop

I valori `*_drop` e `mae_increase` indicano la **degradazione** causata dalla perturbazione:

- **Valori positivi** → perturbazione peggiora le performance (goal per anti-cheat!)
- **Valori vicini a 0** → perturbazione NON influisce (modello robusto)
- **Valori negativi** → perturbazione migliora le performance (anomalo, può succedere su sample piccoli)

### Risultati Attesi (basati su test preliminari)

**Perturbazioni POCO efficaci** (drop ~0-5%):
- Pitch shift (positivo/negativo): le feature IPD/ILD sono invarianti al pitch
- EQ tilt: cambia spettro ma non geometria spaziale
- Low-pass/High-pass moderati: stessa ragione

**Perturbazioni PIÙ efficaci** (drop ~10-20%):
- **Pink noise** (forte): disturba differenze di fase tra canali (IPD)
- **White noise** (forte): disturba tutto lo spettro
- **Combo pink + altro**: effetto cumulativo

### Esempio di Lettura

Supponiamo una riga CSV:

```csv
model,perturbation,level,angle_base,angle_pert,angle_drop,joint_base,joint_pert,joint_drop,mae_base,mae_pert,mae_increase
crnn_angle,pink_noise,HIGH,0.7389,0.5722,0.1667,0.5000,0.3259,0.1741,30.25,54.08,23.83
```

**Interpretazione:**
- Modello CRNN (ottimizzato per angolo)
- Perturbazione: pink noise forte (SNR 18 dB)
- **Direction accuracy:** 73.89% → 57.22% (**drop 16.67%**)
- **Joint accuracy:** 50.00% → 32.59% (**drop 17.41%**)
- **MAE angolare:** 30.25° → 54.08° (**aumento +23.83°**)

→ **Conclusione:** Pink noise HIGH è molto efficace nel degradare le predizioni del modello!

### Relazione Intensità-Drop

In generale, ci aspettiamo:

```
LOW → MEDIUM → HIGH
 ↓       ↓        ↓
piccolo  medio  grande drop
```

Se questo trend NON si verifica (es. LOW peggiore di HIGH), può indicare:
- Rumore troppo forte che "satura" e diventa riconoscibile
- Sample size piccolo → varianza alta
- Interazione complessa tra perturbazione e feature extraction

## 🔬 Uso in Tesi

I risultati di questo sweep forniscono:

1. **Tabelle quantitative** per la sezione sperimentale
2. **Confusion matrices** per analisi qualitativa (dove sbaglia il modello?)
3. **Ranking perturbazioni** per efficacia anti-cheat
4. **Trade-off** percezione-efficacia (confrontare con ascolti soggettivi)

### Prossimi Passi

Dopo aver eseguito lo sweep:

1. Analizza il CSV con pandas/Excel
2. Crea grafici: drop vs livello, per tipo perturbazione
3. Seleziona 2-3 confusion matrix più interessanti per la tesi
4. Scrivi sezione risultati commentando:
   - Quali perturbazioni funzionano meglio
   - Perché alcune sono inefficaci (feature invarianti)
   - Implicazioni per il design dell'anti-cheat

---

**Autore:** Francesco Carcangiu  
**Data:** Dicembre 2024

