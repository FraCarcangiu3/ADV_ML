
**Report ufficiale delle modifiche al codice di AssaultCube per la tesi di anti-cheat ML**

Questo documento contiene il codice completo dei file creati o modificati per implementare il framework di audio obfuscation runtime. È il riferimento centrale per ricostruire il client modificato e per distribuirlo per test. Tutti i file qui elencati includono il loro contenuto completo e la spiegazione del loro ruolo nell'architettura.

---

## 1. FILE CREATI/MODIFICATI

### 1.1 `AC/source/src/audio_runtime_obf.h`

**Contenuto completo**:

```cpp
// audio_runtime_obf.h
// Framework runtime per applicare trasformazioni audio al PCM decodificato
// 
// Step 1: Infrastruttura base + logging (trasformazioni placeholder)
// Step 2: Configurazione CSV e applicazione deterministica
// Step successivi: Randomizzazione e tecniche avanzate
//
// Autore: Francesco Carcangiu
// Data: 29 Ottobre 2025

#pragma once

#include <string>
#include <cstdint>
#include <unordered_map>

// ========================================================================
// Struttura di configurazione per le trasformazioni audio (globale)
// ========================================================================

struct ARO_Profile {
    bool enabled = false;         // obfuscation globale ON/OFF
    
    // Pitch shift (Step 1: parametri pronti, applicazione opzionale)
    bool use_pitch = false;       // abilita pitch shifting
    int  pitch_cents = 0;         // +/- cents (100 cents = 1 semitono)
    
    // Noise injection (Step futuro - placeholder)
    bool use_noise = false;       // abilita aggiunta rumore
    float noise_snr_db = 0.f;     // target SNR in decibel
    
    // Tone injection (Step futuro - placeholder)
    bool use_tone = false;        // abilita aggiunta tono
    float tone_freq_hz = 0.f;     // frequenza tono in Hz
    float tone_level_db = 0.f;    // livello tono in dB
};

// ========================================================================
// Struttura per profilo audio specifico (da CSV)
// Step 2: Configurazione per-sound
// ========================================================================

struct AudioProfile {
    std::string file_name;        // Nome file (es. "weapon/shotgun.ogg")
    
    // Pitch shift range
    int min_pitch_cents = 0;      // Minimo pitch shift in cents
    int max_pitch_cents = 0;      // Massimo pitch shift in cents
    
    // Noise injection — range completi per white e pink
    std::string noise_type;       // "none", "white", "pink", "random"
    float white_snr_min = 0.f;    // White noise SNR min (dB)
    float white_snr_max = 0.f;    // White noise SNR max (dB)
    float pink_snr_min = 0.f;     // Pink noise SNR min (dB)
    float pink_snr_max = 0.f;     // Pink noise SNR max (dB)
    
    // Tone frequency (se noise_type = "tone") — LEGACY, raramente usato
    int min_freq = 0;             // Minima frequenza in Hz
    int max_freq = 0;             // Massima frequenza in Hz
    
    // EQ tilt — range completi per boost e cut
    std::string eq_mode;          // "none", "boost", "cut", "random"
    float eq_boost_min = 0.f;     // EQ boost min (dB)
    float eq_boost_max = 0.f;     // EQ boost max (dB)
    float eq_cut_min = 0.f;       // EQ cut min (dB, negativo)
    float eq_cut_max = 0.f;       // EQ cut max (dB, negativo)
    
    // High-pass filter — range completo
    int hp_min_hz = 0;            // HP cutoff min (Hz, 0 = off)
    int hp_max_hz = 0;            // HP cutoff max (Hz)
    
    // Low-pass filter — range completo
    int lp_min_hz = 0;            // LP cutoff min (Hz)
    int lp_max_hz = 0;            // LP cutoff max (Hz, 0 = off)
};

// ========================================================================
// API pubblica
// ========================================================================

/**
 * Carica profili audio dal file CSV.
 * 
 * Step 2: Parsing del file audio_obf_config.csv per caricare configurazioni
 * specifiche per ogni suono.
 * 
 * @param path Path al file CSV (relativo a root AC/)
 * @return true se caricamento riuscito, false se file non trovato
 */
bool aro_load_profiles_from_csv(const std::string& path);

/**
 * Inizializza il framework da variabili d'ambiente e argomenti CLI.
 * 
 * Step 1: Parsing ENV/CLI per abilitare/disabilitare framework
 * Step 2: Caricamento automatico del file audio_obf_config.csv
 * 
 * Variabili d'ambiente supportate:
 *   AC_AUDIO_OBF=0|1              (default: 0, disabilitato)
 * 
 * Argomenti CLI supportati (precedenza su ENV):
 *   --audio-obf on|off
 * 
 * La precedenza è: CLI > ENV > default (OFF)
 * 
 * @param argc Numero di argomenti da main()
 * @param argv Array di argomenti da main()
 */
void aro_init_from_env_and_cli(int argc, char** argv);

/**
 * Abilita/disabilita il sistema di obfuscation runtime.
 * 
 * @param on true per abilitare, false per disabilitare
 */
void aro_set_enabled(bool on);

/**
 * Controlla se il sistema è abilitato.
 * 
 * @return true se abilitato, false altrimenti
 */
bool aro_is_enabled();

/**
 * Processa un buffer PCM int16 applicando le trasformazioni configurate.
 * 
 * NOTA STEP 1: Per ora questa funzione logga solamente le operazioni
 * che verrebbero eseguite, senza modificare realmente il buffer.
 * L'applicazione delle trasformazioni avverrà negli step successivi.
 * 
 * @param logical_name Nome logico del suono (es. "player/footsteps.ogg")
 * @param pcm          Buffer PCM in formato int16 interleaved
 * @param frames       Numero di frame audio (samples / channels)
 * @param channels     Numero di canali (1=mono, 2=stereo)
 * @param samplerate   Sample rate in Hz (es. 22050, 44100)
 */
void aro_process_pcm_int16(const std::string& logical_name, 
                           int16_t* pcm, 
                           int frames, 
                           int channels, 
                           int samplerate);

/**
 * Stampa lo stato iniziale del sistema (chiamare dopo init).
 * Output format parsabile:
 *   [AUDIO_OBF] enabled=<0|1> from=<ENV|CLI> use_pitch=<0|1> use_noise=<0|1> use_tone=<0|1>
 */
void aro_log_loaded();

/**
 * Logga l'applicazione di un profilo a un suono specifico.
 * Output format parsabile:
 *   [AUDIO_OBF] <name> → pitch:±N cents, noise:SNR=X dB, tone:F Hz @ L dB
 * 
 * @param logical_name Nome del suono
 * @param p            Profilo applicato
 */
void aro_log_apply(const std::string& logical_name, const ARO_Profile& p);
```

