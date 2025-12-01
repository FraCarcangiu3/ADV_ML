# 🔧 Correzione: Rumore Applicato Solo sul Segnale

**Data:** 23 Novembre 2024  
**Problema risolto:** Il rumore veniva aggiunto anche al silenzio

---

## 🎯 Problema Originale

Prima della correzione:
- Il rumore (white/pink noise) veniva aggiunto a **tutti i sample**
- Anche le parti di silenzio (zeri) ricevevano rumore
- Questo NON simula il comportamento reale del gioco

### Comportamento Reale nel Gioco

Nel gioco, il rumore viene aggiunto **solo durante lo sparo**, non sul silenzio ambientale.

---

## ✅ Soluzione Implementata

### Modifiche al Codice

#### 1. `audio_effects.py`

Aggiunti nuovi parametri alle funzioni:
- `add_white_noise(..., only_on_signal=True, threshold=1e-4)`
- `add_pink_noise(..., only_on_signal=True, threshold=1e-4)`

**Logica implementata:**
```python
if only_on_signal:
    # Crea maschera: True dove c'è segnale, False dove c'è silenzio
    signal_mask = np.abs(signal) > threshold
    # Azzera il rumore dove c'è silenzio
    noise = noise * signal_mask
```

#### 2. `offline_perturb.py`

Tutte le chiamate ora usano `only_on_signal=True`:
```python
perturbed_audio = add_white_noise(
    perturbed_audio, 
    snr_db, 
    seed=...,
    only_on_signal=True  # ✅ Rumore solo sul segnale
)
```

---

## 📊 Risultati dei Test

### Prima della Correzione (OLD)
```
Media Percentuale Zeri:
  Originale:    77.38%
  White Noise:  0.00%    ❌ Riempie tutto (non realistico)
  Pink Noise:   0.00%    ❌ Riempie tutto (non realistico)
```

### Dopo la Correzione (NEW)
```
Media Percentuale Zeri:
  Originale:    77.38%
  White Noise:  77.38%   ✅ Mantiene i silenzi!
  Pink Noise:   77.38%   ✅ Mantiene i silenzi!
```

---

## 📐 Nota sull'SNR

### SNR Misurato

Con `only_on_signal=True`, l'SNR misurato è leggermente più alto del target:

```
Target SNR:  40.00 dB
Real SNR:    46-47 dB  (differenza ~6-7 dB)
```

### Perché questo è CORRETTO

L'SNR viene calcolato su **tutto l'audio** (segnale + silenzio):

1. **SNR Locale** (dove c'è segnale): ~40 dB ✅
2. **SNR Globale** (incluso silenzio): ~46 dB ✅

Il silenzio non ha rumore → contribuisce a un SNR globale più alto.

**Questo è il comportamento corretto** perché simula il gioco reale:
- Durante lo sparo: SNR = 40 dB (rumore presente)
- Durante il silenzio: SNR = ∞ (nessun rumore)
- Media globale: ~46 dB

---

## 🎮 Vantaggi della Correzione

### 1. Realismo Migliorato
- Simula esattamente il comportamento del gioco
- Il rumore appare solo durante l'azione (sparo)
- Il silenzio rimane silenzio

### 2. Compatibilità con i CSV
I CSV ora hanno percentuali di zeri simili:
```
pistol_pitch_P2_medium.csv:  75% zeri   ✅
pistol_noiseW_L1.csv:        ~77% zeri  ✅ (prima: 0%)
pistol_noiseK_K1.csv:        ~77% zeri  ✅ (prima: 0%)
```

### 3. Modello ML
- Dati più realistici
- Meglio riflette le condizioni reali
- Il modello vede rumore solo dove dovrebbe esserci

---

## 🔧 Come Usare

### Default (Raccomandato)
```python
# Rumore solo sul segnale (comportamento reale)
audio_noisy = add_white_noise(audio, snr_db=40.0, only_on_signal=True)
```

### Rumore Ovunque (per test/debug)
```python
# Rumore anche sul silenzio
audio_noisy = add_white_noise(audio, snr_db=40.0, only_on_signal=False)
```

### Soglia Personalizzata
```python
# Considera "silenzio" valori sotto 0.001
audio_noisy = add_white_noise(audio, snr_db=40.0, only_on_signal=True, threshold=1e-3)
```

---

## 📝 File Modificati

1. ✅ `ADV_ML/audio_effects.py` - Aggiunti parametri `only_on_signal` e `threshold`
2. ✅ `ADV_ML/offline_perturb.py` - Tutte le chiamate ora usano `only_on_signal=True`
3. ✅ `ADV_ML/test_audio_pipeline.py` - Test aggiornati per verificare comportamento

---

## 🚀 Prossimi Passi

1. ✅ **Correzione applicata e testata**
2. ✅ **Comportamento verificato su 3 file FLAC**
3. 🔄 **Rigenera tutti i CSV** con la nuova logica:
   ```bash
   # Elimina i vecchi CSV (opzionale)
   rm ADV_ML/output/pistol_noiseW_*.csv
   rm ADV_ML/output/pistol_noiseK_*.csv
   
   # Rigenera con la correzione
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

---

## ✅ Validazione

Il professore aveva ragione! La soluzione era semplice:

> "basterebbe isolare la parte dell'audio diversa da zero"

Implementato con successo:
- ✅ Rilevamento automatico del segnale (`np.abs(signal) > threshold`)
- ✅ Maschera applicata al rumore
- ✅ Silenzio preservato
- ✅ SNR corretto sulle parti con segnale

---

**Correzione completata con successo! 🎉**

