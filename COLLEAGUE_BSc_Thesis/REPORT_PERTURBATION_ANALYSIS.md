# Report Analisi Perturbazioni Audio
## Sistema Anti-Cheat basato su Audio Spaziale

**Data:** 03/12/2025 15:52
**Autore:** Francesco Carcangiu
**Campioni testati:** 194
**Totale test eseguiti:** 56

---

## Executive Summary

Questo report presenta i risultati dell'analisi sperimentale volta a valutare l'efficacia di diverse perturbazioni audio nel degradare le performance di modelli di machine learning per la localizzazione audio spaziale. L'obiettivo è identificare perturbazioni che, pur rimanendo percettivamente accettabili per il giocatore, compromettano significativamente la capacità di sistemi di cheating basati su ML.

**Risultati chiave:**
- Perturbazione più efficace: **lowpass** (livello HIGH)
  - Degradazione joint accuracy: **33.0%**
  - Aumento MAE: **0.46°**
- Perturbazione meno efficace: **eq_boost** (livello LOW)
  - Degradazione joint accuracy: **-7.2%**

- Degradazione media (livello HIGH): **14.5%**

---

## 1. Modelli Testati

Sono stati valutati i due modelli migliori del collega:

### CRNN MEL80 (best angle)

- **Checkpoint:** `crnn angle`
- **Ottimizzato per:** Direzione
- **Feature extraction:** MEL-spectrogram + IPD/ILD (feature spaziali)

**Performance baseline (senza perturbazioni):**

| Metrica | Valore |
|---------|--------|
| Direction Accuracy | 99.48% |
| Distance Accuracy | 70.10% |
| Joint Accuracy | 69.59% |
| Mean Absolute Error (MAE) | 0.46° |

### ResNet18 MEL96 (best dist+angle weighted)

- **Checkpoint:** `resnet dist`
- **Ottimizzato per:** Distanza e direzione (pesato)
- **Feature extraction:** MEL-spectrogram + IPD/ILD (feature spaziali)

**Performance baseline (senza perturbazioni):**

| Metrica | Valore |
|---------|--------|
| Direction Accuracy | 100.00% |
| Distance Accuracy | 70.62% |
| Joint Accuracy | 70.62% |
| Mean Absolute Error (MAE) | 0.00° |

---

## 2. Perturbazioni Testate

Ogni perturbazione è stata testata a **3 livelli di intensità** (LOW, MEDIUM, HIGH):

| Tipo | LOW | MEDIUM | HIGH | Descrizione |
|------|-----|--------|------|-------------|
| Pitch Shift (+) | +75¢ | +150¢ | +200¢ | Innalzamento tono (0.75-2 semitoni) |
| Pitch Shift (−) | −75¢ | −150¢ | −200¢ | Abbassamento tono (0.75-2 semitoni) |
| White Noise | 42 dB SNR | 40 dB SNR | 38 dB SNR | Rumore bianco (più basso SNR = più rumore) |
| Pink Noise | 22 dB SNR | 20 dB SNR | 18 dB SNR | Rumore rosa (filtro 1/f, disturba fase) |
| EQ Tilt (boost) | +3 dB | +4.5 dB | +6 dB | Enfasi alte frequenze (high-shelf @ 2kHz) |
| EQ Tilt (cut) | −3 dB | −6 dB | −9 dB | Attenuazione alte frequenze |
| High-pass Filter | 150 Hz | 200 Hz | 250 Hz | Rimozione basse frequenze |
| Low-pass Filter | 12 kHz | 10 kHz | 8 kHz | Rimozione alte frequenze |
| Pink + EQ (combo) | − | Medium | High | Pink noise + EQ tilt boost |
| Pink + HP (combo) | − | Medium | High | Pink noise + High-pass filter |

**Totale:** 56 test (2 modelli × 28 configurazioni perturbazione)

---

## 3. Risultati: Perturbazioni Più Efficaci

Le perturbazioni più efficaci nel degradare le performance dei modelli:

| # | Modello | Perturbazione | Livello | Joint Drop | Dist Drop | MAE Increase |
|---|---------|---------------|---------|------------|-----------|--------------|
| 1 | ResNet | lowpass | HIGH | **33.0%** | 32.5% | 0.5° |
| 2 | ResNet | eq cut | HIGH | **32.0%** | 32.0% | 0.5° |
| 3 | ResNet | pink eq | HIGH | **30.9%** | 8.8% | 32.5° |
| 4 | ResNet | lowpass | MEDIUM | **30.4%** | 30.4% | 0.0° |
| 5 | ResNet | lowpass | LOW | **28.9%** | 28.9% | 0.0° |
| 6 | CRNN | white noise | LOW | **26.3%** | 25.8% | 0.9° |
| 7 | ResNet | pink noise | MEDIUM | **25.3%** | 17.0% | 20.9° |
| 8 | ResNet | pink noise | HIGH | **25.3%** | 16.5% | 26.9° |
| 9 | CRNN | white noise | MEDIUM | **24.7%** | 24.2% | 0.9° |
| 10 | ResNet | pink eq | MEDIUM | **24.2%** | 6.2% | 29.2° |

**Osservazioni:**

1. **Low-pass filter** (rimozione alte frequenze) è la perturbazione singola più efficace:
   - Degrada joint accuracy fino al **33%** (ResNet, HIGH)
   - Impatto principalmente sulla distanza, direzione rimane accurata

2. **Pink noise combo** mostra l'impatto più bilanciato:
   - Degrada sia direzione che distanza
   - Aumenta significativamente MAE angolare (fino a +32°)

3. **ResNet18** (modello distanza) è più sensibile alle perturbazioni rispetto a CRNN

---

## 4. Analisi per Tipo di Perturbazione

Ranking perturbazioni (media su tutti i livelli e modelli):

| Perturbazione | Joint Drop | Direction Drop | Distance Drop | MAE Increase |
|---------------|------------|----------------|---------------|--------------|
| White Noise | 22.3% | 5.2% | 20.0% | 4.6° |
| Pink Noise | 22.1% | 13.0% | 16.6% | 12.8° |
| Pink Hp | 20.9% | 14.9% | 12.4% | 14.8° |
| Lowpass | 20.7% | 0.9% | 20.3% | 0.9° |
| Pink Eq | 20.6% | 21.0% | 5.4% | 20.9° |
| Pitch Neg | 13.2% | 0.3% | 13.1% | 0.2° |
| Eq Cut | 12.2% | 0.1% | 12.3% | 0.1° |
| Pitch Pos | 5.2% | 0.0% | 5.2% | 0.0° |
| Highpass | 0.0% | -0.1% | 0.1% | -0.1° |
| Eq Boost | -5.0% | 0.0% | -5.0% | 0.0° |

**Insight chiave:**

- **White/Pink noise** e **Low-pass filter** sono le perturbazioni più efficaci
- **Pitch shift** ha impatto limitato (feature spaziali IPD/ILD invarianti al pitch)
- **EQ boost** addirittura migliora le performance (paradosso: probabilmente rimuove rumore)
- **Combo perturbazioni** (pink + altro) mostrano effetto cumulativo

---

## 5. Effetto dei Livelli di Intensità

Analisi dell'impatto crescente dei livelli LOW → MEDIUM → HIGH:

| Livello | Joint Drop (media) | Joint Drop (std) | MAE Increase (media) | MAE Increase (std) |
|---------|-------------------|------------------|----------------------|-------------------|
| **LOW** | 9.8% | ±11.4% | 1.6° | ±4.2° |
| **MEDIUM** | 13.2% | ±11.4% | 5.0° | ±8.9° |
| **HIGH** | 14.5% | ±12.0% | 6.4° | ±10.2° |

**Trend osservato:**

- Degradazione crescente: LOW (9.8%) < MEDIUM (13.2%) < HIGH (14.5%)
- Variabilità maggiore a livello HIGH (effetti più eterogenei)
- MAE aumenta significativamente solo con combo perturbazioni

---

