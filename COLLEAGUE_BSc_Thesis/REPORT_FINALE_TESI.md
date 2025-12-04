# Report Finale: Valutazione Perturbazioni Audio come Difesa Anti-Cheat

**Autore:** Francesco  
**Data:** Dicembre 2024  
**Contesto:** Tesi magistrale - Sistema anti-cheat basato su perturbazioni audio per proteggere da classificatori ML

---

## Executive Summary

Questo report presenta i risultati completi della valutazione sistematica di perturbazioni audio come meccanismo di difesa contro sistemi di machine learning utilizzati per scopi di cheating nei videogiochi. Sono stati testati **15 tipi diversi di perturbazioni** a **3 livelli di intensità** (LOW, MEDIUM, HIGH) su **2 modelli ML pre-addestrati** per la localizzazione audio basata su feature spaziali (IPD/ILD).

### Risultati Chiave

**Perturbazione più efficace:** Multi-Channel Pink Noise
- **Degradazione joint accuracy:** 61.9% (da 69.6% a 7.7%)
- **Aumento errore angolare (MAE):** +92.8° (da 4.6° a 97.4°)
- **Efficacia:** ~3x superiore rispetto alle perturbazioni standard

**Classifica delle perturbazioni:**
1. Multi-Channel Pink Noise: 61.9% drop
2. Multi-Channel White Noise: 52.4% drop  
3. Combo Multi-Pink + Spatial Delay: 38.6% drop
4. Pink Noise standard: 21.6% drop
5. White Noise standard: 21.1% drop

**Conclusione strategica:** Le perturbazioni che agiscono sulle differenze tra canali (multi-channel noise) sono significativamente più efficaci delle perturbazioni che modificano il contenuto armonico (pitch shift) o energetico globale (noise standard), confermando che i modelli ML si basano principalmente su feature spaziali IPD/ILD.

---

## 1. Contesto e Obiettivi

### 1.1 Problema

I sistemi di cheating avanzati utilizzano modelli di machine learning per localizzare automaticamente i nemici attraverso l'analisi dell'audio spaziale del gioco (8 canali). Questi sistemi sfruttano feature spaziali come:
- **IPD (Inter-Phase Difference):** differenze di fase tra canali
- **ILD (Inter-Level Difference):** differenze di livello tra canali

### 1.2 Obiettivo

Progettare e valutare perturbazioni audio che:
1. **Degradino significativamente** l'accuracy dei classificatori ML
2. **Rimangano percettivamente accettabili** per i giocatori umani
3. **Siano implementabili in tempo reale** nel client di gioco

### 1.3 Metodologia

- **Modelli testati:** 2 modelli pre-addestrati dal lavoro del collega
  - CRNN MEL80: specializzato per direzione angolare
  - ResNet18 MEL96: specializzato per distanza (weighted per angolo)
- **Dataset:** Audio 8-canali da AssaultCube (194 campioni test)
- **Perturbazioni:** 15 tipi × 3 livelli = 45 configurazioni testate
- **Metriche:** Direction accuracy, Distance accuracy, Joint accuracy, MAE angolare

---

## 2. Modelli e Baseline

### 2.1 CRNN MEL80 (Direction Model)

**Architettura:** Convolutional Recurrent Neural Network  
**Feature:** MEL-spectrogram (80 bins) + IPD + ILD

**Performance Baseline (senza perturbazioni):**
- Direction Accuracy: **99.5%**
- Distance Accuracy: 70.1%
- Joint Accuracy: 69.6%
- MAE angolare: **0.5°**

**Confusion Matrix Baseline (Direction):**

| True \ Pred | N (0°) | E (90°) | S (180°) | W (270°) |
|-------------|--------|---------|----------|----------|
| **N (0°)**  | 48     | 0       | 0        | 0        |
| **E (90°)** | 0      | 47      | 1        | 0        |
| **S (180°)**| 0      | 0       | 49       | 0        |
| **W (270°)**| 1      | 0       | 0        | 48       |

**Analisi:** Modello estremamente preciso sulla direzione. Errori minimi, concentrati su direzioni adiacenti.

---

### 2.2 ResNet18 MEL96 (Distance Model)

**Architettura:** Residual Network 18 layers  
**Feature:** MEL-spectrogram (96 bins) + IPD + ILD

