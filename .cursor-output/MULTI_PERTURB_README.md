# Multi-Perturbation Audio Obfuscation System

**Autore:** Francesco Carcangiu  
**Data:** 30 Ottobre 2025  
**Status:** Implementazione Step 2 (configurabile, non-random)

---

## 📋 Panoramica

Il sistema multi-perturbazione estende l'obfuscation audio da singolo effetto (pitch shift) a una **catena modulare di 8 effetti** applicabili indipendentemente o in combinazione. Ogni effetto è configurabile per suono tramite file YAML, con override via CLI/ENV.

**Obiettivo Step 2**: Configurazione deterministica (nessuna randomizzazione). Ogni effetto usa il **midpoint** del range specificato.

---

## 🎛️ Effetti Disponibili

### 1. Pitch Shift
- **Descrizione**: Altera la frequenza fondamentale senza cambiare durata
- **Parametri**: `min_abs_cents`, `max_abs_cents` (range assoluto)
- **Comportamento**: Usa midpoint `(min_abs + max_abs) / 2` con segno `+`
- **Range tipici**:
  - Weapon/auto: 75–200 cents
  - Footsteps: 100–200 cents
  - Voicecom: 50–100 cents

### 2. EQ Tilt
- **Descrizione**: Filtro shelving lineare da low a high freq
- **Parametri**: `min_db`, `max_db` (pendenza in dB)
- **Implementazione**: FFT con curva lineare o filtro IIR shelving
- **Range tipici**: -3 a +6 dB

### 3. HP/LP Filters
- **Descrizione**: Passa-alto e passa-basso morbidi
- **Parametri**: `hp_hz` (cutoff high-pass), `lp_hz` (cutoff low-pass)
- **Implementazione**: Filtri biquad 2° ordine, Q = 0.707 (Butterworth)
- **Range tipici**: HP 80–100 Hz, LP 13000–14000 Hz

### 4. Comb/Notch Filter
- **Descrizione**: Filtro IIR con picchi/valli spettrali
- **Parametri**: `depth_db`, `f0_hz` (freq fondamentale), `q` (selettività)
- **Uso**: Crea artefatti spettrali sottili
- **Range tipici**: depth 3 dB, f0 400–550 Hz, Q 2.0

### 5. Jitter
- **Descrizione**: Micro-variazioni di resampling (time jitter)
- **Parametri**: `ppm` (parti per milione)
- **Implementazione**: Interpolazione sinc/lineare con offset ±ppm
- **Range tipici**: 150–200 ppm

### 6. Transient Shaping
- **Descrizione**: Boost/attenuazione primissimi ms del suono
- **Parametri**: `gain_db` (gain sui primi 10–30 ms)
- **Uso**: Modifica attack senza alterare sustain
- **Range tipici**: 1.0–1.5 dB

### 7. White Noise
- **Descrizione**: Rumore gaussiano additivo
- **Parametri**: `snr_db` (Signal-to-Noise Ratio target)
- **Range tipici**: 35–40 dB (impercettibile a minimamente percettibile)

### 8. Pink Noise
- **Descrizione**: Rumore 1/f (più naturale del white)
- **Parametri**: `snr_db`
- **Range tipici**: 35–40 dB

---

## 📄 Configurazione YAML

### Struttura File: `AC/audio_obf_profiles.yaml`

```yaml
global:
  sample_rate: 44100
  chain_order: [pitch, eq_tilt, hp_lp, comb_notch, jitter, transient, noise_white, noise_pink]
  defaults:
    pitch: { min_abs_cents: 50, max_abs_cents: 200, enabled: false }
    eq_tilt: { min_db: -3, max_db: 6, enabled: false }
    # ... altri defaults ...

sounds:
  weapon/auto.ogg:
    pitch: { enabled: true, min_abs_cents: 75, max_abs_cents: 200 }
    eq_tilt: { enabled: true, min_db: -3, max_db: 6 }
    noise_white: { enabled: false, snr_db: 40 }
    # ... altri effetti ...
```

### Logica di Selezione

1. **Suono presente in `sounds:`** → usa parametri specifici
2. **Suono NON presente** → usa `defaults` da `global`
3. **Override CLI/ENV** → sovrascrive YAML (precedenza massima)

---

## 🚀 Uso da Linea di Comando

### Abilitazione Base

```bash
# Abilita obfuscation con configurazione YAML (effetti enabled=true)
./ac_client --audio-obf on

# Equivalente ENV
AC_AUDIO_OBF=1 ./ac_client
```