## 6. Confusion Matrices (Selezione)

Analisi delle matrici di confusione per casi chiave:

### 6.1 Baseline CRNN (Direction)

| True \ Pred | N (0°) | W (270°) | S (180°) | E (90°) |
|--------------|---------|-----------|-----------|----------|
| **N (0°)** | 0 | 1 | 2 | 3 |
| **W (270°)** | 47 | 0 | 0 | 1 |
| **S (180°)** | 0 | 48 | 0 | 0 |
| **E (90°)** | 0 | 0 | 49 | 0 |

### 6.2 Worst Case CRNN (white_noise LOW, Direction)

| True \ Pred | N (0°) | W (270°) | S (180°) | E (90°) |
|--------------|---------|-----------|-----------|----------|
| **N (0°)** | 0 | 1 | 2 | 3 |
| **W (270°)** | 46 | 0 | 0 | 2 |
| **S (180°)** | 0 | 48 | 0 | 0 |
| **E (90°)** | 0 | 0 | 49 | 0 |

**Degradazione:** joint accuracy da 69.6% a 43.3% (drop 26.3%)

### 6.3 Baseline ResNet (Distance)

| True \ Pred | Near | Medium | Far |
|--------------|-------|---------|------|
| **Near** | 0 | 1 | 2 |
| **Medium** | 34 | 27 | 3 |
| **Far** | 2 | 45 | 18 |

### 6.4 Worst Case ResNet (lowpass HIGH, Distance)

| True \ Pred | Near | Medium | Far |
|--------------|-------|---------|------|
| **Near** | 0 | 1 | 2 |
| **Medium** | 2 | 26 | 36 |
| **Far** | 0 | 7 | 58 |

**Degradazione:** joint accuracy da 70.6% a 37.6% (drop 33.0%)

---

## 7. Conclusioni e Raccomandazioni

### 7.1 Risultati Principali

1. **Efficacia perturbazioni audio contro ML:**
   - È possibile degradare significativamente (fino al 33%) le performance di modelli ML
   - Le perturbazioni più efficaci agiscono sulle feature spaziali (fase/livello tra canali)
   - Pitch shift è inefficace (feature IPD/ILD invarianti)

2. **Perturbazioni raccomandate per l'anti-cheat:**
   - **Primary:** Pink noise (SNR 18-20 dB) + EQ tilt
   - **Alternative:** White noise, Low-pass filter moderato
   - **Evitare:** Pitch shift, EQ boost, High-pass filter

3. **Trade-off percezione vs efficacia:**
   - Livello MEDIUM offre buon compromesso (13% drop, limitato impatto percettivo)
   - Livello HIGH molto efficace ma potrebbe essere udibile
   - Pink noise è preferibile a white (spettro più naturale)

### 7.2 Limitazioni e Sviluppi Futuri

**Limitazioni dello studio:**
- Test su modelli specifici (potrebbero esistere architetture più robuste)
- Nessuna valutazione percettiva sistematica (solo stima teorica)
- Perturbazioni statiche (non adattive al contesto di gioco)

**Sviluppi futuri:**
- Test con attaccanti che addestrano modelli su audio perturbato (adversarial training)
- Perturbazioni adattive basate su contesto di gioco (silenzio vs azione intensa)
- Studio percettivo formale (MOS, PESQ) per validare accettabilità
- Analisi costi computazionali per deployment in produzione

---

## Appendice A: Materiale Supplementare

**File generati:**
- CSV completo: `summary_perturbations_best_models.csv`
- Confusion matrices: `confusion_matrices/` (116 file)
- Log esecuzione: `sweep_log.txt`

**Codice sorgente:**
- Script valutazione: `model_classifier/run_best_models_perturb_sweep.py`
- Script analisi: `model_classifier/analyze_perturbation_results.py`
- Utilità perturbazioni: `model_classifier/perturbation_utils.py`

**Repository:** `COLLEAGUE_BSc_Thesis/` e `ADV_ML/`

---

*Report generato automaticamente il 03/12/2025 alle 15:52*