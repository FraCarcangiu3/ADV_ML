# 🎧 Guida all'Ascolto per i Professori

Questa cartella contiene esempi audio per dimostrare le perturbazioni applicate agli spari della pistola.

---

## 📁 Struttura Cartelle

```
demo_audio_for_professors/
├── 00_ORIGINALI/          ← Audio originali (riferimento)
├── 01_PITCH/              ← Modifica frequenza (più acuto/grave)
├── 02_WHITE_NOISE/        ← Rumore bianco aggiunto
├── 03_PINK_NOISE/         ← Rumore rosa aggiunto
├── 04_EQ_TILT/            ← Equalizzazione (più brillante/scuro)
├── 05_HIGHPASS/           ← Rimuove frequenze basse
├── 06_LOWPASS/            ← Rimuove frequenze alte
└── README.md              ← Questa guida
```

---

## 🎯 Come Ascoltare (Ordine Consigliato)

### 1️⃣ Inizia con l'Originale
Apri la cartella **`00_ORIGINALI/`** e ascolta uno degli audio:
- `audio_event_006a41c6..._ORIGINALE.wav`
- Questo è lo sparo originale senza modifiche

### 2️⃣ Confronta con le Modifiche

#### **Pitch Shift** (`01_PITCH/`)
Modifica la frequenza (più acuto o più grave):
- **P1_light (+100 cents)**: Leggermente più acuto
- **P2_medium (+150 cents)**: Moderatamente più acuto  
- **P3_strong (+200 cents)**: Molto più acuto
- **P_neg_light (-100 cents)**: Leggermente più grave
- **P_neg_medium (-150 cents)**: Moderatamente più grave
- **P_neg_strong (-200 cents)**: Molto più grave

**Cosa senti:** Lo sparo suona più acuto (come un fischio) o più grave (come un tuono)

#### **White Noise** (`02_WHITE_NOISE/`)
Aggiunge rumore bianco (come statico TV):
- **W1_light (SNR 38 dB)**: Rumore leggero
- **W2_medium (SNR 40 dB)**: Rumore medio
- **W3_strong (SNR 42 dB)**: Rumore forte

**Cosa senti:** Lo sparo è "sporco" con rumore di fondo

#### **Pink Noise** (`03_PINK_NOISE/`)
Aggiunge rumore rosa (più naturale del bianco):
- **K1_light (SNR 18 dB)**: Rumore leggero
- **K2_strong (SNR 22 dB)**: Rumore forte

**Cosa senti:** Rumore più naturale, più naturale rispetto al white noise

#### **EQ Tilt** (`04_EQ_TILT/`)
Modifica il timbro (più brillante o più scuro):
- **boost_light (+3 dB)**: Leggermente più brillante
- **boost_medium (+4.5 dB)**: Moderatamente più brillante
- **boost_strong (+6 dB)**: Molto più brillante
- **cut_light (-3 dB)**: Leggermente più scuro
- **cut_medium (-4.5 dB)**: Moderatamente più scuro
- **cut_strong (-6 dB)**: Molto più scuro

**Cosa senti:** Lo sparo è più "tagliente" (boost) o più "ovattato" (cut)

#### **High-Pass Filter** (`05_HIGHPASS/`)
Rimuove frequenze basse:
- **HP_150Hz**: Rimuove suoni sotto 150 Hz
- **HP_200Hz**: Rimuove suoni sotto 200 Hz
- **HP_250Hz**: Rimuove suoni sotto 250 Hz

**Cosa senti:** Lo sparo perde "corpo", suona più sottile

#### **Low-Pass Filter** (`06_LOWPASS/`)
Rimuove frequenze alte:
- **LP_8000Hz**: Rimuove suoni sopra 8000 Hz
- **LP_10000Hz**: Rimuove suoni sopra 10000 Hz
- **LP_12000Hz**: Rimuove suoni sopra 12000 Hz

**Cosa senti:** Lo sparo perde "chiarezza", suona più ovattato

---

## 📊 Esempio di Confronto

Per ogni audio originale, ci sono **24 versioni modificate**:

1. **6 versioni Pitch** (3 acuto + 3 grave)
2. **3 versioni White Noise** (light/medium/strong)
3. **2 versioni Pink Noise** (light/strong)
4. **6 versioni EQ** (3 boost + 3 cut)
5. **3 versioni High-Pass**
6. **3 versioni Low-Pass**
7. **1 originale** (riferimento)

**Totale:** 5 audio × 25 file = **125 file audio**

---

## ⚠️ Nota Importante

### Rumore Solo sul Segnale

I rumori (white/pink noise) vengono applicati **SOLO durante lo sparo**, non sul silenzio.

Questo significa:
- ✅ Il silenzio prima/dopo lo sparo rimane pulito
- ✅ Il rumore appare solo quando c'è il suono dello sparo
- ✅ Questo simula il comportamento reale del gioco

**Perché?** Nel gioco reale, il rumore viene aggiunto solo quando viene riprodotto il suono della pistola, non durante il silenzio ambientale.

---

## 🎮 Contesto del Progetto

Questi audio sono stati registrati durante il gameplay di AssaultCube:
- **Formato originale:** FLAC multi-canale (8 canali)
- **Durata:** ~1.9 secondi per audio
- **Contenuto:** Suono dello sparo della pistola

Le perturbazioni simulate sono quelle che verranno applicate nel gioco per:
- **Proteggere** il modello ML da riconoscimento audio
- **Mantenere** la qualità del suono accettabile per i giocatori
- **Testare** la robustezza del sistema di riconoscimento

---

## 📝 Formato File

- **Formato:** WAV (compatibile con tutti i player)
- **Sample Rate:** 96 kHz (alta qualità)
- **Canali:** 8 (multi-canale)
- **Durata:** ~1.9 secondi per file

---

## 🔍 Come Usare con i Professori

1. **Apri la cartella** `demo_audio_for_professors/`
2. **Inizia con `00_ORIGINALI/`** - Fai ascoltare l'originale
3. **Poi confronta** - Apri una cartella (es. `01_PITCH/`) e fai ascoltare le varianti
4. **Spiega** - Ogni nome file contiene i parametri usati
5. **Mostra la differenza** - Confronta originale vs modificato

---

## 💡 Suggerimenti

- **Usa un player audio** che supporta multi-canale (VLC, Audacity)
- **Ascolta con cuffie** per sentire meglio le differenze
- **Confronta sempre** con l'originale per capire l'effetto
- **Inizia dai livelli "light"** e poi passa ai "strong"

---

**Buon ascolto! 🎧**