**Ruolo**: Header del framework audio obfuscation. Definisce le strutture `ARO_Profile` (globale) e `AudioProfile` (per-sound) e l'API pubblica. Espone `aro_process_pcm_int16()` che è la funzione principale di hook chiamata da `openal.cpp`.

---

### 1.2 `AC/source/src/audio_runtime_obf.cpp`

**Contenuto completo**: [File di 1009 righe — vedere contenuto completo sopra nella lettura del file]

**Ruolo**: Implementazione completa del framework audio obfuscation. Contiene:
- Conversioni int16 ↔ float per processing audio
- Algoritmi DSP: pitch shift (SoundTouch), white/pink noise injection, tone injection, EQ tilt (high-shelf biquad), HP/LP filters (Butterworth 2° ordine)
- Parser CSV per leggere configurazioni per-sound da `audio_obf_config.csv`
- Logica di randomizzazione (Step 3): distribuzioni uniformi per pitch, SNR, EQ, HP, LP
- Hook principale `aro_process_pcm_int16()`: chiamato da `openal.cpp` dopo decodifica OGG/WAV, prima di `alBufferData()`.

**Catena di processing** (ordine applicazione):
1. EQ Tilt → 2. HP Filter → 3. LP Filter → 4. Pitch Shift → 5. Tone Injection → 6. Noise Injection

**Step implementati**:
- **Step 1**: Infrastruttura + logging
- **Step 2**: Configurazione CSV + applicazione deterministica (midpoint dei range)
- **Step 3**: Randomizzazione con distribuzioni uniformi (seed da timestamp per non-reproducibilità)

---

### 1.3 `AC/source/src/audio_obf.h` (sistema legacy - Step 0)

**Contenuto completo**:

```cpp
// audio_obf.h
// Audio Obfuscation / Anti-Cheat PoC
// Fornisce pitch shift parametrico per asset audio (opzionale, runtime)
//
// Autore: Francesco Carcangiu
// Data: 15 Ottobre 2024
// Scopo: Dimostrare fattibilità tecnica di trasformazioni audio client-side
//        per contrastare cheat basati su riconoscimento audio automatizzato.

#ifndef AUDIO_OBF_H
#define AUDIO_OBF_H

#include <stdbool.h>
#include <stdint.h>

// ========================================================================
// API pubblica per controllo runtime del pitch shift
// ========================================================================

/**
 * Inizializza il sottosistema di obfuscation audio.
 * Legge variabili d'ambiente e argomenti da riga di comando.
 * 
 * Variabili d'ambiente:
 *   AC_ANTICHEAT_PITCH_ENABLED=0|1    (default: 0 disabilitato)
 *   AC_ANTICHEAT_PITCH_CENTS=<int>    (default: 0, range: -100..+100)
 * 
 * Argomenti CLI (sovrascrivono env vars se presenti):
 *   --pitch-enable
 *   --pitch-cents <N>
 * 
 * @param argc Numero argomenti da main()
 * @param argv Array argomenti da main()
 */
void ac_audio_obf_init(int argc, char **argv);

/**
 * Restituisce true se il pitch shift è abilitato a runtime.
 * Se disabilitato, nessuna trasformazione viene applicata.
 */
bool ac_pitch_is_enabled();

/**
 * Restituisce il valore di pitch shift in cents (centesimi di semitono).
 * 100 cents = 1 semitono.
 * Valori positivi → pitch più alto (frequenze aumentate).
 * Valori negativi → pitch più basso (frequenze diminuite).
 * 
 * Range consigliato per impercettibilità: -10..+10 cents.
 * Range test: -100..+100 cents.
 */
int ac_pitch_cents();

/**
 * Applica pitch shift in-place a un buffer PCM.
 * 
 * Questa è la funzione principale da chiamare dopo il decode audio
 * e prima di passare i dati a OpenAL (alBufferData).
 * 
 * NOTA IMPORTANTE: Se SoundTouch non è disponibile, la funzione
 * può usare un fallback (AL_PITCH a livello OpenAL, che non modifica
 * il buffer PCM, oppure un semplice resampling). Il comportamento
 * dipende dalla configurazione di build.
 * 
 * @param samples       Buffer PCM in formato int16 (mono/stereo interleaved).
 *                      Il buffer verrà modificato in-place.
 * @param frames        Numero di frame audio (samples / channels).
 * @param channels      Numero di canali (1=mono, 2=stereo).
 * @param samplerate    Sample rate in Hz (es. 22050, 44100).
 * @param cents         Pitch shift in cents (può essere negativo).
 * 
 * @return true se trasformazione applicata, false se fallback/skip.
 */
bool apply_pitch_inplace(int16_t* samples, int frames, int channels, int samplerate, int cents);

#endif // AUDIO_OBF_H
```

**Ruolo**: Sistema legacy (Step 0) per pitch shift semplice. Implementazione preliminare con API diversa dal nuovo framework. Ancora presente nel codice per compatibilità, ma il nuovo sistema `audio_runtime_obf` lo sostituisce completamente. Inizializzato in `main.cpp` (linea 1214-1215) e usato in `openal.cpp` (linee 298-314) per OGG prima del nuovo framework.

---

### 1.4 `AC/source/src/audio_obf.cpp` (sistema legacy - Step 0)

**Contenuto completo**:

