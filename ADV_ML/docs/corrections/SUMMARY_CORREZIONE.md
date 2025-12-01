# 📋 Riassunto Correzione: Rumore Solo sul Segnale

**Data:** 23 Novembre 2024  
**Problema risolto:** Rumore applicato anche al silenzio ❌ → Rumore solo sul segnale ✅

---

## 🎯 Cosa è Stato Modificato

### Problema Originale
Il rumore (white/pink noise) veniva aggiunto a **tutti i sample**, incluso il silenzio.  
Questo NON riflette il comportamento reale del gioco.

### Soluzione Implementata
Ora il rumore viene applicato **SOLO dove c'è segnale** (non sul silenzio).

---

## ✅ File Modificati

1. **`ADV_ML/audio_effects.py`**
   - ✅ `add_white_noise()` - Aggiunto parametro `only_on_signal=True`
   - ✅ `add_pink_noise()` - Aggiunto parametro `only_on_signal=True`

2. **`ADV_ML/offline_perturb.py`**
   - ✅ Tutte le chiamate ora usano `only_on_signal=True`
   - ✅ Output verboso aggiornato

3. **`ADV_ML/test_audio_pipeline.py`**
   - ✅ Test aggiornati per verificare nuovo comportamento

4. **`ADV_ML/README_OFFLINE_PERTURB.md`**
   - ✅ Documentazione aggiornata

---

## 📊 Risultati Prima vs Dopo

### PRIMA (❌ Non Corretto)
```
Media Percentuale Zeri:
  Originale:    77.38%
  White Noise:  0.00%    ❌ Riempie anche il silenzio
  Pink Noise:   0.00%    ❌ Riempie anche il silenzio
```

### DOPO (✅ Corretto)
```
Media Percentuale Zeri:
  Originale:    77.38%
  White Noise:  77.38%   ✅ Mantiene i silenzi!
  Pink Noise:   77.38%   ✅ Mantiene i silenzi!
```

---

## 🚀 Cosa Devi Fare Ora

### 1. ⚠️ Rigenera i CSV con Rumore

I CSV vecchi hanno rumore anche sul silenzio. Devono essere rigenerati:

```bash
# Elimina i vecchi (opzionale)
rm ADV_ML/output/pistol_noiseW_*.csv
rm ADV_ML/output/pistol_noiseK_*.csv

# Rigenera con la correzione
cd "/Users/francesco03/Documents/GitHub/AssaultCube Server"

# W1 - White Noise Light
ADV_ML/venv/bin/python3 ADV_ML/offline_perturb.py \
  --dataset-root COLLEAGUE_BSc_Thesis/Data/audio/audio_loopback_flac \
  --perturbation white_noise \
  --mode random \
  --min-snr 35 \
  --max-snr 38 \
  --num-samples 50 \
  --output-csv ADV_ML/output/pistol_noiseW_W1_light.csv \
  --verbose

# W2 - White Noise Medium
ADV_ML/venv/bin/python3 ADV_ML/offline_perturb.py \
  --dataset-root COLLEAGUE_BSc_Thesis/Data/audio/audio_loopback_flac \
  --perturbation white_noise \
  --mode random \
  --min-snr 38 \
  --max-snr 42 \
  --num-samples 50 \
  --output-csv ADV_ML/output/pistol_noiseW_W2_medium.csv \
  --verbose

# W3 - White Noise Strong
ADV_ML/venv/bin/python3 ADV_ML/offline_perturb.py \
  --dataset-root COLLEAGUE_BSc_Thesis/Data/audio/audio_loopback_flac \
  --perturbation white_noise \
  --mode random \
  --min-snr 42 \
  --max-snr 45 \
  --num-samples 50 \
  --output-csv ADV_ML/output/pistol_noiseW_W3_strong.csv \
  --verbose

# K1 - Pink Noise Light
ADV_ML/venv/bin/python3 ADV_ML/offline_perturb.py \
  --dataset-root COLLEAGUE_BSc_Thesis/Data/audio/audio_loopback_flac \
  --perturbation pink_noise \
  --mode random \
  --min-snr 16 \
  --max-snr 20 \
  --num-samples 50 \
  --output-csv ADV_ML/output/pistol_noiseK_K1_light.csv \
  --verbose

# K2 - Pink Noise Strong
ADV_ML/venv/bin/python3 ADV_ML/offline_perturb.py \
  --dataset-root COLLEAGUE_BSc_Thesis/Data/audio/audio_loopback_flac \
  --perturbation pink_noise \
  --mode random \
  --min-snr 20 \
  --max-snr 24 \
  --num-samples 50 \
  --output-csv ADV_ML/output/pistol_noiseK_K2_strong.csv \
  --verbose
```

