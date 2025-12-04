# Report Completo: Confusion Matrices per Rumori Base
Questo report include le confusion matrices per tutti i rumori base (pink_noise, white_noise, pitch, eq, hp, lp) a tutti i livelli (LOW, MEDIUM, HIGH).

---

## PINK NOISE

### Livello: LOW

#### CRNN (Direction)

### Direction - pink_noise LOW

| True \ Pred | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| **0** | 46 | 0 | 0 | 2 |
| **1** | 0 | 48 | 0 | 0 |
| **2** | 0 | 0 | 48 | 1 |
| **3** | 1 | 0 | 0 | 48 |

**Metriche:**
- Direction Accuracy: 99.5% → 97.9% (drop: 1.5%)
- MAE: 0.5° → 1.9° (+1.4°)

#### ResNet (Distance)

### Distance - pink_noise LOW

| True \ Pred | 0 | 1 | 2 |
|---|---|---|---|
| **0** | 17 | 36 | 11 |
| **1** | 1 | 30 | 34 |
| **2** | 0 | 8 | 57 |

**Metriche:**
- Distance Accuracy: 70.6% → 53.6% (drop: 17.0%)
- Joint Accuracy: 70.6% → 48.5% (drop: 22.2%)

---

### Livello: MEDIUM

#### CRNN (Direction)

### Direction - pink_noise MEDIUM

| True \ Pred | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| **0** | 43 | 2 | 0 | 3 |
| **1** | 0 | 48 | 0 | 0 |
| **2** | 0 | 0 | 47 | 2 |
| **3** | 2 | 0 | 0 | 47 |

**Metriche:**
- Direction Accuracy: 99.5% → 95.4% (drop: 4.1%)
- MAE: 0.5° → 4.2° (+3.7°)

#### ResNet (Distance)

### Distance - pink_noise MEDIUM

| True \ Pred | 0 | 1 | 2 |
|---|---|---|---|
| **0** | 21 | 32 | 11 |
| **1** | 1 | 28 | 36 |
| **2** | 0 | 10 | 55 |

**Metriche:**
- Distance Accuracy: 70.6% → 53.6% (drop: 17.0%)
- Joint Accuracy: 70.6% → 45.9% (drop: 24.7%)

---

### Livello: HIGH

#### CRNN (Direction)

### Direction - pink_noise HIGH

| True \ Pred | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| **0** | 39 | 4 | 0 | 5 |
| **1** | 0 | 48 | 0 | 0 |
| **2** | 0 | 0 | 42 | 7 |
| **3** | 1 | 0 | 0 | 48 |

**Metriche:**
- Direction Accuracy: 99.5% → 91.2% (drop: 8.2%)
- MAE: 0.5° → 7.9° (+7.4°)

#### ResNet (Distance)

### Distance - pink_noise HIGH

| True \ Pred | 0 | 1 | 2 |
|---|---|---|---|
| **0** | 26 | 29 | 9 |
| **1** | 1 | 28 | 36 |
| **2** | 0 | 8 | 57 |

**Metriche:**
- Distance Accuracy: 70.6% → 57.2% (drop: 13.4%)
- Joint Accuracy: 70.6% → 47.4% (drop: 23.2%)

---


## WHITE NOISE

### Livello: LOW

#### CRNN (Direction)

### Direction - white_noise LOW

| True \ Pred | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| **0** | 46 | 0 | 0 | 2 |
| **1** | 0 | 48 | 0 | 0 |
| **2** | 0 | 0 | 49 | 0 |
| **3** | 1 | 0 | 0 | 48 |

**Metriche:**
- Direction Accuracy: 99.5% → 98.5% (drop: 1.0%)
- MAE: 0.5° → 1.4° (+0.9°)

#### ResNet (Distance)

### Distance - white_noise LOW

| True \ Pred | 0 | 1 | 2 |
|---|---|---|---|
| **0** | 19 | 31 | 14 |
| **1** | 0 | 33 | 32 |
| **2** | 0 | 7 | 58 |

**Metriche:**
- Distance Accuracy: 70.6% → 56.7% (drop: 13.9%)
- Joint Accuracy: 70.6% → 53.6% (drop: 17.0%)

---

### Livello: MEDIUM

#### CRNN (Direction)

### Direction - white_noise MEDIUM

| True \ Pred | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| **0** | 46 | 0 | 0 | 2 |
| **1** | 0 | 48 | 0 | 0 |
| **2** | 0 | 0 | 49 | 0 |
| **3** | 1 | 0 | 0 | 48 |

**Metriche:**
- Direction Accuracy: 99.5% → 98.5% (drop: 1.0%)
- MAE: 0.5° → 1.4° (+0.9°)

#### ResNet (Distance)

### Distance - white_noise MEDIUM