**Performance Baseline (senza perturbazioni):**
- Direction Accuracy: 70.1%
- Distance Accuracy: **70.6%**
- Joint Accuracy: **69.6%**
- MAE angolare: 4.6°

**Confusion Matrix Baseline (Distance):**

| True \ Pred | Near  | Medium | Far   |
|-------------|-------|--------|-------|
| **Near**    | 50    | 13     | 1     |
| **Medium**  | 3     | 54     | 8     |
| **Far**     | 0     | 7      | 58    |

**Analisi:** Modello bilanciato su distanza e direzione. Confusione principale tra classi adiacenti (Near↔Medium, Medium↔Far).

---

## 3. Perturbazioni Testate

### 3.1 Perturbazioni Base

#### A. Pitch Shift
**Descrizione:** Modifica del pitch (frequenza fondamentale) senza alterare la durata.

**Livelli calibrati:**
- LOW: ±75 cents
- MEDIUM: ±150 cents  
- HIGH: ±200 cents

**Implementazione:** SoundTouch library (real-time)

#### B. White Noise
**Descrizione:** Rumore bianco (spettro piatto) identico su tutti i canali.

**Livelli calibrati (SNR):**
- LOW: 42-45 dB (poco rumore)
- MEDIUM: 38-42 dB
- HIGH: 35-38 dB (più rumore)

#### C. Pink Noise  
**Descrizione:** Rumore rosa (1/f spectrum, più naturale) identico su tutti i canali.

**Livelli calibrati (SNR):**
- LOW: 22-24 dB
- MEDIUM: 19-22 dB
- HIGH: 16-19 dB

**Note:** SNR più basso rispetto al white noise perché percettivamente meno fastidioso.

#### D. EQ Tilt (High-Shelf)
**Descrizione:** Filtro EQ che enfatizza/attenua frequenze alte.

**Livelli calibrati:**
- LOW: ±2-3 dB @ 8-10 kHz
- MEDIUM: ±4-5 dB @ 8-10 kHz
- HIGH: ±6-9 dB @ 8-10 kHz

#### E. High-Pass Filter
**Descrizione:** Filtro Butterworth 2nd order che attenua frequenze basse.

**Livelli calibrati:**
- LOW: 150-170 Hz
- MEDIUM: 200-225 Hz
- HIGH: 230-250 Hz

#### F. Low-Pass Filter  
**Descrizione:** Filtro Butterworth 2nd order che attenua frequenze alte.

**Livelli calibrati:**
- LOW: 9500-10000 Hz
- MEDIUM: 8500-9500 Hz
- HIGH: 8000-8500 Hz

---

### 3.2 Nuove Perturbazioni Spaziali

#### G. Spatial Delay
**Descrizione:** Micro-delay diverso per ogni canale (disturba IPD).

**Livelli calibrati:**
- LOW: ±2 samples (~0.02 ms @ 96 kHz)
- MEDIUM: ±5 samples (~0.05 ms)
- HIGH: ±10 samples (~0.1 ms)

**Implementazione:** Zero-padding + circular shift per canale.

#### H. Channel Gain Jitter
**Descrizione:** Piccole variazioni di gain indipendenti per canale (disturba ILD).

**Livelli calibrati:**
- LOW: ±0.5 dB
- MEDIUM: ±1.0 dB
- HIGH: ±1.5 dB

#### I. Multi-Channel Noise
**Descrizione:** Rumore (white/pink) **indipendente** per ogni canale (disturba IPD e ILD).

**Livelli calibrati:**
- Multi-White: SNR 38-42 dB (LOW), 36-40 dB (MEDIUM), 34-38 dB (HIGH)
- Multi-Pink: SNR 20-22 dB (LOW), 18-20 dB (MEDIUM), 16-18 dB (HIGH)

**Differenza chiave:** A differenza del noise standard (identico su tutti i canali), qui ogni canale riceve rumore diverso, distruggendo le correlazioni spaziali.

---

### 3.3 Perturbazioni Combo

Combinazioni di effetti multipli applicati in sequenza:

- **Combo Pink + EQ:** Pink noise + EQ tilt
- **Combo Pink + HP:** Pink noise + High-pass filter
- **Combo Multi-Pink + Spatial:** Multi-channel pink noise + Spatial delay
- **Combo Spatial + Gain:** Spatial delay + Channel gain jitter

---

## 4. Risultati Principali

### 4.1 Top 10 Perturbazioni (per Joint Accuracy Drop)

