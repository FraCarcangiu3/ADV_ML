# Nuovi Effetti Spaziali Anti-ML

## 📋 Panoramica

Sono stati implementati **3 nuovi effetti audio spaziali** specificamente progettati per disturbare le feature IPD (Inter-Phase Difference) e ILD (Inter-Level Difference) utilizzate dai modelli ML per la localizzazione audio.

**Data implementazione:** Dicembre 2024  
**Autore:** Francesco Carcangiu

---

## 🎯 Motivazione

I test precedenti hanno dimostrato che:
- **Pitch shift** è inefficace (feature IPD/ILD invarianti)
- **Noise/EQ normali** hanno impatto limitato (~10-17% drop)
- Serve perturbazioni che disturbano le **relazioni spaziali tra canali**

---

## 🔊 Nuovi Effetti Implementati

### 1️⃣ Spatial Delay (micro-delay tra canali)

**Cosa fa:** Applica delay diversi per ogni canale (ordine di pochi sample) per sporcare l'IPD.

**Livelli calibrati:**
| Livello | Max Samples | Tempo @ 96kHz | Tempo @ 44.1kHz |
|---------|-------------|---------------|-----------------|
| LOW | ±2 samples | ~0.02ms | ~0.045ms |
| MEDIUM | ±5 samples | ~0.05ms | ~0.11ms |
| HIGH | ±10 samples | ~0.10ms | ~0.23ms |

**Impatto feature (smoke test):** 0.37-0.46% (moderato)

**Percettibilità:** Impercettibile (delay sub-millisecondi)

---

### 2️⃣ Channel Gain Jitter (variazioni gain per canale)

**Cosa fa:** Moltiplica ogni canale per un fattore di gain leggermente diverso (±0.5-1.5 dB) per sporcare l'ILD.

**Livelli calibrati:**
| Livello | Max dB |
|---------|--------|
| LOW | ±0.5 dB |
| MEDIUM | ±1.0 dB |
| HIGH | ±1.5 dB |

**Impatto feature (smoke test):** 0.03-0.09% (basso)

**Percettibilità:** Molto sottile, difficilmente percettibile

---

### 3️⃣ Multi-Channel Noise (rumore indipendente per canale)

**Cosa fa:** Aggiunge rumore DIVERSO per ogni canale (invece del solito rumore identico su tutti i canali). Disturba sia IPD che ILD.

**Livelli calibrati:**

**White variant:**
| Livello | SNR |
|---------|-----|
| LOW | 42 dB |
| MEDIUM | 40 dB |
| HIGH | 38 dB |

**Pink variant:**
| Livello | SNR |
|---------|-----|
| LOW | 22 dB |
| MEDIUM | 20 dB |
| HIGH | 18 dB |

**Impatto feature (smoke test):**
- White: 18-21% (molto efficace)
- Pink: **52-56%** (ESTREMAMENTE efficace!)

**Percettibilità:** Comparabile al noise normale, ma spazialmente più "caotico"

---

## 🔧 Implementazione Tecnica

### C++ (Client AssaultCube)

**File modificati:**
- `AC/source/src/audio_runtime_obf.h` — struct AudioProfile estesa
- `AC/source/src/audio_runtime_obf.cpp` — 3 nuove funzioni + integrazione nella pipeline
- `AC/audio_obf_config.csv` — 8 nuove colonne

**Nuove funzioni:**
```cpp
static void apply_spatial_delay(float* samples, int frames, int channels, int max_samples, std::mt19937& rng)
static void apply_channel_gain_jitter(float* samples, int frames, int channels, float max_db, std::mt19937& rng)
static void apply_multi_channel_noise(float* samples, int frames, int channels, float snr_db, bool use_pink, std::mt19937& rng)
```

**Ordine applicazione effetti:**
1. EQ tilt
2. High-pass filter
3. Low-pass filter
4. Pitch shift
5. **→ Spatial delay** (nuovo)
6. **→ Gain jitter** (nuovo)
7. Tone injection
8. Noise (white/pink)
9. **→ Multi-channel noise** (nuovo)

**Logging:** I nuovi effetti compaiono nel log `[AUDIO_OBF]`:
```
[AUDIO_OBF_RAND] weapon/usp → pitch:+123c; ... spatial_delay:±5smp; gain_jitter:±1.0dB; multi_noise:pink@19dB
```

---

### Python (Offline Testing)

**File modificati:**
- `ADV_ML/audio_effects.py` — 3 nuove funzioni pure
- `COLLEAGUE_BSc_Thesis/model_classifier/perturbation_utils.py` — preset aggiunti
- `COLLEAGUE_BSc_Thesis/model_classifier/run_best_models_perturb_sweep.py` — integrazione nel sweep

**Nuove funzioni:**
```python
def apply_spatial_delay(signal, sr, max_samples, seed=None) -> np.ndarray
def apply_channel_gain_jitter(signal, max_db, seed=None) -> np.ndarray
def apply_multi_channel_noise(signal, snr_db, noise_type="white", seed=None) -> np.ndarray
```

**Preset disponibili:**
```python
# Spatial delay
"spatial_delay_light/medium/strong"  # 2/5/10 samples

# Gain jitter
"gain_jitter_light/medium/strong"    # 0.5/1.0/1.5 dB

# Multi-channel noise
"multi_white_light/medium/strong"    # SNR 42/40/38 dB
"multi_pink_light/medium/strong"     # SNR 22/20/18 dB
```

