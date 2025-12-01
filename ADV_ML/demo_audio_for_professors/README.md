# 🎵 Esempi Audio per Professori

Questa cartella contiene esempi di audio originali e modificati per dimostrare le perturbazioni applicate.

## 📁 Struttura Cartelle

- **00_ORIGINALI/** - Audio FLAC originali convertiti in WAV
- **01_PITCH/** - Pitch shift (modifica frequenza)
- **02_WHITE_NOISE/** - Rumore bianco aggiunto
- **03_PINK_NOISE/** - Rumore rosa aggiunto
- **04_EQ_TILT/** - Equalizzazione (boost/cut)
- **05_HIGHPASS/** - Filtro passa-alto
- **06_LOWPASS/** - Filtro passa-basso

## 🎯 Come Ascoltare

1. **Inizia con 00_ORIGINALI/** - Ascolta l'audio originale
2. **Poi confronta con le modifiche** - Ogni cartella contiene vari livelli
3. **Nomi file** - Contengono i parametri usati (es. `+150cents`, `SNR40dB`)

## 📊 Livelli di Perturbazione

### Pitch Shift
- **P1_light**: ±100 cents (leggero)
- **P2_medium**: ±150 cents (medio)
- **P3_strong**: ±200 cents (forte)
- **P_neg_***: Pitch negativo (più grave)

### White Noise
- **W1_light**: SNR 38 dB (rumore leggero)
- **W2_medium**: SNR 40 dB (rumore medio)
- **W3_strong**: SNR 42 dB (rumore forte)

### Pink Noise
- **K1_light**: SNR 18 dB (rumore leggero)
- **K2_strong**: SNR 22 dB (rumore forte)

### EQ Tilt
- **boost_***: Aumenta frequenze alte (più brillante)
- **cut_***: Riduce frequenze alte (più scuro)

### Filtri
- **High-Pass**: Rimuove frequenze basse
- **Low-Pass**: Rimuove frequenze alte

## ⚠️ Nota Importante

Il rumore (white/pink noise) viene applicato **SOLO durante lo sparo**, non sul silenzio.
Questo simula il comportamento reale del gioco.

## 📝 Formato

Tutti i file sono in formato WAV a 96 kHz per compatibilità con tutti i player audio.

---
Generato automaticamente con `generate_demo_audio.py`