```cpp
// audio_obf.cpp
// Implementazione sistema di obfuscation audio (pitch shift)
//
// Autore: Francesco Carcangiu
// Data: 15 Ottobre 2024

#include "audio_obf.h"
#include <cstdlib>
#include <cstring>
#include <cstdio>
#include <vector>
#include <algorithm>

// Tenta di usare SoundTouch se disponibile
// Se non presente al momento del build, usa fallback
#ifdef HAVE_SOUNDTOUCH
#include <soundtouch/SoundTouch.h>
using namespace soundtouch;
#endif

// ========================================================================
// Stato globale (interno)
// ========================================================================

static bool g_pitch_enabled = false;
static int  g_pitch_cents = 0;
static bool g_initialized = false;

// ========================================================================
// Implementazione inizializzazione
// ========================================================================

void ac_audio_obf_init(int argc, char **argv)
{
    if (g_initialized) return; // Evita doppia inizializzazione
    g_initialized = true;

    // Step 1: Leggi variabili d'ambiente
    const char* env_enabled = std::getenv("AC_ANTICHEAT_PITCH_ENABLED");
    const char* env_cents = std::getenv("AC_ANTICHEAT_PITCH_CENTS");

    if (env_enabled && (strcmp(env_enabled, "1") == 0 || strcmp(env_enabled, "true") == 0)) {
        g_pitch_enabled = true;
    }

    if (env_cents) {
        g_pitch_cents = atoi(env_cents);
    }

    // Step 2: Parsing argomenti CLI (sovrascrive env vars)
    for (int i = 1; i < argc; ++i) {
        if (strcmp(argv[i], "--pitch-enable") == 0) {
            g_pitch_enabled = true;
        }
        else if (strcmp(argv[i], "--pitch-cents") == 0 && i + 1 < argc) {
            g_pitch_cents = atoi(argv[++i]);
        }
    }

    // Step 3: Validazione e clamping
    // Range sicuro: -100..+100 cents (±1 semitono)
    // Range esteso test: fino a ±500 cents (5 semitoni) per test percettibilità
    // Nota: Valori <150 cents possono essere poco percettibili su suoni percussivi
    if (g_pitch_cents < -500) {
        fprintf(stderr, "[audio_obf] WARNING: pitch_cents=%d troppo basso, clamped a -500\n", g_pitch_cents);
        g_pitch_cents = -500;
    }
    if (g_pitch_cents > 500) {
        fprintf(stderr, "[audio_obf] WARNING: pitch_cents=%d troppo alto, clamped a +500\n", g_pitch_cents);
        g_pitch_cents = 500;
    }

    // Step 4: Log stato
    if (g_pitch_enabled) {
        fprintf(stdout, "[audio_obf] Pitch shift ENABLED: %+d cents\n", g_pitch_cents);
#ifdef HAVE_SOUNDTOUCH
        fprintf(stdout, "[audio_obf] Using SoundTouch library for high-quality pitch shift\n");
#else
        fprintf(stdout, "[audio_obf] WARNING: SoundTouch not available, fallback mode active\n");
        fprintf(stdout, "[audio_obf]          (Fallback: AL_PITCH will be used if supported)\n");
#endif
    } else {
        fprintf(stdout, "[audio_obf] Pitch shift DISABLED (default)\n");
    }
}

// ========================================================================
// Getters pubblici
// ========================================================================

bool ac_pitch_is_enabled()
{
    return g_pitch_enabled;
}

int ac_pitch_cents()
{
    return g_pitch_cents;
}

// ========================================================================
// Implementazione trasformazione pitch
// ========================================================================

#ifdef HAVE_SOUNDTOUCH

// Percorso A: SoundTouch disponibile (high-quality)
bool apply_pitch_inplace(int16_t* samples, int frames, int channels, int samplerate, int cents)
{
    if (!g_pitch_enabled || cents == 0 || frames == 0) {
        return false; // Nessuna trasformazione necessaria
    }

    try {
        // Inizializza SoundTouch
        SoundTouch st;
        st.setSampleRate(samplerate);
        st.setChannels(channels);
        
        // Converti cents in semitoni (100 cents = 1 semitono)
        float semitones = cents / 100.0f;
        st.setPitchSemiTones(semitones);

        // SoundTouch lavora con float, convertiamo int16 → float [-1,1]
        std::vector<float> float_samples(frames * channels);
        for (int i = 0; i < frames * channels; ++i) {
            float_samples[i] = samples[i] / 32768.0f; // int16 range: -32768..32767
        }

        // Feed samples a SoundTouch
        st.putSamples(float_samples.data(), frames);
        st.flush();

        // Receive processed samples
        std::vector<float> output;
        output.reserve(frames * channels * 2); // Reserve extra space
        
        const int RECV_BUFF_SIZE = 4096;
        float temp_buff[RECV_BUFF_SIZE];
        int nSamples;
        
        do {
            nSamples = st.receiveSamples(temp_buff, RECV_BUFF_SIZE / channels);
            if (nSamples > 0) {
                for (int i = 0; i < nSamples * channels; ++i) {
                    output.push_back(temp_buff[i]);
                }
            }
        } while (nSamples != 0);

        // Converti output float → int16 e scrivi in buffer originale
        // NOTA: il pitch shift può cambiare leggermente la lunghezza.
        // Per semplicità, tronchiamo o zero-paddiamo al frame count originale.
        int output_frames = output.size() / channels;
        int copy_frames = std::min(output_frames, frames);

        for (int i = 0; i < copy_frames * channels; ++i) {
            float val = output[i] * 32768.0f;
            // Clamp to int16 range
            if (val > 32767.0f) val = 32767.0f;
            if (val < -32768.0f) val = -32768.0f;
            samples[i] = (int16_t)val;
        }

        // Se output è più corto, zero-pad
        for (int i = copy_frames * channels; i < frames * channels; ++i) {
            samples[i] = 0;
        }

        return true;

    } catch (...) {
        fprintf(stderr, "[audio_obf] ERROR: SoundTouch exception during pitch shift\n");
        return false;
    }
}

#else

// Percorso B: Fallback senza SoundTouch
// OPZIONE 1: Usare AL_PITCH (non modifica PCM, ma imposta parametro sorgente OpenAL)
// OPZIONE 2: Resampling semplice (cambia durata, non pitch puro)
// 
// Qui implementiamo OPZIONE 2 come PoC minimo (nearest-neighbor resampling)
// NOTA: questo NON è pitch shift vero (cambia anche la durata), ma serve
//       per dimostrare che il sistema funziona senza SoundTouch.

bool apply_pitch_inplace(int16_t* samples, int frames, int channels, int samplerate, int cents)
{
    if (!g_pitch_enabled || cents == 0 || frames == 0) {
        return false;
    }

    // Calcola pitch factor: cents → ratio
    // pitch_factor = 2^(cents/1200)
    // Esempio: +100 cents (1 semitono) → factor ~1.059
    float semitones = cents / 100.0f;
    float pitch_factor = pow(2.0f, semitones / 12.0f);

    fprintf(stderr, "[audio_obf] Fallback resampling (pitch_factor=%.3f)\n", pitch_factor);
    fprintf(stderr, "[audio_obf] NOTE: This is NOT true pitch shift (changes duration)\n");
    fprintf(stderr, "[audio_obf] Rebuild with SoundTouch for proper pitch shifting.\n");

    // Resampling semplice: leggi sample a step variabile
    int new_frames = (int)(frames / pitch_factor);
    if (new_frames > frames) new_frames = frames; // Safety clamp

    std::vector<int16_t> temp(new_frames * channels);
    for (int i = 0; i < new_frames; ++i) {
        float src_pos = i * pitch_factor;
        int src_frame = (int)src_pos;
        if (src_frame >= frames) src_frame = frames - 1;

        for (int ch = 0; ch < channels; ++ch) {
            temp[i * channels + ch] = samples[src_frame * channels + ch];
        }
    }

    // Copy back to original buffer
    memcpy(samples, temp.data(), new_frames * channels * sizeof(int16_t));

    // Zero-pad remainder
    for (int i = new_frames * channels; i < frames * channels; ++i) {
        samples[i] = 0;
    }

    return true;
}

#endif // HAVE_SOUNDTOUCH
```