### Selezione Effetti Specifici

```bash
# SOLO pitch shift (ignora altri enabled nel YAML)
./ac_client --audio-obf on --obf-select pitch

# Pitch + EQ tilt
./ac_client --audio-obf on --obf-select pitch,eq_tilt

# Tutti gli effetti noise
./ac_client --audio-obf on --obf-select noise_white,noise_pink
```

### Override Parametri

```bash
# Forza pitch a valore fisso (ignora min/max YAML)
./ac_client --audio-obf on --obf-override pitch=150

# Pitch + EQ con valori custom
./ac_client --audio-obf on \
  --obf-select pitch,eq_tilt \
  --obf-override pitch=150 \
  --obf-override eq_tilt=3

# White noise con SNR custom
./ac_client --audio-obf on \
  --obf-select noise_white \
  --obf-override snr=35

# Combinazione complessa
./ac_client --audio-obf on \
  --obf-select pitch,eq_tilt,hp_lp \
  --obf-override pitch=120 \
  --obf-override eq_tilt=4 \
  --obf-override hp=100 \
  --obf-override lp=13500
```

### Equivalenti ENV

```bash
# Select
AC_AUDIO_OBF=1 AC_OBF_SELECT="pitch,eq_tilt" ./ac_client

# Override (sintassi parsabile)
AC_AUDIO_OBF=1 AC_OBF_OVERRIDE="pitch:150; eq_tilt:3; snr:40" ./ac_client
```

---

## 📊 Log di Esempio

### Log Formato Standard

Ogni suono processato genera UNA riga di log con tutti gli effetti applicati:

```
[AUDIO_OBF] weapon/auto.ogg → pitch:+137c; eq:+1.5dB; hp_lp:off; comb:off; jitter:off; transient:off; noise:off
[AUDIO_OBF] player/footsteps.ogg → pitch:+150c; eq:+1.5dB; hp_lp:off; comb:off; jitter:off; transient:off; noise:off
[AUDIO_OBF] voicecom/affirmative.ogg → pitch:+75c; eq:+0.0dB; hp_lp:off; comb:off; jitter:off; transient:off; noise:off
```

### Log con Effetti Multipli Attivi

```
[AUDIO_OBF] weapon/auto.ogg → pitch:+150c; eq:+3.0dB; hp_lp:hp@80Hz,lp@14kHz; comb:depth=3dB,f0=550Hz; jitter:200ppm; transient:+1.5dB; noise:white@40dB
[AUDIO_OBF] player/footsteps.ogg → pitch:+175c; eq:+4.5dB; hp_lp:off; comb:off; jitter:off; transient:off; noise:pink@35dB
```

### Log con Override CLI

```bash
$ ./ac_client --audio-obf on --obf-select pitch --obf-override pitch=200

[AUDIO_OBF] Config loaded: AC/audio_obf_profiles.yaml
[AUDIO_OBF] CLI override: pitch=200 (forced)
[AUDIO_OBF] weapon/auto.ogg → pitch:+200c; eq:off; hp_lp:off; comb:off; jitter:off; transient:off; noise:off
[AUDIO_OBF] player/footsteps.ogg → pitch:+200c; eq:off; hp_lp:off; comb:off; jitter:off; transient:off; noise:off
[AUDIO_OBF] voicecom/affirmative.ogg → pitch:+200c; eq:off; hp_lp:off; comb:off; jitter:off; transient:off; noise:off
```

---

## 🧪 Esempi Pratici

### Caso 1: Test Solo Pitch (Baseline)

**Obiettivo**: Validare che pitch shift funzioni come Step 1

```bash
cd "/Users/francesco03/Documents/GitHub/AssaultCube Server/AC"
./source/src/ac_client --audio-obf on --obf-select pitch
```

**Log atteso**:
```
[AUDIO_OBF] weapon/auto.ogg → pitch:+137c; eq:off; hp_lp:off; comb:off; jitter:off; transient:off; noise:off
```

**Valore pitch**: `(75 + 200) / 2 = 137.5 ≈ 137` cents

---

### Caso 2: Pitch + EQ Tilt

**Obiettivo**: Testare combinazione di 2 effetti

```bash
./source/src/ac_client --audio-obf on --obf-select pitch,eq_tilt
```

**Log atteso**:
```
[AUDIO_OBF] weapon/auto.ogg → pitch:+137c; eq:+1.5dB; hp_lp:off; comb:off; jitter:off; transient:off; noise:off
```