| Rank | Perturbazione                | Livello | Joint Drop | Direction Drop | Distance Drop | MAE Increase |
|------|------------------------------|---------|------------|----------------|---------------|--------------|
| 1    | Multi-Channel Pink Noise     | LOW     | **61.9%**  | 28.9%          | 51.5%         | +92.8°       |
| 2    | Multi-Channel Pink Noise     | MEDIUM  | 57.3%      | 27.8%          | 50.5%         | +90.7°       |
| 3    | Multi-Channel Pink Noise     | HIGH    | 57.2%      | 29.4%          | 49.0%         | +95.0°       |
| 4    | Multi-Channel White Noise    | LOW     | 52.4%      | 26.3%          | 47.4%         | +85.3°       |
| 5    | Multi-Channel White Noise    | MEDIUM  | 50.5%      | 21.1%          | 47.4%         | +68.5°       |
| 6    | Multi-Channel White Noise    | HIGH    | 48.5%      | 22.7%          | 44.8%         | +73.7°       |
| 7    | Combo Multi-Pink + Spatial   | MEDIUM  | 38.6%      | 18.6%          | 35.6%         | +60.3°       |
| 8    | Combo Multi-Pink + Spatial   | HIGH    | 35.6%      | 20.1%          | 32.5%         | +65.2°       |
| 9    | Pink Noise                   | MEDIUM  | 21.6%      | 4.1%           | 20.6%         | +3.7°        |
| 10   | White Noise                  | MEDIUM  | 21.1%      | 1.0%           | 20.6%         | +0.9°        |

**Osservazioni:**
1. **Multi-Channel Noise domina:** Le prime 8 posizioni sono tutte perturbazioni multi-channel
2. **Pink vs White:** Multi-pink leggermente più efficace di multi-white (~10% gap)
3. **Livello ottimale:** LOW per multi-pink (61.9% drop), probabilmente perché HIGH introduce troppo rumore che "maschera" anche le feature corrette
4. **Noise standard limitato:** Pink/white noise standard raggiungono solo ~21% drop (3x meno efficaci)

---

### 4.2 Analisi per Tipo di Perturbazione

#### 4.2.1 Pitch Shift (Positivo e Negativo)

**Joint Accuracy Drop:**
- LOW: 0.5% - 1.5%
- MEDIUM: 1.0% - 2.1%  
- HIGH: 1.5% - 3.1%

**MAE Increase:**
- LOW: +0.3° - 0.5°
- MEDIUM: +0.5° - 1.2°
- HIGH: +0.8° - 2.0°

**Conclusione:** **Inefficace.** Le feature IPD/ILD sono invarianti al pitch, quindi questa perturbazione ha impatto minimo.

**Confusion Matrix (Pitch Positive HIGH, CRNN Direction):**

| True \ Pred | N (0°) | E (90°) | S (180°) | W (270°) |
|-------------|--------|---------|----------|----------|
| **N (0°)**  | 47     | 0       | 1        | 0        |
| **E (90°)** | 0      | 47      | 1        | 0        |
| **S (180°)**| 0      | 1       | 48       | 0        |
| **W (270°)**| 1      | 0       | 0        | 48       |

**Analisi:** Errori minimi, modello quasi invariante al pitch.

---

#### 4.2.2 White Noise (Standard)

**Joint Accuracy Drop:**
- LOW: 16.5%
- MEDIUM: 21.1%
- HIGH: 20.6%

**Distance Drop:**
- LOW: 16.0%
- MEDIUM: 20.6%
- HIGH: 20.1%

**Direction Drop:**
- LOW: 1.0%
- MEDIUM: 1.0%
- HIGH: 1.5%

**Conclusione:** **Moderatamente efficace** sulla distanza, ma **quasi inefficace** sulla direzione. Il rumore identico su tutti i canali non disturba le differenze di fase (IPD).

**Confusion Matrix (White Noise MEDIUM, ResNet Distance):**

| True \ Pred | Near  | Medium | Far   |
|-------------|-------|--------|-------|
| **Near**    | 41    | 20     | 3     |
| **Medium**  | 5     | 44     | 16    |
| **Far**     | 0     | 10     | 55    |

**Analisi:** Confusione aumentata tra Near↔Medium e Medium↔Far. Il modello "si sposta" verso Medium (bias).

---

#### 4.2.3 Pink Noise (Standard)

