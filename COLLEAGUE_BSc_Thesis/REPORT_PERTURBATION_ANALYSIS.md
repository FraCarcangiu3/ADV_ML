# Report Analisi Perturbazioni Audio
## Sistema Anti-Cheat basato su Audio Spaziale

**Data:** 03/12/2025 18:13
**Autore:** Francesco Carcangiu
**Campioni testati:** 194
**Totale test eseguiti:** 88

---

## Executive Summary

Questo report presenta i risultati dell'analisi sperimentale volta a valutare l'efficacia di diverse perturbazioni audio nel degradare le performance di modelli di machine learning per la localizzazione audio spaziale. L'obiettivo è identificare perturbazioni che, pur rimanendo percettivamente accettabili per il giocatore, compromettano significativamente la capacità di sistemi di cheating basati su ML.

**Risultati chiave:**
- Perturbazione più efficace: **multi_pink_noise** (livello LOW)
  - Degradazione joint accuracy: **61.9%**
  - Aumento MAE: **92.78°**
- Perturbazione meno efficace: **eq_boost** (livello LOW)
  - Degradazione joint accuracy: **-7.2%**

- Degradazione media (livello HIGH): **19.9%**

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
| 1 | CRNN | multi pink noise | LOW | **61.9%** | 36.6% | 92.8° |
| 2 | CRNN | multi pink noise | MEDIUM | **61.9%** | 36.6% | 92.8° |
| 3 | CRNN | multi pink noise | HIGH | **61.9%** | 36.6% | 93.2° |
| 4 | CRNN | multi pink spatial | MEDIUM | **61.9%** | 36.6% | 92.8° |
| 5 | CRNN | multi pink spatial | HIGH | **61.9%** | 36.6% | 93.2° |
| 6 | ResNet | multi pink noise | HIGH | **61.9%** | 37.1% | 72.4° |
| 7 | ResNet | multi pink spatial | MEDIUM | **61.9%** | 36.6% | 71.9° |
| 8 | ResNet | multi pink spatial | HIGH | **61.9%** | 37.1% | 74.2° |
| 9 | ResNet | multi pink noise | MEDIUM | **60.8%** | 36.6% | 71.4° |
| 10 | ResNet | multi pink noise | LOW | **59.3%** | 36.6% | 66.8° |

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
| Multi Pink Spatial | 61.9% | 73.6% | 36.7% | 83.0° |
| Multi Pink Noise | 61.3% | 72.6% | 36.7% | 81.6° |
| Multi White Noise | 52.4% | 47.0% | 36.9% | 53.3° |
| White Noise | 21.7% | 5.4% | 19.3% | 4.9° |
| Pink Noise | 21.6% | 13.1% | 16.1% | 12.8° |
| Lowpass | 20.7% | 0.9% | 20.3% | 0.9° |
| Pink Hp | 20.5% | 15.2% | 12.4% | 15.2° |
| Pink Eq | 19.5% | 20.2% | 5.3% | 20.3° |
| Pitch Neg | 13.2% | 0.3% | 13.1% | 0.2° |
| Eq Cut | 12.2% | 0.1% | 12.3% | 0.1° |
| Pitch Pos | 5.2% | 0.0% | 5.2% | 0.0° |
| Spatial Delay | 0.1% | 0.0% | 0.1% | 0.0° |
| Highpass | 0.0% | -0.1% | 0.1% | -0.1° |
| Gain Jitter | -0.3% | 0.1% | -0.3% | 0.1° |
| Spatial Gain | -0.5% | 0.1% | -0.6% | 0.1° |
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
| **LOW** | 15.7% | ±21.1% | 12.0° | ±26.5° |
| **MEDIUM** | 19.0% | ±22.0% | 16.7° | ±29.6° |
| **HIGH** | 19.9% | ±21.9% | 17.9° | ±29.9° |

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

### 6.2 Worst Case CRNN (multi_pink_noise LOW, Direction)

| True \ Pred | N (0°) | W (270°) | S (180°) | E (90°) |
|--------------|---------|-----------|-----------|----------|
| **N (0°)** | 0 | 1 | 2 | 3 |
| **W (270°)** | 0 | 45 | 3 | 0 |
| **S (180°)** | 0 | 45 | 3 | 0 |
| **E (90°)** | 0 | 49 | 0 | 0 |

**Degradazione:** joint accuracy da 69.6% a 7.7% (drop 61.9%)

### 6.3 Baseline ResNet (Distance)

| True \ Pred | Near | Medium | Far |
|--------------|-------|---------|------|
| **Near** | 0 | 1 | 2 |
| **Medium** | 34 | 27 | 3 |
| **Far** | 2 | 45 | 18 |

### 6.4 Worst Case ResNet (multi_pink_noise HIGH, Distance)

| True \ Pred | Near | Medium | Far |
|--------------|-------|---------|------|
| **Near** | 0 | 1 | 2 |
| **Medium** | 0 | 0 | 64 |
| **Far** | 0 | 1 | 64 |

**Degradazione:** joint accuracy da 70.6% a 8.8% (drop 61.9%)

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

*Report generato automaticamente il 03/12/2025 alle 18:13*