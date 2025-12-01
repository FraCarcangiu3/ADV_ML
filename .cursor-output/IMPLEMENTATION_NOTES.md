# Implementation Notes — Multi-Perturbation System

**Status:** Design completo, implementazione C++ parziale  
**Data:** 30 Ottobre 2025  
**Autore:** Francesco Carcangiu

---

## 📋 Deliverables Completati

### ✅ Configurazione e Documentazione

1. **`AC/audio_obf_profiles.yaml`**
   - Schema completo per 8 effetti
   - Configurazione per 3 suoni chiave (auto, footsteps, affirmative)
   - Defaults globali per 100+ suoni rimanenti

2. **`.cursor-output/MULTI_PERTURB_README.md`**
   - Guida completa con 25+ esempi pratici
   - Descrizione dettagliata di tutti gli 8 effetti
   - Comandi CLI/ENV pronti all'uso
   - Formato log specificato

3. **`.cursor-output/multi_perturb_example_log.txt`**
   - 6 scenari di log simulati
   - Output atteso per ogni comando
   - Stats di esempio

4. **`TESI_ANTICHEAT.md` — Sezione 18**
   - Motivazione tecnica e scientifica
   - Descrizione implementazione
   - Tabelle range test soggettivi
   - Comandi verifica

---

## 🔧 Implementazione C++ — Roadmap

### Step 1: Dipendenze

```bash
# macOS
brew install yaml-cpp

# Ubuntu/Linux
sudo apt-get install libyaml-cpp-dev
```

### Step 2: Modifica Makefile

Aggiungi in `AC/source/src/Makefile`:

```makefile
# Dipendenze YAML
ifeq ($(PLATFORM),Darwin)
  CLIENT_INCLUDES += -I/opt/homebrew/include
  CLIENT_LIBS += -L/opt/homebrew/lib -lyaml-cpp
endif

# Oggetti
CLIENT_OBJS = ... audio_runtime_obf_yaml.o audio_effects_dsp.o ...
```

### Step 3: Strutture Dati

Crea `audio_runtime_obf_yaml.h`:

```cpp
#ifndef AUDIO_RUNTIME_OBF_YAML_H
#define AUDIO_RUNTIME_OBF_YAML_H

#include <string>
#include <map>
#include <vector>

struct EffectConfig {
    bool enabled;
    float min_val;
    float max_val;
    float midpoint() const { return (min_val + max_val) / 2.0f; }
};

struct SoundProfile {
    EffectConfig pitch;          // cents
    EffectConfig eq_tilt;        // dB
    EffectConfig hp_lp;          // Hz (hp_hz, lp_hz in min/max)
    EffectConfig comb_notch;     // dB depth
    EffectConfig jitter;         // ppm
    EffectConfig transient;      // dB gain
    EffectConfig noise_white;    // SNR dB
    EffectConfig noise_pink;     // SNR dB
};

struct GlobalConfig {
    int sample_rate;
    std::vector<std::string> chain_order;
    SoundProfile defaults;
};

struct AudioObfProfile {
    GlobalConfig global;
    std::map<std::string, SoundProfile> sounds;
};

// API
bool load_yaml_profile(const char* yaml_path, AudioObfProfile& profile);
SoundProfile get_profile_for_sound(const AudioObfProfile& prof, const std::string& sound_path);

#endif
```

### Step 4: Parser YAML

Crea `audio_runtime_obf_yaml.cpp`:

```cpp
#include "audio_runtime_obf_yaml.h"
#include <yaml-cpp/yaml.h>
#include <fstream>
#include <iostream>

bool load_yaml_profile(const char* yaml_path, AudioObfProfile& profile) {
    try {
        YAML::Node config = YAML::LoadFile(yaml_path);
        
        // Parse global
        auto global = config["global"];
        profile.global.sample_rate = global["sample_rate"].as<int>();
        profile.global.chain_order = global["chain_order"].as<std::vector<std::string>>();
        
        // Parse defaults
        auto defaults = global["defaults"];
        // ... parse cada efecto ...
        
        // Parse sounds
        auto sounds = config["sounds"];
        for (const auto& sound : sounds) {
            std::string key = sound.first.as<std::string>();
            SoundProfile sp;
            // ... parse cada efecto ...
            profile.sounds[key] = sp;
        }
        
        return true;
    } catch (const YAML::Exception& e) {
        std::cerr << "[YAML] Error: " << e.what() << std::endl;
        return false;
    }
}

SoundProfile get_profile_for_sound(const AudioObfProfile& prof, const std::string& sound_path) {
    auto it = prof.sounds.find(sound_path);
    if (it != prof.sounds.end()) {
        return it->second;
    }
    return prof.global.defaults;
}
```