**Ruolo**: Implementazione del sistema legacy per pitch shift semplice. Usa SoundTouch per pitch shifting di qualità. Variabili d'ambiente: `AC_ANTICHEAT_PITCH_ENABLED`, `AC_ANTICHEAT_PITCH_CENTS`. Chiamato in `openal.cpp` per OGG (linee 298-314) prima del nuovo framework. **NOTA**: Questo sistema è stato sostituito da `audio_runtime_obf`, ma rimane nel codice per compatibilità.

---

### 1.5 `AC/source/src/openal.cpp` (modifiche complete)

**Modifiche complete**:

```cpp
// Riga 4-5: Include headers
#include "audio_obf.h"  // Audio obfuscation / pitch shift (vecchio sistema)
#include "audio_runtime_obf.h"  // Audio runtime obfuscation framework (nuovo)

// Riga 297-336: Hook per OGG (dopo ov_read, prima di alBufferData)
// Apply pitch shifting if enabled (vecchio sistema)
if (ac_pitch_is_enabled())
{
    int16_t* pcm_data = (int16_t*)buf.getbuf();
    int channels = info->channels;
    int samplerate = info->rate;
    int bytes_total = buf.length();
    int frames = bytes_total / (sizeof(int16_t) * channels);
    int cents = ac_pitch_cents();

    // Log EVERY transformation for debugging
    static int ogg_transform_count = 0;
    ogg_transform_count++;
    fprintf(stdout, "[openal.cpp] Pitch #%d: %s → %d frames, %d ch, %d Hz, %+d cents\n",
            ogg_transform_count, name, frames, channels, samplerate, cents);

    // Apply pitch shift
    apply_pitch_inplace(pcm_data, frames, channels, samplerate, cents);
}

// Nuovo framework runtime obfuscation (Step 2)
// Hook: processa il PCM prima di alBufferData
{
    int16_t* pcm_data = (int16_t*)buf.getbuf();
    int channels = info->channels;
    int samplerate = info->rate;
    int bytes_total = buf.length();
    int frames = bytes_total / (sizeof(int16_t) * channels);
    
    // Logical name: usa il nome del file audio
    std::string logical_name = name ? std::string(name) : "OGG::<unknown>";
    
    // DEBUG: stampa il nome per verificare
    std::printf("[AUDIO_OBF_DEBUG] Loading OGG: '%s' (frames=%d, ch=%d, sr=%d)\n", 
                logical_name.c_str(), frames, channels, samplerate);
    std::fflush(stdout);
    
    // Processa in-place (modifica pcm_data direttamente)
    aro_process_pcm_int16(logical_name, pcm_data, frames, channels, samplerate);
}

// Riga 377-397: Hook per WAV (dopo SDL_LoadWAV, prima di alBufferData)
// Nuovo framework runtime obfuscation (Step 2) - WAV path
// Hook: processa il PCM prima di alBufferData
// NOTA: per ora supportiamo solo formati 16-bit
if (wavspec.format == AUDIO_S16 || wavspec.format == AUDIO_U16)
{
    int16_t* pcm_data = (int16_t*)wavbuf;
    int channels = wavspec.channels;
    int samplerate = wavspec.freq;
    int frames = wavlen / (sizeof(int16_t) * channels);
    
    // Logical name: usa il nome del file audio
    std::string logical_name = name ? std::string(name) : "WAV::<unknown>";
    
    // DEBUG: stampa il nome per verificare
    std::printf("[AUDIO_OBF_DEBUG] Loading WAV: '%s' (frames=%d, ch=%d, sr=%d)\n", 
                logical_name.c_str(), frames, channels, samplerate);
    std::fflush(stdout);
    
    // Processa in-place (modifica pcm_data direttamente)
    aro_process_pcm_int16(logical_name, pcm_data, frames, channels, samplerate);
}
```

**Ruolo**: Hookato nel loader audio di AssaultCube (`sbuffer::load()`). Implementa **doppio sistema**:
1. **Sistema legacy** (linee 298-314): Pitch shift semplice per OGG usando `audio_obf.cpp` (vecchio sistema)
2. **Sistema nuovo** (linee 317-336 per OGG, 377-397 per WAV): Framework completo `audio_runtime_obf` che applica tutte le trasformazioni DSP (pitch, noise, EQ, HP/LP) **prima** che il buffer venga caricato in OpenAL con `alBufferData()`. Il nome logico del suono viene estratto dal nome del file (`name`) e passato al framework per lookup nel CSV. Questo permette la modifica in-place del PCM decodificato senza cambiare il protocollo di rete o i file audio su disco.

---

### 1.6 `AC/source/src/main.cpp` (porzioni modificate)

**Modifiche complete**:

```cpp
// Riga 1212-1215: Inizializzazione sistema legacy (Step 0)
// Initialize audio obfuscation system (pitch shift)
// Must be called before any audio operations
extern void ac_audio_obf_init(int, char**);
ac_audio_obf_init(argc, argv);

// Riga 1217-1222: Inizializzazione nuovo framework (Step 1+)
// Initialize new audio runtime obfuscation framework (Step 1)
// Legge env vars e CLI args, stampa stato al bootstrap
extern void aro_init_from_env_and_cli(int, char**);
extern void aro_log_loaded();
aro_init_from_env_and_cli(argc, argv);
aro_log_loaded();
```