| True \ Pred | 0 | 1 | 2 |
|---|---|---|---|
| **0** | 19 | 32 | 13 |
| **1** | 1 | 31 | 33 |
| **2** | 0 | 7 | 58 |

**Metriche:**
- Distance Accuracy: 70.6% → 55.7% (drop: 14.9%)
- Joint Accuracy: 70.6% → 51.5% (drop: 19.1%)

---

### Livello: HIGH

#### CRNN (Direction)

### Direction - white_noise HIGH

| True \ Pred | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| **0** | 46 | 0 | 0 | 2 |
| **1** | 0 | 48 | 0 | 0 |
| **2** | 0 | 0 | 49 | 0 |
| **3** | 1 | 0 | 0 | 48 |

**Metriche:**
- Direction Accuracy: 99.5% → 98.5% (drop: 1.0%)
- MAE: 0.5° → 1.4° (+0.9°)

#### ResNet (Distance)

### Distance - white_noise HIGH

| True \ Pred | 0 | 1 | 2 |
|---|---|---|---|
| **0** | 22 | 31 | 11 |
| **1** | 1 | 31 | 33 |
| **2** | 0 | 10 | 55 |

**Metriche:**
- Distance Accuracy: 70.6% → 55.7% (drop: 14.9%)
- Joint Accuracy: 70.6% → 50.0% (drop: 20.6%)

---


## PITCH POS

### Livello: LOW

#### CRNN (Direction)

### Direction - pitch_pos LOW

| True \ Pred | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| **0** | 47 | 0 | 0 | 1 |
| **1** | 0 | 48 | 0 | 0 |
| **2** | 0 | 0 | 49 | 0 |
| **3** | 0 | 0 | 0 | 49 |

**Metriche:**
- Direction Accuracy: 99.5% → 99.5% (drop: 0.0%)
- MAE: 0.5° → 0.5° (+0.0°)

#### ResNet (Distance)

### Distance - pitch_pos LOW

| True \ Pred | 0 | 1 | 2 |
|---|---|---|---|
| **0** | 24 | 36 | 4 |
| **1** | 1 | 36 | 28 |
| **2** | 0 | 2 | 63 |

**Metriche:**
- Distance Accuracy: 70.6% → 63.4% (drop: 7.2%)
- Joint Accuracy: 70.6% → 62.9% (drop: 7.7%)

---

### Livello: MEDIUM

#### CRNN (Direction)

### Direction - pitch_pos MEDIUM

| True \ Pred | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| **0** | 48 | 0 | 0 | 0 |
| **1** | 0 | 48 | 0 | 0 |
| **2** | 0 | 0 | 49 | 0 |
| **3** | 0 | 0 | 0 | 49 |

**Metriche:**
- Direction Accuracy: 99.5% → 100.0% (drop: -0.5%)
- MAE: 0.5° → 0.0° (+-0.5°)

#### ResNet (Distance)

### Distance - pitch_pos MEDIUM

| True \ Pred | 0 | 1 | 2 |
|---|---|---|---|
| **0** | 22 | 37 | 5 |
| **1** | 1 | 33 | 31 |
| **2** | 0 | 2 | 63 |

**Metriche:**
- Distance Accuracy: 70.6% → 60.8% (drop: 9.8%)
- Joint Accuracy: 70.6% → 60.8% (drop: 9.8%)

---

### Livello: HIGH

#### CRNN (Direction)

### Direction - pitch_pos HIGH

| True \ Pred | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| **0** | 47 | 0 | 0 | 1 |
| **1** | 0 | 48 | 0 | 0 |
| **2** | 0 | 0 | 49 | 0 |
| **3** | 0 | 0 | 0 | 49 |

**Metriche:**
- Direction Accuracy: 99.5% → 99.5% (drop: 0.0%)
- MAE: 0.5° → 0.5° (+0.0°)

#### ResNet (Distance)

### Distance - pitch_pos HIGH

| True \ Pred | 0 | 1 | 2 |
|---|---|---|---|
| **0** | 23 | 34 | 7 |
| **1** | 1 | 35 | 29 |
| **2** | 0 | 3 | 62 |

**Metriche:**
- Distance Accuracy: 70.6% → 61.9% (drop: 8.8%)
- Joint Accuracy: 70.6% → 61.9% (drop: 8.8%)

---


## PITCH NEG

### Livello: LOW

#### CRNN (Direction)

### Direction - pitch_neg LOW

| True \ Pred | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| **0** | 47 | 0 | 0 | 1 |
| **1** | 0 | 48 | 0 | 0 |
| **2** | 0 | 0 | 49 | 0 |
| **3** | 0 | 0 | 0 | 49 |

**Metriche:**
- Direction Accuracy: 99.5% → 99.5% (drop: 0.0%)
- MAE: 0.5° → 0.5° (+0.0°)