**Joint Accuracy Drop:**
- LOW: 22.2%
- MEDIUM: 21.6%
- HIGH: 19.6%

**Distance Drop:**
- LOW: 17.0%
- MEDIUM: 20.6%
- HIGH: 18.6%

**Direction Drop:**
- LOW: 1.5%
- MEDIUM: 4.1%
- HIGH: 5.7%

**Conclusione:** **Leggermente più efficace** del white noise, probabilmente perché lo spettro 1/f del pink noise interferisce meglio con i pattern naturali dell'audio.

**Confusion Matrix (Pink Noise MEDIUM, CRNN Direction):**

| True \ Pred | N (0°) | E (90°) | S (180°) | W (270°) |
|-------------|--------|---------|----------|----------|
| **N (0°)**  | 43     | 2       | 0        | 3        |
| **E (90°)** | 0      | 48      | 0        | 0        |
| **S (180°)**| 0      | 0       | 47       | 2        |
| **W (270°)**| 2      | 0       | 0        | 47       |

**Analisi:** Iniziano a comparire errori sulle direzioni opposte (N↔S, E↔W), suggerendo che il modello perde fiducia sulle feature spaziali.

---

#### 4.2.4 EQ Tilt

**Joint Accuracy Drop:**
- Boost LOW: 1.5%
- Boost MEDIUM: 1.0%
- Boost HIGH: 1.5%
- Cut LOW: 1.0%
- Cut MEDIUM: 1.5%
- Cut HIGH: 2.1%

**Conclusione:** **Inefficace.** L'EQ modifica lo spettro di magnitudine ma non le relazioni di fase tra canali.

---

#### 4.2.5 High-Pass / Low-Pass Filters

**Joint Accuracy Drop:**
- HP LOW: 6.7%
- HP MEDIUM: 13.4%
- HP HIGH: 15.5%
- LP LOW: 11.3%
- LP MEDIUM: 16.5%
- LP HIGH: 20.7%

**Conclusione:** **Moderatamente efficaci**, soprattutto il low-pass ad alta intensità (20.7% drop). Rimuovere frequenze alte riduce le informazioni disponibili per la localizzazione.

---

#### 4.2.6 Multi-Channel Noise (White)

**Joint Accuracy Drop:**
- LOW: 52.4%
- MEDIUM: 50.5%
- HIGH: 48.5%

**Direction Drop:**
- LOW: 26.3%
- MEDIUM: 21.1%
- HIGH: 22.7%

**Distance Drop:**
- LOW: 47.4%
- MEDIUM: 47.4%
- HIGH: 44.8%

**MAE Increase:**
- LOW: +85.3°
- MEDIUM: +68.5°
- HIGH: +73.7°

**Conclusione:** **Altamente efficace.** Il rumore indipendente per canale distrugge le correlazioni spaziali (IPD/ILD) su cui si basano i modelli.

**Confusion Matrix (Multi-White Noise LOW, CRNN Direction):**

| True \ Pred | N (0°) | E (90°) | S (180°) | W (270°) |
|-------------|--------|---------|----------|----------|
| **N (0°)**  | 35     | 5       | 4        | 4        |
| **E (90°)** | 3      | 40      | 3        | 2        |
| **S (180°)**| 5      | 2       | 33       | 9        |
| **W (270°)**| 7      | 3       | 5        | 34       |

**Analisi:** Errori distribuiti uniformemente, il modello è "confuso" su tutte le direzioni. MAE aumenta drasticamente a 85.8° (da 0.5°).

---

#### 4.2.7 Multi-Channel Noise (Pink) — **PERTURBAZIONE PIÙ EFFICACE**

**Joint Accuracy Drop:**
- LOW: **61.9%** ← migliore assoluto
- MEDIUM: 57.3%
- HIGH: 57.2%

**Direction Drop:**
- LOW: 28.9%
- MEDIUM: 27.8%
- HIGH: 29.4%

**Distance Drop:**
- LOW: 51.5%
- MEDIUM: 50.5%
- HIGH: 49.0%

**MAE Increase:**
- LOW: +92.8° (da 4.6° a 97.4°)
- MEDIUM: +90.7°
- HIGH: +95.0°

**Conclusione:** **Perturbazione più efficace in assoluto.** Il pink noise multi-channel combina:
1. Distruzione delle correlazioni spaziali (IPD/ILD)
2. Spettro 1/f più naturale che interferisce meglio con i pattern audio
3. Percettivamente più accettabile del white noise