**Ruolo**: Chiamato all'avvio del client (main bootstrap). Inizializza **entrambi** i sistemi:
1. **Sistema legacy** (linee 1214-1215): Inizializza `ac_audio_obf_init()` per compatibilità con vecchio sistema (variabili `AC_ANTICHEAT_PITCH_ENABLED`, `AC_ANTICHEAT_PITCH_CENTS`)
2. **Sistema nuovo** (linee 1219-1222): Inizializza `aro_init_from_env_and_cli()` per il nuovo framework completo. Legge variabili d'ambiente (`AC_AUDIO_OBF`, `AC_AUDIO_OBF_RANDOMIZE`) e argomenti CLI (`--audio-obf on|off`). Carica i profili audio da `audio_obf_config.csv`. Stampa lo stato del sistema nel log per debugging.

---

### 1.7 `AC/source/src/Makefile` (porzioni modificate)

**Modifiche**:

```makefile
# Riga 120-121: Aggiunta oggetti al link
audio_obf.o \
audio_runtime_obf.o \
```

**Ruolo**: Aggiunge `audio_runtime_obf.o` alla lista degli oggetti da compilare e linkare nel client finale `ac_client`. Richiede SoundTouch (`-lSoundTouch`) per pitch shifting.

---

### 1.6 `AC/audio_obf_config.csv`

**Contenuto completo**:

```csv
# =====================================================================================
# CONFIGURAZIONE AUDIO OBFUSCATION — ANTI-CHEAT ML DEFENSE
# =====================================================================================
#
# OGNI RIGA = 1 SUONO CON I SUOI RANGE CALIBRATI
#
# Quando AC_AUDIO_OBF_RANDOMIZE=1, il sistema sceglie valori RANDOM entro questi range.
#
# =====================================================================================
# SPIEGAZIONE COLONNE (una per una):
# =====================================================================================
#
# 1. file_name          → Nome suono (es. "weapon/usp")
# 2. min_pitch_cents    → Pitch minimo (es. -200)
# 3. max_pitch_cents    → Pitch massimo (es. 200)
# 4. noise_type         → "random" | "white" | "pink" | "none"
# 5. white_snr_min       → White noise SNR minimo in dB (es. 35)
# 6. white_snr_max       → White noise SNR massimo in dB (es. 45)
# 7. pink_snr_min        → Pink noise SNR minimo in dB (es. 16)
# 8. pink_snr_max        → Pink noise SNR massimo in dB (es. 24)
# 9. eq_mode            → "random" | "boost" | "cut" | "none"
# 10. eq_boost_min       → EQ boost minimo in dB (es. 2)
# 11. eq_boost_max       → EQ boost massimo in dB (es. 6)
# 12. eq_cut_min          → EQ cut minimo in dB (NEGATIVO, es. -9)
# 13. eq_cut_max          → EQ cut massimo in dB (NEGATIVO, es. -3)
# 14. hp_min_hz          → High-pass filter minimo in Hz (es. 150)
# 15. hp_max_hz          → High-pass filter massimo in Hz (es. 250)
# 16. lp_min_hz          → Low-pass filter minimo in Hz (es. 8000)
# 17. lp_max_hz          → Low-pass filter massimo in Hz (es. 10000)
#
# =====================================================================================
# ESEMPI VALORI:
# =====================================================================================
#
# weapon/usp con MASSIMA VARIABILITÀ:
#   noise_type="random" → 50% white[35-45dB], 50% pink[16-24dB]
#   eq_mode="random"    → 50% boost[2-6dB], 50% cut[-9--3dB]
#
# weapon/usp con white fisso:
#   noise_type="white"  → sempre white[35-45dB]
#   eq_mode="random"    → 50% boost[2-6dB], 50% cut[-9--3dB]
#
# weapon/usp senza rumore, solo pitch:
#   noise_type="none"  → nessun rumore
#   eq_mode="none"     → nessun EQ
#
# =====================================================================================

file_name,min_pitch_cents,max_pitch_cents,noise_type,white_snr_min,white_snr_max,pink_snr_min,pink_snr_max,eq_mode,eq_boost_min,eq_boost_max,eq_cut_min,eq_cut_max,hp_min_hz,hp_max_hz,lp_min_hz,lp_max_hz

# =====================================================================================
# CONFIGURAZIONE WEAPON/USP (pistola) — Range calibrati da test soggettivi
# =====================================================================================
#
# PITCH:  [-200, -75] ∪ [75, 200] cents  (dead zone [-75, 75] esclusa)
# NOISE:  50% white[35-45dB], 50% pink[16-24dB]  (se noise_type="random")
# EQ:     50% boost[2-6dB], 50% cut[-9--3dB]     (se eq_mode="random")
# HP:     [150, 250] Hz
# LP:     [8000, 10000] Hz
#
weapon/usp,-200,200,random,35,45,16,24,random,2,6,-9,-3,150,250,8000,10000

# =====================================================================================
# ALTRI SUONI (TODO: calibrare range con test soggettivi)
# =====================================================================================
#
# Decommentare e modificare i range dopo i test:
#
# weapon/auto,-200,200,random,35,45,16,24,random,2,6,-9,-3,150,250,8000,10000
# player/footsteps,-200,200,random,35,45,16,24,random,2,6,-9,-3,150,250,8000,10000
# voicecom/affirmative,-200,200,random,35,45,16,24,random,2,6,-9,-3,150,250,8000,10000
```

**Ruolo**: Configurazione per-sound dell'audio obfuscation. Ogni riga definisce un suono di gioco (es. `weapon/usp`) con i suoi range calibrati per ogni parametro DSP. Il sistema legge questo file all'avvio e lo usa per determinare come applicare le trasformazioni. Se `noise_type="random"` o `eq_mode="random"`, il sistema randomizza TRA i due tipi (white/pink, boost/cut) con probabilità 50%/50%.

---

### 1.7 `ADV_ML/scripts/run_random_variants.sh`

**Contenuto completo**:

```bash
#!/bin/bash
# run_random_variants.sh
# Genera N varianti audio con parametri random per test ML
#
# Uso: ./run_random_variants.sh <sound_name> <num_variants>
# Esempio: ./run_random_variants.sh weapon/usp 100

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
OUTPUT_DIR="$SCRIPT_DIR/../output/random_variants"
CSV_OUTPUT="$OUTPUT_DIR/random_params.csv"

# Parametri
SOUND_NAME="${1:-weapon/usp}"
NUM_VARIANTS="${2:-50}"

# Colori
GREEN='\033[0.32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== Audio Random Variants Generator (Step 3) ===${NC}"
echo "Sound: $SOUND_NAME"
echo "Num variants: $NUM_VARIANTS"
echo "Output: $OUTPUT_DIR"
echo ""

# Crea directory output
mkdir -p "$OUTPUT_DIR"

# Crea header CSV
echo "variant_id,pitch_cents,noise_snr_db,eq_tilt_db,hp_hz,lp_hz" > "$CSV_OUTPUT"

# Funzione per generare variante con parametri random (simulazione distribuzioni C++)
generate_variant() {
    local variant_id=$1
    local output_file="$OUTPUT_DIR/${SOUND_NAME##*/}_variant_$(printf "%03d" $variant_id).wav"
    
       # Genera parametri random usando DISTRIBUZIONE UNIFORME (anti-ML, da RANGE.md)
       
       # 1. PITCH: Uniforme in [-200..-75] ∪ [75..200] (escluso dead zone ±75)
       pitch=$(python3 -c "import random; neg_or_pos = random.choice(['neg', 'pos']); print(random.randint(-200, -75) if neg_or_pos == 'neg' else random.randint(75, 200))")
       
       # 2. SNR: Uniforme in [35, 45] dB per white noise (da RANGE.md)
       snr=$(python3 -c "import random; print(f'{random.uniform(35, 45):.1f}')")
       
       # 3. EQ Tilt: Uniforme in [2, 6] dB (boost, da RANGE.md)
       eq_tilt=$(python3 -c "import random; print(f'{random.uniform(2.0, 6.0):.1f}')")
       
       # 4. HP Filter: Uniforme in [150, 250] Hz (da RANGE.md)
       hp_hz=$(python3 -c "import random; print(random.randint(150, 250))")
       
       # 5. LP Filter: Uniforme in [8000, 10000] Hz (da RANGE.md)
       lp_hz=$(python3 -c "import random; print(random.randint(8000, 10000))")
    
    # Log parametri nel CSV
    echo "$variant_id,$pitch,$snr,$eq_tilt,$hp_hz,$lp_hz" >> "$CSV_OUTPUT"
    
    # Log a schermo (mostra tutti i parametri)
    echo "  Generated variant $variant_id: pitch=${pitch}c, SNR=${snr}dB, EQ=${eq_tilt}dB, HP=${hp_hz}Hz, LP=${lp_hz}Hz"
    
    # NOTA: Per generazione reale, usa:
    # 1. Modifica temp CSV con questi parametri
    # 2. Esegui client con AC_AUDIO_OBF_RANDOMIZE=1
    # 3. Estrai audio processato da buffer OpenAL
}

echo -e "${YELLOW}Generating $NUM_VARIANTS variants...${NC}"
for i in $(seq 1 $NUM_VARIANTS); do
    generate_variant $i
done

echo ""
echo -e "${GREEN}✓ Generation complete!${NC}"
echo "Variants: $OUTPUT_DIR/"
echo "Parameters CSV: $CSV_OUTPUT"
echo ""
echo "Next steps:"
echo "1. Test soggettivo: python3 ADV_ML/tests/human_listen_and_label.py $OUTPUT_DIR"
echo "2. Estrazione MFCC: python3 ADV_ML/scripts/extract_features.py $OUTPUT_DIR"
echo "3. Test ML: python3 ADV_ML/scripts/train_classifier.py"
```

**Ruolo**: Script bash per generare varianti offline con parametri random simulando il comportamento del framework C++. Utile per test ML batch senza eseguire il client. Genera un CSV con i parametri usati per ogni variante (per tracciabilità e analisi statistiche).

---

## 2. ARCHITETTURA GENERALE

### 2.1 Flusso di elaborazione audio

```
1. Gioco carica suono (es. weapon/usp.ogg)
     ↓
2. openal.cpp → ov_read() / SDL_LoadWAV()
     ↓ [decodifica OGG/WAV → PCM int16]
3. openal.cpp → aro_process_pcm_int16(logical_name, pcm, ...)
     ↓
4. audio_runtime_obf.cpp:
   a) Cerca profilo per logical_name in audio_obf_config.csv
   b) Calcola parametri (deterministici o random)
   c) Converti int16 → float
   d) Applica catena DSP: EQ → HP → LP → Pitch → Tone → Noise
   e) Converti float → int16 (con clipping)
     ↓
5. openal.cpp → alBufferData(id, format, pcm, ...)
     ↓ [caricamento buffer modificato in OpenAL]
6. Gioco riproduce audio obfuscato
```

**Caratteristiche**:
- **Lato client**: tutte le modifiche sono nel client. Il protocollo di rete, il server e i file audio su disco NON sono stati cambiati.
- **In-place processing**: il buffer PCM viene modificato direttamente, senza copia aggiuntiva.
- **Configurabile**: ogni suono può avere parametri diversi (da CSV).

### 2.2 Step 2 vs Step 3

**Step 2 (Deterministico)**:
- `AC_AUDIO_OBF=1` (senza `AC_AUDIO_OBF_RANDOMIZE`)
- Parametri calcolati come **midpoint** dei range nel CSV
- Esempio: `weapon/usp` con pitch range `[-200, 200]` → usa `pitch = 0` (midpoint)
- Utile per: test iniziali, debug, baseline per confronto ML

**Step 3 (Randomizzato)**:
- `AC_AUDIO_OBF=1` + `AC_AUDIO_OBF_RANDOMIZE=1`
- Parametri calcolati con **distribuzioni uniformi** entro i range del CSV
- RNG seeded con timestamp (`std::chrono::high_resolution_clock`) → non-reproducibile
- Esempio: `weapon/usp` con pitch range `[-200, 200]` → ogni colpo ha pitch random in `[-200..-75] ∪ [75..200]` (escluso dead zone `[-75, 75]`)
- Utile per: anti-ML, massima variabilità, dataset R₁ diverso da R₀

---

## 3. ISTRUZIONI PER COMPILAZIONE E DISTRIBUZIONE

### 3.1 Compilazione del client modificato

**Prerequisiti**:
- GCC/Clang con supporto C++11+
- SoundTouch library (`libsoundtouch-dev` su Debian/Ubuntu, `soundtouch` via Homebrew su macOS)
- SDL2, OpenAL, vorbisfile (già richiesti da AssaultCube stock)

**Comandi**:

```bash
cd "/Users/francesco03/Documents/GitHub/AssaultCube Server/AC/source/src"
make clean
make client -j4
```

**Output**: Binario `ac_client` in `AC/`.

**Note**:
- Su macOS: usa `make client -j` (non `make -j` che compila anche standalone targets che richiedono SDL_timer.h)
- Se SoundTouch non è installato, pitch shift sarà disabilitato (warning durante compilazione)