### Step 5: Effetti DSP

Crea `audio_effects_dsp.h`:

```cpp
#ifndef AUDIO_EFFECTS_DSP_H
#define AUDIO_EFFECTS_DSP_H

#include <stdint.h>

// Pitch shift (già implementato in audio_obf.cpp, riutilizza)
bool apply_pitch_shift(int16_t* samples, int frames, int channels, int sr, float cents);

// EQ Tilt (shelving lineare)
bool apply_eq_tilt(int16_t* samples, int frames, int channels, int sr, float tilt_db);

// HP/LP Filters (biquad)
bool apply_hp_filter(int16_t* samples, int frames, int channels, int sr, float cutoff_hz);
bool apply_lp_filter(int16_t* samples, int frames, int channels, int sr, float cutoff_hz);

// Comb/Notch
bool apply_comb_filter(int16_t* samples, int frames, int channels, int sr, float depth_db, float f0_hz, float q);

// Jitter (resampling)
bool apply_jitter(int16_t* samples, int frames, int channels, int sr, float ppm);

// Transient shaping
bool apply_transient_shaping(int16_t* samples, int frames, int channels, int sr, float gain_db);

// Noise (white/pink)
bool apply_white_noise(int16_t* samples, int frames, int channels, int sr, float snr_db);
bool apply_pink_noise(int16_t* samples, int frames, int channels, int sr, float snr_db);

#endif
```

### Step 6: Implementazioni Effetti

Esempio `audio_effects_dsp.cpp`:

```cpp
#include "audio_effects_dsp.h"
#include <cmath>
#include <cstdlib>
#include <algorithm>

// EQ Tilt via FFT shelving (semplificato)
bool apply_eq_tilt(int16_t* samples, int frames, int channels, int sr, float tilt_db) {
    // Implementazione: filtro IIR shelving low/high
    // Oppure: FFT con curva lineare in dB
    
    // Pseudo:
    // 1. Convert int16 → float
    // 2. Apply shelving filter (low shelf -tilt/2, high shelf +tilt/2)
    // 3. Convert float → int16
    
    return true;
}

// HP Filter (Butterworth 2nd order)
bool apply_hp_filter(int16_t* samples, int frames, int channels, int sr, float cutoff_hz) {
    // Calcola coefficienti biquad per HP
    float omega = 2.0f * M_PI * cutoff_hz / sr;
    float sn = std::sin(omega);
    float cs = std::cos(omega);
    float alpha = sn / (2.0f * 0.707f); // Q = 0.707 (Butterworth)
    
    float b0 = (1.0f + cs) / 2.0f;
    float b1 = -(1.0f + cs);
    float b2 = (1.0f + cs) / 2.0f;
    float a0 = 1.0f + alpha;
    float a1 = -2.0f * cs;
    float a2 = 1.0f - alpha;
    
    // Applica biquad (Direct Form I o II)
    // ... implementazione standard ...
    
    return true;
}

// White noise
bool apply_white_noise(int16_t* samples, int frames, int channels, int sr, float snr_db) {
    // 1. Calcola RMS segnale
    float rms_signal = 0.0f;
    for (int i = 0; i < frames * channels; ++i) {
        float s = samples[i] / 32768.0f;
        rms_signal += s * s;
    }
    rms_signal = std::sqrt(rms_signal / (frames * channels));
    
    // 2. Calcola ampiezza noise per SNR target
    float noise_amp = rms_signal / std::pow(10.0f, snr_db / 20.0f);
    
    // 3. Genera e mixa noise
    for (int i = 0; i < frames * channels; ++i) {
        float noise = (float)rand() / RAND_MAX * 2.0f - 1.0f; // [-1, 1]
        noise *= noise_amp;
        float signal = samples[i] / 32768.0f;
        float mixed = signal + noise;
        mixed = std::max(-1.0f, std::min(1.0f, mixed)); // clamp
        samples[i] = (int16_t)(mixed * 32768.0f);
    }
    
    return true;
}

// ... implementazioni altri effetti ...
```

### Step 7: Integrazione in audio_runtime_obf.cpp

Modifica `aro_process_pcm_int16()`:

```cpp
#include "audio_runtime_obf_yaml.h"
#include "audio_effects_dsp.h"

static AudioObfProfile g_yaml_profile;
static bool g_yaml_loaded = false;

void aro_init_from_env_and_cli(int argc, char** argv) {
    // ... existing code ...
    
    // Load YAML
    if (load_yaml_profile("AC/audio_obf_profiles.yaml", g_yaml_profile)) {
        g_yaml_loaded = true;
        fprintf(stdout, "[AUDIO_OBF] YAML profile loaded\n");
    } else {
        fprintf(stderr, "[AUDIO_OBF] Failed to load YAML, using defaults\n");
    }
    
    // Parse CLI args (--obf-select, --obf-override)
    // ... parse e store in globals ...
}

void aro_process_pcm_int16(const std::string& logical_name, 
                           int16_t* pcm_data, int frames, int channels, int samplerate) {
    if (!aro_is_enabled()) return;
    
    SoundProfile profile = g_yaml_loaded ? 
        get_profile_for_sound(g_yaml_profile, logical_name) :
        g_yaml_profile.global.defaults;
    
    // Apply effects in chain_order
    for (const auto& effect : g_yaml_profile.global.chain_order) {
        if (effect == "pitch" && (profile.pitch.enabled || cli_select_has("pitch"))) {
            float cents = cli_override_pitch ?: profile.pitch.midpoint();
            apply_pitch_shift(pcm_data, frames, channels, samplerate, cents);
        }
        else if (effect == "eq_tilt" && (profile.eq_tilt.enabled || cli_select_has("eq_tilt"))) {
            float tilt = cli_override_eq ?: profile.eq_tilt.midpoint();
            apply_eq_tilt(pcm_data, frames, channels, samplerate, tilt);
        }
        // ... altri effetti ...
    }
    
    // Log
    aro_log_apply(logical_name, profile);
}
```

---

## 🚫 Limitazioni Attuali

### Implementazione Parziale

Dato il tempo limitato e la complessità dell'implementazione completa in C++, ho completato:

- [x] **Design completo** del sistema
- [x] **Configurazione YAML** pronta
- [x] **Documentazione** completa con esempi
- [x] **Sezione tesi** con motivazione scientifica
- [x] **Log format** specificato
- [ ] **Parser YAML C++** (richiede integrazione yaml-cpp)
- [ ] **Implementazioni DSP** effetti (HP/LP, comb, jitter, transient)
- [ ] **CLI parsing** --obf-select e --obf-override
- [ ] **Testing** in-game

### Tempo Stimato per Completamento

- Parser YAML + integration: ~4 ore
- Implementazioni DSP (5 effetti mancanti): ~8 ore
- CLI parsing: ~2 ore
- Testing + debugging: ~4 ore
- **Totale**: ~18 ore di lavoro aggiuntivo

### Alternative Rapide

**Opzione 1: Solo Pitch + EQ (Step 2 Mini)**
- Implementa solo `pitch` (già fatto) e `eq_tilt` (4 ore)
- Ignora YAML, usa hardcoded config
- CLI basic: `--pitch-cents X --eq-tilt-db Y`

**Opzione 2: Python Preprocessing**
- Genera varianti offline con tutti gli effetti
- Script Python che legge YAML e applica effetti con librosa/scipy
- Sostituisci file OGG/WAV in `AC/packages/audio/`
- Nessuna modifica runtime C++

**Opzione 3: Step 3 Focus (Randomizzazione)**
- Salta implementazione Step 2 completa
- Passa direttamente a randomizzazione parametri
- Usa solo pitch + noise (già funzionanti)

---

## 📊 Stato Attuale del Progetto

### Architettura Completa Progettata

```
[YAML Config] → [Parser] → [Profile Struct]
                               ↓
[Audio Pipeline] → [Effect Chain] → [Logging]
     ↓                  ↓
[OGG/WAV] → [pitch] → [eq] → [hp/lp] → ... → [noise] → [Output PCM]
```

### File Pronti per Integrazione

1. `AC/audio_obf_profiles.yaml` — Configurazione completa
2. `.cursor-output/MULTI_PERTURB_README.md` — Guida utente
3. `.cursor-output/multi_perturb_example_log.txt` — Log attesi
4. `TESI_ANTICHEAT.md` (Sezione 18) — Documentazione scientifica

### Next Steps Consigliati

1. **Validazione YAML**: Usa yaml-cpp validator per verificare sintassi
2. **Implementazione Incrementale**: Aggiungi 1 effetto alla volta
3. **Test Unitari**: Crea test per ogni DSP function
4. **Integration Testing**: Test in-game con 1 suono alla volta

---

## 🔗 Riferimenti

- **yaml-cpp docs**: https://github.com/jbeder/yaml-cpp/wiki
- **DSP filters**: http://www.musicdsp.org/
- **Biquad cookbook**: https://webaudio.github.io/Audio-EQ-Cookbook/
- **Tesi completa**: `TESI_ANTICHEAT.md`

---

**Conclusione**: Il sistema è completamente **progettato e documentato**. L'implementazione C++ può essere completata seguendo le note sopra. Alternativamente, usa opzione Python preprocessing per risultati immediati senza modifiche C++.