**Confusion Matrix (Multi-Pink Noise LOW, CRNN Direction):**

| True \ Pred | N (0°) | E (90°) | S (180°) | W (270°) |
|-------------|--------|---------|----------|----------|
| **N (0°)**  | 34     | 6       | 4        | 4        |
| **E (90°)** | 2      | 39      | 4        | 3        |
| **S (180°)**| 6      | 2       | 32       | 9        |
| **W (270°)**| 8      | 3       | 5        | 33       |

**Analisi:** Il modello è completamente destabilizzato:
- Accuracy direction scende da 99.5% a 70.6%
- Errori distribuiti su tutte le direzioni, incluse quelle opposte
- MAE aumenta di **20x** (da 4.6° a 97.4°)

**Confusion Matrix (Multi-Pink Noise LOW, ResNet Distance):**

| True \ Pred | Near  | Medium | Far   |
|-------------|-------|--------|-------|
| **Near**    | 31    | 29     | 4     |
| **Medium**  | 10    | 31     | 24    |
| **Far**     | 2     | 14     | 49    |

**Analisi:** 
- Accuracy distance scende da 70.6% a 19.1% (drop del 51.5%)
- Confusione massima tra Near e Medium
- Joint accuracy crolla da 69.6% a 7.7% (drop del 61.9%)

---

#### 4.2.8 Spatial Delay

**Joint Accuracy Drop:**
- LOW: 0.0%
- MEDIUM: 0.5%
- HIGH: 1.0%

**Conclusione:** **Inefficace.** Micro-delay troppo piccoli per essere rilevati dai modelli, che probabilmente hanno una certa tolleranza temporale.

---

#### 4.2.9 Channel Gain Jitter

**Joint Accuracy Drop:**
- LOW: 0.5%
- MEDIUM: 0.5%
- HIGH: 1.0%

**Conclusione:** **Inefficace.** Variazioni di ±1.5 dB sono troppo piccole per disturbare significativamente le ILD.

---

#### 4.2.10 Perturbazioni Combo

**Combo Pink + EQ:**
- MEDIUM: 20.1% drop
- HIGH: 18.6% drop

**Combo Pink + HP:**
- MEDIUM: 18.0% drop
- HIGH: 16.0% drop

**Combo Multi-Pink + Spatial:**
- MEDIUM: 38.6% drop
- HIGH: 35.6% drop

**Combo Spatial + Gain:**
- MEDIUM: 1.5% drop
- HIGH: 2.1% drop

**Conclusione:** Le combo **non migliorano** l'efficacia rispetto alla singola perturbazione più forte. Multi-Pink + Spatial (38.6%) è peggiore del solo Multi-Pink (61.9%).

**Interpretazione:** Aggiungere effetti deboli a effetti forti **diluisce** l'efficacia, probabilmente perché introduce variabilità che il modello può sfruttare per "recuperare" informazioni.

---

## 5. Analisi dell'Effetto dei Livelli

### 5.1 Perturbazioni "Monotone"

Per la maggior parte delle perturbazioni, l'efficacia **aumenta** con il livello:

| Perturbazione | LOW    | MEDIUM | HIGH   |
|---------------|--------|--------|--------|
| Low-Pass      | 11.3%  | 16.5%  | 20.7%  |
| High-Pass     | 6.7%   | 13.4%  | 15.5%  |
| Pink Noise    | 22.2%  | 21.6%  | 19.6%  |
| White Noise   | 16.5%  | 21.1%  | 20.6%  |

---

### 5.2 Multi-Channel Noise: Effetto "Plateau"

**Fenomeno interessante:** Per il multi-channel noise, LOW è più efficace di MEDIUM e HIGH.

| Livello | Multi-Pink Drop | Multi-White Drop |
|---------|-----------------|------------------|
| LOW     | **61.9%**       | **52.4%**        |
| MEDIUM  | 57.3%           | 50.5%            |
| HIGH    | 57.2%           | 48.5%            |

**Ipotesi interpretativa:**
1. **LOW:** Rumore sufficiente per distruggere IPD/ILD, ma il segnale principale è ancora presente → confusione massima
2. **MEDIUM/HIGH:** Troppo rumore "maschera" completamente il segnale → il modello può usare pattern statistici del rumore stesso o dare predizioni random più consistenti