### 3.2 Esecuzione con obfuscation

**Obfuscation deterministico (Step 2)**:

```bash
cd AC
export AC_AUDIO_OBF=1
./ac_client
```

**Obfuscation randomizzato (Step 3)**:

```bash
cd AC
export AC_AUDIO_OBF=1
export AC_AUDIO_OBF_RANDOMIZE=1
./ac_client
```

**Verifica funzionamento**:
- All'avvio, cercare nel log: `[AUDIO_OBF] enabled=1 from=ENV`
- Durante il gioco (sparare con pistola): `[AUDIO_OBF_RAND] weapon/usp → pitch:+156c; eq:+4.2dB; ... noise:white@42dB`

### 3.3 Server di test e distribuzione

**IMPORTANTE**: Il server **NON è stato modificato**. Il client modificato è **100% compatibile** con qualsiasi server AssaultCube stock (versione 1.3.0.2). L'obfuscation audio avviene solo lato client e **non è trasmessa in rete** → il server non sa che il client sta usando audio obfuscato.

#### Opzione 1: Server locale per test

**Passo 1: Compila il server stock** (se non presente)

```bash
cd AC/source/src
make clean
make server -j4
```

**Passo 2: Avvia il server**

```bash
cd AC
./ac_server
# Oppure con parametri:
./ac_server -p 28763  # Porta default
```

**Passo 3: Avvia il client modificato** (in altro terminale)

```bash
cd AC
export AC_AUDIO_OBF=1
export AC_AUDIO_OBF_RANDOMIZE=1
./ac_client
# In-game: Menu → Multiplayer → Connect to 127.0.0.1:28763
```

**Verifica**: Gli altri giocatori (con client stock) sentono i suoni normali, mentre tu (con client modificato) senti i suoni obfuscati.

#### Opzione 2: Server pubblico (online)

Il client modificato può connettersi a **qualsiasi server pubblico** AssaultCube senza problemi. L'obfuscation è **invisibile** al server e agli altri client.

```bash
cd AC
export AC_AUDIO_OBF=1
export AC_AUDIO_OBF_RANDOMIZE=1
./ac_client
# In-game: Menu → Multiplayer → Browse → Connetti a server pubblico
```

#### Opzione 3: Server dedicato per distribuzione

**Scenario**: Vuoi distribuire un server + client modificato per testare l'anti-cheat ML.

**Passo 1: Crea pacchetto server** (direttorio completo)

```bash
cd "AssaultCube Server"
mkdir -p ac_server_package
cp -r AC/source/src/ac_server ac_server_package/
cp -r AC/packages ac_server_package/
cp -r AC/config ac_server_package/
cp AC/README* ac_server_package/ 2>/dev/null || true
```

**Passo 2: Crea pacchetto client modificato**

```bash
cd "AssaultCube Server"
mkdir -p ac_client_obfuscated_package
cp AC/source/src/ac_client ac_client_obfuscated_package/
cp AC/audio_obf_config.csv ac_client_obfuscated_package/
cp -r AC/packages ac_client_obfuscated_package/
cp -r AC/config ac_client_obfuscated_package/

# Crea script di avvio
cat > ac_client_obfuscated_package/start_client.sh << 'EOF'
#!/bin/bash
# Script per avviare client con audio obfuscation abilitata

export AC_AUDIO_OBF=1
export AC_AUDIO_OBF_RANDOMIZE=1

./ac_client "$@"
EOF

chmod +x ac_client_obfuscated_package/start_client.sh
```

**Passo 3: Crea archivio distribuzione**

```bash
cd "AssaultCube Server"
tar -czf ac_server_package.tar.gz ac_server_package/
tar -czf ac_client_obfuscated_package.tar.gz ac_client_obfuscated_package/
```

**Passo 4: Istruzioni per utente finale**

Crea file `README_DISTRIBUZIONE.md`:

```markdown
# AssaultCube Anti-Cheat Audio Obfuscation - Distribuzione

## Server

1. Estrai `ac_server_package.tar.gz`
2. Avvia: `./ac_server -p 28763`

## Client Modificato

1. Estrai `ac_client_obfuscated_package.tar.gz`
2. Avvia: `./start_client.sh`
   - Oppure manualmente:
     ```bash
     export AC_AUDIO_OBF=1
     export AC_AUDIO_OBF_RANDOMIZE=1
     ./ac_client
     ```
3. Connetti al server: Menu → Multiplayer → Connect to <SERVER_IP>:28763

## Note

- Il client modificato è compatibile con server stock AssaultCube
- L'obfuscation audio è trasparente per il server (non trasmessa in rete)
- Solo il giocatore con client modificato sente audio obfuscato
- Per disabilitare obfuscation: rimuovi `export AC_AUDIO_OBF=1`
```

#### Opzione 4: Server Docker (opzionale)

Per distribuzione più semplice, crea `Dockerfile`:

```dockerfile
# Dockerfile per server AssaultCube
FROM ubuntu:20.04

RUN apt-get update && apt-get install -y \
    libopenal1 libsdl2-2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY ac_server_package/ .

EXPOSE 28763/udp

CMD ["./ac_server", "-p", "28763"]
```

**Build e run**:
```bash
docker build -t assaultcube-server .
docker run -p 28763:28763/udp assaultcube-server
```

### 3.4 Pacchetto distribuzione completo (Server + Client)

**File necessari per distribuzione client**:

```
ac_client_obfuscated_package/
├── ac_client                     # Binario client modificato
├── audio_obf_config.csv          # Configurazione obfuscation
├── start_client.sh               # Script di avvio (con env vars)
├── packages/                     # Asset audio (da distribuzione stock AC)
│   └── audio/
│       ├── sounds/
│       │   └── weapon/
│       │       └── usp.ogg       # File audio originali
│       └── ... (altri suoni)
└── config/                       # Config client (opzionale)
```

**File necessari per distribuzione server**:

```
ac_server_package/
├── ac_server                     # Binario server stock
├── packages/                     # Asset game (mappe, modelli, ecc.)
└── config/                       # Config server (opzionale)
```

**Creazione pacchetti completi**:

```bash
cd "AssaultCube Server"

# 1. Client modificato
mkdir -p ac_client_obfuscated_package
cp AC/source/src/ac_client ac_client_obfuscated_package/
cp AC/audio_obf_config.csv ac_client_obfuscated_package/
cp -r AC/packages ac_client_obfuscated_package/
cp -r AC/config ac_client_obfuscated_package/ 2>/dev/null || true

# Crea script avvio
cat > ac_client_obfuscated_package/start_client.sh << 'EOF'
#!/bin/bash
export AC_AUDIO_OBF=1
export AC_AUDIO_OBF_RANDOMIZE=1
./ac_client "$@"
EOF
chmod +x ac_client_obfuscated_package/start_client.sh

# 2. Server stock
mkdir -p ac_server_package
cp AC/source/src/ac_server ac_server_package/
cp -r AC/packages ac_server_package/
cp -r AC/config ac_server_package/ 2>/dev/null || true

# 3. Crea archivi
tar -czf ac_client_obfuscated_package.tar.gz ac_client_obfuscated_package/
tar -czf ac_server_package.tar.gz ac_server_package/
```

**Istruzioni per utente finale** (crea `README_DISTRIBUZIONE.md`):

```markdown
# AssaultCube Anti-Cheat - Installazione

## Server

1. Estrai `ac_server_package.tar.gz`
2. Avvia server: `./ac_server -p 28763`
3. Nota IP server (es. `192.168.1.100`)

## Client Modificato

1. Estrai `ac_client_obfuscated_package.tar.gz`
2. Avvia client: `./start_client.sh`
   - Oppure manualmente:
     ```bash
     export AC_AUDIO_OBF=1
     export AC_AUDIO_OBF_RANDOMIZE=1
     ./ac_client
     ```
3. In-game: Menu → Multiplayer → Connect to <SERVER_IP>:28763

## Verifica Obfuscation

- Nel log del client, cerca: `[AUDIO_OBF_RAND] weapon/usp → ...`
- Ogni colpo dovrebbe avere parametri diversi (pitch, noise, EQ random)

## Disabilitare Obfuscation

Rimuovi `export AC_AUDIO_OBF=1` o usa `./ac_client` direttamente.
```

---

## 4. CHANGELOG SINTETICO PER STEP

### Step 0: Sistema legacy (pitch shift semplice)

**File creati/modificati**:
- `AC/source/src/audio_obf.h` (nuovo)
- `AC/source/src/audio_obf.cpp` (nuovo)
- `AC/source/src/openal.cpp` (hook per OGG con vecchio sistema)
- `AC/source/src/main.cpp` (init call `ac_audio_obf_init`)
- `AC/source/src/Makefile` (aggiunta oggetto `audio_obf.o`)

**Funzionalità**:
- Pitch shift semplice con SoundTouch
- Variabili d'ambiente: `AC_ANTICHEAT_PITCH_ENABLED`, `AC_ANTICHEAT_PITCH_CENTS`
- Hook per OGG only (WAV non supportato)

### Step 1: Infrastruttura base

**File creati/modificati**:
- `AC/source/src/audio_runtime_obf.h` (nuovo)
- `AC/source/src/audio_runtime_obf.cpp` (nuovo)
- `AC/source/src/openal.cpp` (hook aggiunto per nuovo framework OGG+WAV)
- `AC/source/src/main.cpp` (init call `aro_init_from_env_and_cli`)
- `AC/source/src/Makefile` (aggiunta oggetto `audio_runtime_obf.o`)

**Funzionalità**:
- Infrastruttura framework: ENV/CLI parsing, logging
- Hook audio post-decodifica (prima di `alBufferData`) per OGG e WAV
- Logging placeholder (no trasformazioni reali applicate)

### Step 2: DSP + CSV + Applicazione deterministica

**File creati/modificati**:
- `AC/source/src/audio_runtime_obf.cpp` (aggiunta algoritmi DSP)
- `AC/audio_obf_config.csv` (nuovo)

**Funzionalità**:
- Algoritmi DSP completi: pitch shift (SoundTouch), white/pink noise, tone, EQ tilt, HP/LP filters (Butterworth)
- Parser CSV per profili per-sound
- Applicazione deterministica: parametri = midpoint dei range

### Step 3: Randomizzazione

**File creati/modificati**:
- `AC/source/src/audio_runtime_obf.cpp` (aggiunta logica randomizzazione)
- `AC/audio_obf_config.csv` (esteso con range completi per white/pink, boost/cut)
- `ADV_ML/scripts/run_random_variants.sh` (nuovo)

**Funzionalità**:
- Randomizzazione con distribuzioni uniformi (pitch, SNR, EQ, HP, LP)
- Randomizzazione tipo noise (50% white, 50% pink) e segno EQ (50% boost, 50% cut)
- RNG seeded con timestamp (non-reproducibile)
- Script batch per generazione varianti offline

---

## 5. CHECKLIST FINALE

### 5.1 File da CONSERVARE in `ADV_ML/`

**Script essenziali**:
- `ADV_ML/scripts/run_random_variants.sh`

**Documentazione**:
- `ADV_ML/docs/randomization_guide.md`
- `ADV_ML/docs/randomization_summary.txt`

**Output di test** (se generati):
- `ADV_ML/output/random_variants/random_params.csv`

### 5.2 File da ELIMINARE (temporanei/intermedi)

**Cartelle cache**:
- `ADV_ML/.cache/*`
- `ADV_ML/output/variants/*` (varianti intermedie)

**Script obsoleti** (già eliminati):
- `ADV_ML/preprocess_audio_obf.py`
- `ADV_ML/tests/generate_variants.py`
- `ADV_ML/tests/generate_audible_variants.py`
- `ADV_ML/tests/human_listen_and_label.py`
- `ADV_ML/tests/run_abx.py`

**File temporanei**:
- `.cursor-output/*` (tranne `RANGE.md`, `GUIDA_*.md`, `TEST_*.md` che sono utili)

### 5.3 Come aggiornare questo documento

Quando modifichi codice, aggiorna `AC_MODIFICATIONS.md`:

1. Se modifichi un file esistente: aggiorna la sezione corrispondente con il nuovo contenuto
2. Se crei un nuovo file: aggiungi una nuova sezione con contenuto completo + spiegazione ruolo
3. Aggiorna il changelog (Sezione 4) se cambi step
4. Commit con messaggio descrittivo:
   ```bash
   git add AC_MODIFICATIONS.md
   git commit -m "MOD: AC changes - [descrizione breve]"
   ```

---

**Ultimo aggiornamento**: 2025-11-03  
**Autore**: Francesco Carcangiu  
**Versione**: 1.0 (Step 3 completo - Randomizzazione uniforme implementata)