---

## 🚀 Come Usare

### In-Game (Client C++)

1. **Ricompila il client:**
```bash
cd AC/source
make clean && make
```

2. **Abilita obfuscation con randomizzazione:**
```bash
AC_AUDIO_OBF_RANDOMIZE=1 ./ac_client
```

3. **Controlla i log:**
Spara con la pistola (weapon/usp) e cerca nel log:
```
[AUDIO_OBF_RAND] weapon/usp → ... spatial_delay:±Xsmp; gain_jitter:±YdB; multi_noise:type@ZdB
```

### Offline Testing (Python)

1. **Smoke test (verifica funzionamento):**
```bash
cd COLLEAGUE_BSc_Thesis
python -m model_classifier.test_new_spatial_effects
```

2. **Test singolo effetto:**
```python
import audio_effects
import numpy as np

# Carica audio multicanale (frames, 8)
audio = ...  # shape (N, 8)

# Applica spatial delay
audio_delayed = audio_effects.apply_spatial_delay(audio, 96000, max_samples=5)

# Applica gain jitter
audio_jittered = audio_effects.apply_channel_gain_jitter(audio, max_db=1.0)

# Applica multi-channel pink noise
audio_multi_pink = audio_effects.apply_multi_channel_noise(audio, snr_db=20.0, noise_type="pink")
```

3. **Sweep completo (tutti i modelli e perturbazioni):**
```bash
cd COLLEAGUE_BSc_Thesis
python -m model_classifier.run_best_models_perturb_sweep --max-samples 100
```

Questo ora include anche i 4 nuovi tipi di perturbazione (spatial_delay, gain_jitter, multi_white_noise, multi_pink_noise) a 3 livelli ciascuno.

---

## 📊 Risultati Attesi

Basandosi sui risultati del smoke test:

**Classifica efficacia (cambio feature):**
1. **Multi-channel pink noise:** ~52-56% (WINNER! 🏆)
2. **Multi-channel white noise:** ~18-21%
3. **Spatial delay:** ~0.37-0.46%
4. **Gain jitter:** ~0.03-0.09% (troppo sottile)

**Raccomandazioni:**
- **Primary:** Multi-channel pink noise (MEDIUM o HIGH)
- **Alternative:** Multi-channel white noise
- **Combo:** Multi-pink + spatial delay per effetto cumulativo
- **Evitare:** Gain jitter da solo (impatto troppo basso)

---

## 🔬 Test Completo su Modelli ML

Per valutare l'impatto reale sulle accuracy dei modelli:

```bash
cd COLLEAGUE_BSc_Thesis

# Test completo (~20-30 minuti, include i nuovi effetti)
python -m model_classifier.run_best_models_perturb_sweep

# Analisi risultati
python -m model_classifier.analyze_perturbation_results
```

I risultati includeranno ora anche:
- 12 nuovi test per spatial_delay/gain_jitter/multi_white/multi_pink (3 livelli × 4 tipi)
- Combo con effetti spaziali
- Confronto con perturbazioni classiche

---

## 📝 Note Implementative

### Differenze tra noise normale vs multi-channel

**Noise normale (white/pink):**
- Stesso rumore aggiunto a tutti i canali
- Mantiene correlazioni spaziali (IPD/ILD invariati)
- Impatto limitato sui modelli spaziali

**Multi-channel noise:**
- Rumore DIVERSO per ogni canale
- **Distrugge correlazioni spaziali**
- Impatto molto maggiore su IPD/ILD
- Risultati smoke test: fino a 56% cambio feature!

### Perché multi-channel pink > spatial delay?

- Spatial delay: sposta il segnale ma mantiene la forma
- Multi-noise: introduce variabilità stocastica differente per canale
- Pink noise ha spettro 1/f che interagisce meglio con feature MEL

---

## ⚙️ Configurazione CSV (C++)

Le nuove colonne in `audio_obf_config.csv`:

```csv
..., spatial_delay_min_samples, spatial_delay_max_samples, gain_jitter_min_db, gain_jitter_max_db, multi_noise_type, multi_white_snr_min, multi_white_snr_max, multi_pink_snr_min, multi_pink_snr_max
```

**Esempio weapon/usp con nuovi effetti:**
```csv
weapon/usp, ..., 0, 5, 0.0, 1.0, random, 38, 42, 18, 22
```

**Backward compatibility:** Se le nuove colonne mancano o sono vuote, gli effetti sono disabilitati (OFF).

---

## ✅ Checklist Integrazione

- [x] Header C++ aggiornato (audio_runtime_obf.h)
- [x] Implementazione C++ (audio_runtime_obf.cpp)
- [x] CSV config esteso (audio_obf_config.csv)
- [x] Parser CSV aggiornato
- [x] Randomizzazione integrata
- [x] Logging esteso
- [x] Funzioni Python (audio_effects.py)
- [x] Preset Python (perturbation_utils.py)
- [x] Sweep test aggiornato (run_best_models_perturb_sweep.py)
- [x] Combo perturbazioni aggiunte
- [x] Smoke test eseguito con successo
- [ ] Ricompilazione client C++
- [ ] Test in-game
- [ ] Sweep completo su modelli ML

---

**Prossimo step:** Ricompila il client C++ e testa in-game, oppure esegui subito il sweep ML offline per vedere l'impatto sulle accuracy.

---

*Documento generato automaticamente il 03/12/2024*