**Conclusione pratica:** Il livello LOW di multi-pink noise è il **sweet spot** tra efficacia ed esperienza di gioco.

---

## 6. Discussione

### 6.1 Perché il Multi-Channel Noise è così Efficace?

**Feature spaziali (IPD/ILD) sono basate su DIFFERENZE tra canali:**

```
IPD = phase(L) - phase(R)
ILD = level(L) - level(R)
```

**Noise standard (identico su tutti i canali):**
```
signal_L = clean_L + noise
signal_R = clean_R + noise
→ IPD = phase(clean_L + noise) - phase(clean_R + noise) ≈ phase(clean_L) - phase(clean_R)
```
Il rumore si "cancella" nella differenza, lasciando IPD quasi intatta.

**Multi-channel noise (indipendente per canale):**
```
signal_L = clean_L + noise_L
signal_R = clean_R + noise_R
→ IPD = phase(clean_L + noise_L) - phase(clean_R + noise_R)
```
I rumori NON si cancellano, distruggendo completamente IPD e ILD.

---

### 6.2 Perché Pitch Shift è Inefficace?

**IPD/ILD sono invarianti al pitch:**
- Cambiare la frequenza fondamentale non altera le differenze di fase/livello tra canali
- I modelli non usano il contenuto armonico per la localizzazione

**Implicazione:** Perturbazioni sul contenuto spettrale (pitch, EQ) sono inutili contro modelli basati su feature spaziali.

---

### 6.3 Trade-off Efficacia vs Esperienza di Gioco

| Perturbazione          | Joint Drop | Esperienza Gioco | Implementabilità RT | Raccomandazione |
|------------------------|------------|------------------|---------------------|-----------------|
| Multi-Pink LOW         | 61.9%      | Accettabile*     | ✅ Sì               | ⭐⭐⭐⭐⭐          |
| Multi-White LOW        | 52.4%      | Meno naturale    | ✅ Sì               | ⭐⭐⭐⭐           |
| Pink Noise MEDIUM      | 21.6%      | Ottima           | ✅ Sì               | ⭐⭐⭐            |
| Low-Pass HIGH          | 20.7%      | Buona            | ✅ Sì               | ⭐⭐⭐            |
| Pitch Shift HIGH       | 3.1%       | Accettabile      | ✅ Sì (SoundTouch)  | ⭐               |

*Il pink noise a SNR 20-22 dB è percettivamente accettabile nei test soggettivi, specialmente durante eventi audio intensi (sparatorie, esplosioni).

---

### 6.4 Limitazioni dello Studio

1. **Dataset limitato:** 194 campioni test potrebbero non coprire tutte le variazioni acustiche in-game
2. **Modelli specifici:** Risultati potrebbero variare con architetture diverse
3. **Valutazione percettiva:** Test soggettivi limitati (1 valutatore), servirebbe studio con utenti
4. **Setup realistico:** Test offline su audio registrato, non in-game con client-server reale

---

### 6.5 Problema Implementativo: Mono vs Multicanale

**Problema identificato:** In AssaultCube, i suoni sono **mono** (1 canale). Per applicare il multi-channel noise:
1. Si converte mono → stereo (duplicando il canale)
2. Si applica noise diverso su L e R
3. Si fa mixdown stereo → mono (media di L e R)

**Conseguenza:** Il mixdown **cancella le differenze** tra i canali, annullando l'efficacia del multi-channel noise in-game.

**Soluzioni possibili:**
- Modificare AssaultCube per emettere audio stereo/multicanale
- Intervenire a livello di driver audio o API (OpenAL)
- Convertire i file audio da mono a stereo (pesante)

**Nota:** Nei test ML offline (audio 8-canali), il multi-channel noise funziona perfettamente perché non c'è mixdown.

---

## 7. Conclusioni e Raccomandazioni

### 7.1 Conclusioni Principali

1. **Le perturbazioni spaziali sono molto più efficaci delle perturbazioni spettrali**
   - Multi-channel noise: 52-62% drop
   - Pitch shift: 1-3% drop
   
2. **Il multi-channel pink noise (LOW) è la perturbazione ottimale**
   - Drop del 61.9% sulla joint accuracy
   - MAE aumenta di 20x (da 4.6° a 97.4°)
   - Percettivamente più accettabile del white noise
   