#### ResNet (Distance)

### Distance - pitch_neg LOW

| True \ Pred | 0 | 1 | 2 |
|---|---|---|---|
| **0** | 20 | 35 | 9 |
| **1** | 1 | 24 | 40 |
| **2** | 0 | 2 | 63 |

**Metriche:**
- Distance Accuracy: 70.6% → 55.2% (drop: 15.5%)
- Joint Accuracy: 70.6% → 54.6% (drop: 16.0%)

---

### Livello: MEDIUM

#### CRNN (Direction)

### Direction - pitch_neg MEDIUM

| True \ Pred | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| **0** | 47 | 0 | 0 | 1 |
| **1** | 0 | 48 | 0 | 0 |
| **2** | 0 | 0 | 49 | 0 |
| **3** | 1 | 0 | 0 | 48 |

**Metriche:**
- Direction Accuracy: 99.5% → 99.0% (drop: 0.5%)
- MAE: 0.5° → 0.9° (+0.5°)

#### ResNet (Distance)

### Distance - pitch_neg MEDIUM

| True \ Pred | 0 | 1 | 2 |
|---|---|---|---|
| **0** | 11 | 41 | 12 |
| **1** | 0 | 20 | 45 |
| **2** | 0 | 1 | 64 |

**Metriche:**
- Distance Accuracy: 70.6% → 49.0% (drop: 21.6%)
- Joint Accuracy: 70.6% → 49.0% (drop: 21.6%)

---

### Livello: HIGH

#### CRNN (Direction)

### Direction - pitch_neg HIGH

| True \ Pred | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| **0** | 46 | 0 | 0 | 2 |
| **1** | 0 | 48 | 0 | 0 |
| **2** | 0 | 0 | 49 | 0 |
| **3** | 0 | 0 | 0 | 49 |

**Metriche:**
- Direction Accuracy: 99.5% → 99.0% (drop: 0.5%)
- MAE: 0.5° → 0.9° (+0.5°)

#### ResNet (Distance)

### Distance - pitch_neg HIGH

| True \ Pred | 0 | 1 | 2 |
|---|---|---|---|
| **0** | 7 | 39 | 18 |
| **1** | 0 | 19 | 46 |
| **2** | 0 | 0 | 65 |

**Metriche:**
- Distance Accuracy: 70.6% → 46.9% (drop: 23.7%)
- Joint Accuracy: 70.6% → 46.9% (drop: 23.7%)

---


## EQ BOOST

### Livello: LOW

#### CRNN (Direction)

### Direction - eq_boost LOW

| True \ Pred | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| **0** | 47 | 0 | 0 | 1 |
| **1** | 0 | 48 | 0 | 0 |
| **2** | 0 | 0 | 49 | 0 |
| **3** | 0 | 0 | 0 | 49 |

**Metriche:**
- Direction Accuracy: 99.5% → 99.5% (drop: 0.0%)
- MAE: 0.5° → 0.5° (+0.0°)

#### ResNet (Distance)

### Distance - eq_boost LOW

| True \ Pred | 0 | 1 | 2 |
|---|---|---|---|
| **0** | 49 | 14 | 1 |
| **1** | 2 | 53 | 10 |
| **2** | 0 | 16 | 49 |

**Metriche:**
- Distance Accuracy: 70.6% → 77.8% (drop: -7.2%)
- Joint Accuracy: 70.6% → 77.8% (drop: -7.2%)

---

### Livello: MEDIUM

#### CRNN (Direction)

### Direction - eq_boost MEDIUM

| True \ Pred | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| **0** | 47 | 0 | 0 | 1 |
| **1** | 0 | 48 | 0 | 0 |
| **2** | 0 | 0 | 49 | 0 |
| **3** | 0 | 0 | 0 | 49 |

**Metriche:**
- Direction Accuracy: 99.5% → 99.5% (drop: 0.0%)
- MAE: 0.5° → 0.5° (+0.0°)

#### ResNet (Distance)

### Distance - eq_boost MEDIUM

| True \ Pred | 0 | 1 | 2 |
|---|---|---|---|
| **0** | 55 | 8 | 1 |
| **1** | 5 | 51 | 9 |
| **2** | 2 | 19 | 44 |

**Metriche:**
- Distance Accuracy: 70.6% → 77.3% (drop: -6.7%)
- Joint Accuracy: 70.6% → 77.3% (drop: -6.7%)

---

### Livello: HIGH

#### CRNN (Direction)

### Direction - eq_boost HIGH

| True \ Pred | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| **0** | 47 | 0 | 0 | 1 |
| **1** | 0 | 48 | 0 | 0 |
| **2** | 0 | 0 | 49 | 0 |
| **3** | 0 | 0 | 0 | 49 |