**Valori**:
- Pitch: midpoint 137 cents
- EQ: midpoint `(-3 + 6) / 2 = 1.5` dB

---

### Caso 3: Override Completo

**Obiettivo**: Forzare valori custom ignorando YAML

```bash
./source/src/ac_client --audio-obf on \
  --obf-select pitch,eq_tilt,noise_white \
  --obf-override pitch=150 \
  --obf-override eq_tilt=3 \
  --obf-override snr=35
```

**Log atteso**:
```
[AUDIO_OBF] weapon/auto.ogg → pitch:+150c; eq:+3.0dB; hp_lp:off; comb:off; jitter:off; transient:off; noise:white@35dB
```

---

### Caso 4: Test Noise Singolo

**Obiettivo**: Validare white noise injection

```bash
./source/src/ac_client --audio-obf on --obf-select noise_white --obf-override snr=40
```

**Log atteso**:
```
[AUDIO_OBF] weapon/auto.ogg → pitch:off; eq:off; hp_lp:off; comb:off; jitter:off; transient:off; noise:white@40dB
```

---

## 🔧 Implementazione Tecnica

### Ordine di Applicazione (Chain)

Gli effetti sono applicati in sequenza secondo `global.chain_order`:

1. **pitch** → SoundTouch WSOLA
2. **eq_tilt** → FFT shelving o IIR
3. **hp_lp** → Biquad filters
4. **comb_notch** → IIR comb
5. **jitter** → Resampling con offset
6. **transient** → Windowing gain
7. **noise_white** → Gaussian additive
8. **noise_pink** → 1/f shaping + additive

### Buffer Management

- **In-place quando possibile**: pitch, eq_tilt, hp_lp, transient
- **Temp buffer per convolution**: jitter (sinc interpolation)
- **Mixing finale**: noise (white/pink) applicati dopo tutti gli altri

### Compatibilità CSV

Per suoni **non presenti** in YAML, il sistema fallback su `AC/audio_obf_config.csv` (solo pitch shift) per retrocompatibilità con Step 1.

---

## 📈 Range Derivati da Test Soggettivi

Basati su ascolto guidato con `human_listen_and_label.py`:

| Suono | Pitch (cents) | EQ (dB) | Noise (dB SNR) | Note |
|-------|---------------|---------|----------------|------|
| **weapon/auto.ogg** | 75–200 | -3 a +6 | 35–40 (off default) | Gunshot robusto, tollerante |
| **player/footsteps.ogg** | 100–200 | -3 a +6 | 35–40 (off default) | Passi brevi, pitch meno critico |
| **voicecom/affirmative.ogg** | 50–100 | -3 a +3 | 40+ (off default) | Voce sensibile, range ridotto |

**Criterio `min_perc`** (minimo percettibile): primo valore con `perceived_change=Y` nei test  
**Criterio `max_ok`** (massimo accettabile): ultimo valore con `severity ≤ 2`

---

## 🚦 Status Implementazione

### ✅ Completato (Step 2)

- [x] Schema YAML completo con 8 effetti
- [x] Configurazione per 3 suoni chiave
- [x] Documentazione CLI/ENV
- [x] Esempi pratici replicabili
- [x] Log format specification

### 🔄 In Corso

- [ ] Parser YAML C++ (yaml-cpp integration)
- [ ] Implementazione effetti modulari in `audio_runtime_obf.cpp`
- [ ] CLI parsing `--obf-select` e `--obf-override`
- [ ] Testing + compilazione verificata

### ⏳ Step 3 (Futuro)

- [ ] Randomizzazione parametri (uniform, normal, beta distributions)
- [ ] Sampling in [min, max] con seed deterministico
- [ ] Adaptive obfuscation (modifica parametri per sessione/mappa)

---

## 📚 Riferimenti

- **Tesi**: `TESI_ANTICHEAT.md` — Sezione 17 (Calibrazione soggettiva multi-perturbazione)
- **Config**: `AC/audio_obf_profiles.yaml`
- **Test soggettivi**: `ADV_ML/tests/subjective_results.csv`
- **Guida test umani**: `ADV_ML/tests/README_PER_UBI.md`
- **CLI test**: `ADV_ML/tests/human_listen_and_label.py`

---

**Fine Documento**

**Next Steps**: Implementare parser YAML e effetti DSP in C++, compilare, testare in-game.