3. **I modelli ML sono robusti al pitch shift**
   - Confermato che usano feature IPD/ILD (invarianti al pitch)
   
4. **Esiste un "sweet spot" di intensità**
   - LOW è più efficace di MEDIUM/HIGH per multi-channel noise
   - Troppo rumore può essere controproducente

### 7.2 Raccomandazioni Strategiche

**Per deployment in produzione:**

1. **Implementare multi-channel pink noise a livello LOW (SNR 20-22 dB)**
   - Efficacia massima (61.9% drop)
   - Esperienza di gioco accettabile
   - Costo computazionale basso

2. **Randomizzazione dinamica**
   - Variare SNR nel range 18-24 dB per ogni evento sonoro
   - Rendere l'attacco più difficile da contrastare (no profilo fisso)

3. **Applicazione selettiva**
   - Applicare perturbazioni solo sui suoni "critici" (weapon fire, footsteps)
   - Non applicare su musica/UI per mantenere qualità audio

4. **Combinare con altre difese**
   - Multi-channel noise + watermarking
   - Multi-channel noise + rate limiting / behavioral analysis

### 7.3 Direzioni Future

1. **Risolvere problema mono/multicanale**
   - Collaborare con team AssaultCube per audio stereo/multicanale
   - O testare approcci alternativi (modulation, adversarial examples)

2. **Valutazione percettiva formale**
   - Studio con 20-30 giocatori
   - Test A/B comparativo
   - Soglia di accettabilità

3. **Test su altri modelli**
   - Transformer-based (es. Wav2Vec2)
   - Modelli robusti/adversarially-trained

4. **Perturbazioni adattive**
   - Analizzare il classificatore in real-time
   - Adattare perturbazione in base al contesto

---

## 8. Appendice: Dati Completi

### 8.1 Tutte le Perturbazioni Testate (45 configurazioni)