**Metriche:**
- Direction Accuracy: 99.5% → 99.5% (drop: 0.0%)
- MAE: 0.5° → 0.5° (+0.0°)

#### ResNet (Distance)

### Distance - eq_boost HIGH

| True \ Pred | 0 | 1 | 2 |
|---|---|---|---|
| **0** | 58 | 5 | 1 |
| **1** | 12 | 46 | 7 |
| **2** | 3 | 22 | 40 |

**Metriche:**
- Distance Accuracy: 70.6% → 74.2% (drop: -3.6%)
- Joint Accuracy: 70.6% → 74.2% (drop: -3.6%)

---


## EQ CUT

### Livello: LOW

#### CRNN (Direction)

### Direction - eq_cut LOW

| True \ Pred | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| **0** | 48 | 0 | 0 | 0 |
| **1** | 0 | 48 | 0 | 0 |
| **2** | 0 | 0 | 49 | 0 |
| **3** | 0 | 0 | 0 | 49 |

**Metriche:**
- Direction Accuracy: 99.5% → 100.0% (drop: -0.5%)
- MAE: 0.5° → 0.0° (+-0.5°)

#### ResNet (Distance)

### Distance - eq_cut LOW

| True \ Pred | 0 | 1 | 2 |
|---|---|---|---|
| **0** | 23 | 34 | 7 |
| **1** | 1 | 32 | 32 |
| **2** | 0 | 1 | 64 |

**Metriche:**
- Distance Accuracy: 70.6% → 61.3% (drop: 9.3%)
- Joint Accuracy: 70.6% → 61.3% (drop: 9.3%)

---

### Livello: MEDIUM

#### CRNN (Direction)

### Direction - eq_cut MEDIUM

| True \ Pred | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| **0** | 48 | 0 | 0 | 0 |
| **1** | 0 | 48 | 0 | 0 |
| **2** | 0 | 0 | 49 | 0 |
| **3** | 1 | 0 | 0 | 48 |

**Metriche:**
- Direction Accuracy: 99.5% → 99.5% (drop: 0.0%)
- MAE: 0.5° → 0.5° (+0.0°)

#### ResNet (Distance)

### Distance - eq_cut MEDIUM

| True \ Pred | 0 | 1 | 2 |
|---|---|---|---|
| **0** | 10 | 37 | 17 |
| **1** | 0 | 18 | 47 |
| **2** | 0 | 0 | 65 |

**Metriche:**
- Distance Accuracy: 70.6% → 47.9% (drop: 22.7%)
- Joint Accuracy: 70.6% → 47.9% (drop: 22.7%)

---

### Livello: HIGH

#### CRNN (Direction)

### Direction - eq_cut HIGH

| True \ Pred | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| **0** | 48 | 0 | 0 | 0 |
| **1** | 0 | 48 | 0 | 0 |
| **2** | 0 | 0 | 49 | 0 |
| **3** | 2 | 0 | 0 | 47 |

**Metriche:**
- Direction Accuracy: 99.5% → 99.0% (drop: 0.5%)
- MAE: 0.5° → 0.9° (+0.5°)

#### ResNet (Distance)

### Distance - eq_cut HIGH

| True \ Pred | 0 | 1 | 2 |
|---|---|---|---|
| **0** | 3 | 33 | 28 |
| **1** | 0 | 7 | 58 |
| **2** | 0 | 0 | 65 |

**Metriche:**
- Distance Accuracy: 70.6% → 38.7% (drop: 32.0%)
- Joint Accuracy: 70.6% → 38.7% (drop: 32.0%)

---


## HP

### Livello: LOW

#### CRNN (Direction)

### Direction - hp LOW

*Matrice non disponibile*

#### ResNet (Distance)

### Distance - hp LOW

*Matrice non disponibile*

---

### Livello: MEDIUM

#### CRNN (Direction)

### Direction - hp MEDIUM

*Matrice non disponibile*

#### ResNet (Distance)

### Distance - hp MEDIUM

*Matrice non disponibile*

---

### Livello: HIGH

#### CRNN (Direction)

### Direction - hp HIGH

*Matrice non disponibile*

#### ResNet (Distance)

### Distance - hp HIGH

*Matrice non disponibile*

---


## LP

### Livello: LOW

#### CRNN (Direction)

### Direction - lp LOW

*Matrice non disponibile*

#### ResNet (Distance)

### Distance - lp LOW

*Matrice non disponibile*

---

### Livello: MEDIUM

#### CRNN (Direction)

### Direction - lp MEDIUM

*Matrice non disponibile*

#### ResNet (Distance)

### Distance - lp MEDIUM

*Matrice non disponibile*

---

### Livello: HIGH

#### CRNN (Direction)

### Direction - lp HIGH

*Matrice non disponibile*

#### ResNet (Distance)

### Distance - lp HIGH

*Matrice non disponibile*

---