### 2. ✅ I CSV Pitch Sono OK

I file pitch **NON** devono essere rigenerati:
- ✅ `pistol_pitch_P1_light.csv`
- ✅ `pistol_pitch_P2_medium.csv`
- ✅ `pistol_pitch_P3_strong.csv`

Il pitch shift mantiene già correttamente i silenzi!

---

## 📝 Come Verificare

### Test Rapido su 1 File

```bash
# Testa white noise su 1 file
ADV_ML/venv/bin/python3 ADV_ML/offline_perturb.py \
  --dataset-root COLLEAGUE_BSc_Thesis/Data/audio/audio_loopback_flac \
  --perturbation white_noise \
  --mode fixed \
  --snr-db 40 \
  --num-samples 1 \
  --output-csv ADV_ML/output/test_white_1sample.csv \
  --verbose
```

**Output atteso:**
```
...
White noise: SNR=40.0 dB (solo su segnale)
...
```

Se vedi "(solo su segnale)" nel messaggio, la correzione è attiva! ✅

### Test Completo

```bash
# Esegui test pipeline completo
ADV_ML/venv/bin/python3 ADV_ML/test_audio_pipeline.py
```

Dovresti vedere:
```
Media Percentuale Zeri:
  White Noise:  77.38%   ✅ Mantiene i silenzi!
  Pink Noise:   77.38%   ✅ Mantiene i silenzi!
```

---

## 📚 Documentazione

1. **`ADV_ML/CORREZIONE_RUMORE_SOLO_SEGNALE.md`**  
   → Spiegazione tecnica dettagliata

2. **`ADV_ML/README_OFFLINE_PERTURB.md`**  
   → Guida all'uso (aggiornata)

3. **`ADV_ML/RISPOSTA_ZERI_CSV.md`**  
   → Spiegazione del problema originale (ancora valida per pitch)

---

## ❓ FAQ

### Q: Perché l'SNR misurato è più alto del target?

**A:** È normale! Con `only_on_signal=True`:
- SNR **locale** (sul segnale): ~40 dB ✅
- SNR **globale** (incluso silenzio): ~46 dB ✅

Il silenzio senza rumore contribuisce a un SNR globale più alto.

### Q: Devo rigenerare TUTTI i CSV?

**A:** Solo quelli con rumore:
- ❌ Da rigenerare: `pistol_noiseW_*.csv` e `pistol_noiseK_*.csv`
- ✅ OK come sono: `pistol_pitch_*.csv`

### Q: Come so se un CSV è vecchio o nuovo?

**A:** Controlla la percentuale di zeri:
```python
import numpy as np
data = np.loadtxt("file.csv", delimiter=",", max_rows=100)
zeros = (data == 0).sum() / data.size * 100
print(f"Zeri: {zeros:.1f}%")
```

- Se ~0%: CSV vecchio (da rigenerare) ❌
- Se ~75-78%: CSV nuovo (corretto) ✅

### Q: Posso usare only_on_signal=False?

**A:** Sì, ma NON è realistico. Usa solo per test/debug:
```python
from audio_effects import add_white_noise

# Rumore anche sul silenzio (non realistico)
audio_noisy = add_white_noise(audio, snr_db=40, only_on_signal=False)
```

---

## ✅ Checklist Finale

Prima di procedere con i test ML, verifica:

- [ ] Ho rigenerato tutti i CSV `pistol_noiseW_*.csv`
- [ ] Ho rigenerato tutti i CSV `pistol_noiseK_*.csv`
- [ ] I nuovi CSV hanno ~75-78% di zeri (come originale)
- [ ] Ho eseguito `test_audio_pipeline.py` per verificare
- [ ] Ho letto `CORREZIONE_RUMORE_SOLO_SEGNALE.md`

---

**Correzione completata e testata! 🎉**

Ora i dati riflettono correttamente il comportamento reale del gioco!