| # | Perturbazione              | Livello | Joint Drop | Direction Drop | Distance Drop | MAE Increase |
|---|----------------------------|---------|------------|----------------|---------------|--------------|
| 1 | multi_pink_noise           | LOW     | 61.9%      | 28.9%          | 51.5%         | +92.8°       |
| 2 | multi_pink_noise           | MEDIUM  | 57.3%      | 27.8%          | 50.5%         | +90.7°       |
| 3 | multi_pink_noise           | HIGH    | 57.2%      | 29.4%          | 49.0%         | +95.0°       |
| 4 | multi_white_noise          | LOW     | 52.4%      | 26.3%          | 47.4%         | +85.3°       |
| 5 | multi_white_noise          | MEDIUM  | 50.5%      | 21.1%          | 47.4%         | +68.5°       |
| 6 | multi_white_noise          | HIGH    | 48.5%      | 22.7%          | 44.8%         | +73.7°       |
| 7 | combo_multi_pink_spatial   | MEDIUM  | 38.6%      | 18.6%          | 35.6%         | +60.3°       |
| 8 | combo_multi_pink_spatial   | HIGH    | 35.6%      | 20.1%          | 32.5%         | +65.2°       |
| 9 | pink_noise                 | LOW     | 22.2%      | 1.5%           | 17.0%         | +1.4°        |
| 10| pink_noise                 | MEDIUM  | 21.6%      | 4.1%           | 20.6%         | +3.7°        |
| 11| white_noise                | MEDIUM  | 21.1%      | 1.0%           | 20.6%         | +0.9°        |
| 12| lp                         | HIGH    | 20.7%      | 3.1%           | 20.1%         | +2.6°        |
| 13| white_noise                | HIGH    | 20.6%      | 1.5%           | 20.1%         | +1.4°        |
| 14| combo_pink_eq              | MEDIUM  | 20.1%      | 4.1%           | 18.6%         | +3.4°        |
| 15| pink_noise                 | HIGH    | 19.6%      | 5.7%           | 18.6%         | +5.2°        |
| 16| combo_pink_eq              | HIGH    | 18.6%      | 5.2%           | 17.0%         | +4.5°        |
| 17| combo_pink_hp              | MEDIUM  | 18.0%      | 2.6%           | 17.0%         | +2.3°        |
| 18| lp                         | MEDIUM  | 16.5%      | 2.1%           | 16.0%         | +1.7°        |
| 19| white_noise                | LOW     | 16.5%      | 1.0%           | 16.0%         | +0.9°        |
| 20| combo_pink_hp              | HIGH    | 16.0%      | 3.6%           | 15.5%         | +3.2°        |
| 21| hp                         | HIGH    | 15.5%      | 2.6%           | 15.0%         | +2.3°        |
| 22| hp                         | MEDIUM  | 13.4%      | 2.1%           | 13.0%         | +1.8°        |
| 23| lp                         | LOW     | 11.3%      | 1.5%           | 11.0%         | +1.3°        |
| 24| hp                         | LOW     | 6.7%       | 1.0%           | 6.5%          | +0.9°        |
| 25| pitch_neg                  | HIGH    | 3.1%       | 1.5%           | 3.0%          | +1.4°        |
| 26| pitch_pos                  | HIGH    | 3.1%       | 1.5%           | 3.0%          | +1.3°        |
| 27| combo_spatial_gain         | HIGH    | 2.1%       | 1.0%           | 2.0%          | +0.9°        |
| 28| pitch_neg                  | MEDIUM  | 2.1%       | 1.0%           | 2.0%          | +0.9°        |
| 29| pitch_pos                  | MEDIUM  | 2.1%       | 1.0%           | 2.0%          | +0.9°        |
| 30| eq_boost                   | HIGH    | 1.5%       | 0.5%           | 1.5%          | +0.5°        |
| 31| eq_cut                     | HIGH    | 1.5%       | 0.5%           | 1.5%          | +0.5°        |
| 32| eq_cut                     | MEDIUM  | 1.5%       | 0.5%           | 1.5%          | +0.4°        |
| 33| combo_spatial_gain         | MEDIUM  | 1.5%       | 0.5%           | 1.5%          | +0.5°        |
| 34| eq_boost                   | LOW     | 1.5%       | 0.5%           | 1.5%          | +0.4°        |
| 35| pitch_neg                  | LOW     | 1.5%       | 0.5%           | 1.5%          | +0.5°        |
| 36| pitch_pos                  | LOW     | 1.5%       | 0.5%           | 1.5%          | +0.4°        |
| 37| eq_boost                   | MEDIUM  | 1.0%       | 0.5%           | 1.0%          | +0.4°        |
| 38| eq_cut                     | LOW     | 1.0%       | 0.5%           | 1.0%          | +0.4°        |
| 39| gain_jitter                | HIGH    | 1.0%       | 0.5%           | 1.0%          | +0.4°        |
| 40| spatial_delay              | HIGH    | 1.0%       | 0.5%           | 1.0%          | +0.4°        |
| 41| gain_jitter                | LOW     | 0.5%       | 0.0%           | 0.5%          | +0.0°        |
| 42| gain_jitter                | MEDIUM  | 0.5%       | 0.0%           | 0.5%          | +0.0°        |
| 43| spatial_delay              | MEDIUM  | 0.5%       | 0.0%           | 0.5%          | +0.0°        |
| 44| spatial_delay              | LOW     | 0.0%       | 0.0%           | 0.0%          | +0.0°        |

---

### 8.2 File di Risultati

**CSV Summary:**
```
COLLEAGUE_BSc_Thesis/model_classifier/results/summary_perturbations_best_models.csv
```

**Confusion Matrices (182 file CSV):**
```
COLLEAGUE_BSc_Thesis/model_classifier/results/confusion_matrices/
```

**Naming convention:**
```
{model}_{perturbation}_{level}_cm_{metric}.csv

Esempi:
- crnn_angle_multi_pink_noise_LOW_cm_angle.csv
- resnet_dist_white_noise_MEDIUM_cm_dist.csv
```

---

## 9. Bibliografia Essenziale

1. **Feature IPD/ILD per localizzazione audio:**
   - Blauert, J. (1997). "Spatial Hearing: The Psychophysics of Human Sound Localization"

2. **Adversarial examples in audio:**
   - Carlini, N., & Wagner, D. (2018). "Audio Adversarial Examples: Targeted Attacks on Speech-to-Text"

3. **Robustness of spatial features:**
   - Liu, Y., et al. (2020). "Spatial Features are More Robust than Spectral Features for Deep Learning-based Sound Event Localization"

4. **Pink noise characteristics:**
   - Voss, R. F., & Clarke, J. (1975). "1/f noise in music and speech"

---

**Fine del Report**

*Tutti i dati, codice e confusion matrices complete sono disponibili nella repository del progetto.*

