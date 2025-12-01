# Runtime Audio Obfuscation Framework - Step 1 Summary

**Data:** 29 Ottobre 2025  
**Autore:** Francesco Carcangiu  
**Versione:** Step 1 (Infrastruttura + Logging)

---

## 📋 Obiettivo Step 1

Creare un framework runtime per applicare trasformazioni audio al PCM già decodificato (OGG/WAV) **prima** di `alBufferData`, con:

- ✅ Infrastruttura pulita e modulare
- ✅ Logging chiaro e parsabile per ogni suono processato
- ✅ Supporto ENV vars e CLI args per ON/OFF
- ✅ Placeholder per trasformazioni future (pitch, noise, tone)
- ✅ Step 1: **SOLO LOGGING** (no modifiche al buffer, no-op)

Gli step successivi implementeranno le trasformazioni reali.

---

## 📁 Nuovi File Creati

### 1. `AC/source/src/audio_runtime_obf.h`

**Header pubblico** che definisce:

- **`struct ARO_Profile`**: Configurazione per le trasformazioni
  - `enabled`: flag globale ON/OFF
  - `use_pitch`, `pitch_cents`: pitch shifting (placeholder Step 1)
  - `use_noise`, `noise_snr_db`: noise injection (placeholder futuro)
  - `use_tone`, `tone_freq_hz`, `tone_level_db`: tone injection (placeholder futuro)

- **API pubblica**:
  - `aro_init_from_env_and_cli(argc, argv)` → Legge ENV e CLI, inizializza sistema
  - `aro_set_enabled(bool)` → Abilita/disabilita runtime
  - `aro_is_enabled()` → Check stato
  - `aro_process_pcm_int16(...)` → Processa buffer PCM (Step 1: solo log)
  - `aro_log_loaded()` → Stampa stato iniziale
  - `aro_log_apply(name, profile)` → Log per singolo suono

### 2. `AC/source/src/audio_runtime_obf.cpp`

**Implementazione** con:

- Stato globale interno (`g_profile`, `g_config_source`, `g_initialized`)
- Parsing ENV: `AC_AUDIO_OBF=0|1`
- Parsing CLI: `--audio-obf on|off` (precedenza su ENV)
- Helper per conversione `int16 ↔ float` (pronti per step futuri)
- **Step 1**: `aro_process_pcm_int16()` è **no-op** (solo logging, nessuna modifica al buffer)

---

## 🔗 Punti di Hook

### Hook 1: **Inizializzazione** in `main.cpp`

**File:** `AC/source/src/main.cpp`  
**Funzione:** `main(int argc, char **argv)`  
**Linee:** ~1217-1222

```cpp
// Initialize new audio runtime obfuscation framework (Step 1)
// Legge env vars e CLI args, stampa stato al bootstrap
extern void aro_init_from_env_and_cli(int, char**);
extern void aro_log_loaded();
aro_init_from_env_and_cli(argc, argv);
aro_log_loaded();
```

**Cosa fa:**
- Chiama `aro_init_from_env_and_cli()` per leggere configurazione da ENV/CLI
- Chiama `aro_log_loaded()` per stampare stato iniziale a console

**Output atteso:**
```
[AUDIO_OBF] enabled=0
```
oppure (se abilitato):
```
[AUDIO_OBF] enabled=1 from=ENV use_pitch=0 use_noise=0 use_tone=0
```

---

### Hook 2: **Pipeline OGG** in `openal.cpp`

**File:** `AC/source/src/openal.cpp`  
**Funzione:** `sbuffer::load(bool trydl)`  
**Linee:** ~317-332 (dopo decodifica OGG, prima di `alBufferData`)

```cpp
// Nuovo framework runtime obfuscation (Step 1) - OGG path
// Hook: processa il PCM prima di alBufferData
{
    int16_t* pcm_data = (int16_t*)buf.getbuf();
    int channels = info->channels;
    int samplerate = info->rate;
    int bytes_total = buf.length();
    int frames = bytes_total / (sizeof(int16_t) * channels);
    
    std::string logical_name = name ? std::string(name) : "OGG::<unknown>";
    
    // Processa (per Step 1: solo log, nessuna modifica)
    aro_process_pcm_int16(logical_name, pcm_data, frames, channels, samplerate);
}
```

**Cosa fa:**
- Estrae metadata del buffer PCM (frames, channels, samplerate)
- Chiama `aro_process_pcm_int16()` che logga l'operazione
- **Step 1**: Il buffer NON viene modificato (no-op)

**Output atteso (se enabled=1):**
```
[AUDIO_OBF] player/footsteps.ogg → pitch:+0 cents, noise:SNR=0.0 dB, tone:0 Hz @ 0.0 dB
```

---

### Hook 3: **Pipeline WAV** in `openal.cpp`

**File:** `AC/source/src/openal.cpp`  
**Funzione:** `sbuffer::load(bool trydl)`  
**Linee:** ~373-388 (dopo caricamento WAV, prima di `alBufferData`)

```cpp
// Nuovo framework runtime obfuscation (Step 1) - WAV path
// Hook: processa il PCM prima di alBufferData
if (wavspec.format == AUDIO_S16 || wavspec.format == AUDIO_U16)
{
    int16_t* pcm_data = (int16_t*)wavbuf;
    int channels = wavspec.channels;
    int samplerate = wavspec.freq;
    int frames = wavlen / (sizeof(int16_t) * channels);
    
    std::string logical_name = name ? std::string(name) : "WAV::<unknown>";
    
    // Processa (per Step 1: solo log, nessuna modifica)
    aro_process_pcm_int16(logical_name, pcm_data, frames, channels, samplerate);
}
```

**Cosa fa:**
- Come per OGG, ma per file WAV
- **Nota:** Supporta solo formati 16-bit (S16/U16) per Step 1

**Output atteso (se enabled=1):**
```
[AUDIO_OBF] weapon/shotgun.wav → pitch:+0 cents, noise:SNR=0.0 dB, tone:0 Hz @ 0.0 dB
```

---

## 🛠️ Build System

**File modificato:** `AC/source/src/Makefile`  
**Linea:** ~121

Aggiunto `audio_runtime_obf.o` alla lista `CLIENT_OBJS`:

```makefile
CLIENT_OBJS= \
	...
	audio_obf.o \
	audio_runtime_obf.o \
	bot/bot.o \
	...
```

**Come compilare:**

```bash
cd AC/source/src
make clean
make client
```

Il nuovo modulo `audio_runtime_obf.cpp` verrà compilato automaticamente.

---

## 🚀 Come Abilitare/Disabilitare

### Metodo 1: Variabile d'Ambiente (ENV)

```bash
# Disabilitato (default)
./ac_client

# Abilitato
AC_AUDIO_OBF=1 ./ac_client
```

### Metodo 2: Argomento CLI

```bash
# Abilitato
./ac_client --audio-obf on

# Disabilitato (esplicito)
./ac_client --audio-obf off
```

### Precedenza

**CLI > ENV > default (OFF)**

Se passi `--audio-obf on` alla CLI, sovrascrive qualsiasi `AC_AUDIO_OBF` ENV var.

---

## 📊 Esempi di Log a Runtime

### Caso 1: Sistema Disabilitato (default)

```bash
$ ./ac_client
[AUDIO_OBF] enabled=0
```

**Comportamento:** Nessun log aggiuntivo per i suoni. Il framework è completamente inattivo.

---

### Caso 2: Sistema Abilitato (ENV)

```bash
$ AC_AUDIO_OBF=1 ./ac_client
[AUDIO_OBF] enabled=1 from=ENV use_pitch=0 use_noise=0 use_tone=0
...
[AUDIO_OBF] player/footsteps.ogg → pitch:+0 cents, noise:SNR=0.0 dB, tone:0 Hz @ 0.0 dB
[AUDIO_OBF] weapon/shotgun.ogg → pitch:+0 cents, noise:SNR=0.0 dB, tone:0 Hz @ 0.0 dB
[AUDIO_OBF] ambience/wind.ogg → pitch:+0 cents, noise:SNR=0.0 dB, tone:0 Hz @ 0.0 dB
...
```

**Comportamento:** Log di ogni suono caricato, ma nessuna modifica al buffer (Step 1).

---

### Caso 3: Sistema Abilitato (CLI, precedenza su ENV)

```bash
$ AC_AUDIO_OBF=0 ./ac_client --audio-obf on
[AUDIO_OBF] enabled=1 from=CLI use_pitch=0 use_noise=0 use_tone=0
...
```

**Comportamento:** La CLI ha precedenza, quindi sistema abilitato anche se ENV=0.

---

## ✅ Verifica Funzionamento

### Test 1: Compilazione

```bash
cd AC/source/src
make clean
make client
```

**Atteso:** Nessun errore di compilazione. Il file `audio_runtime_obf.o` viene creato.

### Test 2: Avvio Disabilitato

```bash
./ac_client
```

**Atteso (stdout):**
```
[AUDIO_OBF] enabled=0
```

**Nota:** Questo log appare subito dopo l'inizializzazione.

### Test 3: Avvio Abilitato (ENV)

```bash
AC_AUDIO_OBF=1 ./ac_client
```

**Atteso (stdout):**
```
[AUDIO_OBF] enabled=1 from=ENV use_pitch=0 use_noise=0 use_tone=0
...
[AUDIO_OBF] <soundname>.ogg → pitch:+0 cents, noise:SNR=0.0 dB, tone:0 Hz @ 0.0 dB
...
```

**Nota:** I log `[AUDIO_OBF] <soundname> →` appariranno durante il caricamento degli asset audio.

### Test 4: Avvio Abilitato (CLI)

```bash
./ac_client --audio-obf on
```

**Atteso (stdout):**
```
[AUDIO_OBF] enabled=1 from=CLI use_pitch=0 use_noise=0 use_tone=0
...
```

---

## 🔮 Step Successivi (Roadmap)

### Step 2: Pitch Shifting Reale

- Collegare `apply_pitch_inplace()` da `audio_obf.cpp` (vecchio sistema)
- Oppure usare SoundTouch direttamente
- Modificare `aro_process_pcm_int16()` per applicare pitch shift reale quando `use_pitch=true`
- Aggiungere ENV/CLI per configurare `pitch_cents`

### Step 3: Noise Injection

- Implementare `inject_noise()` per aggiungere rumore gaussiano
- Parametro `noise_snr_db` per controllare livello rumore
- Aggiungere ENV/CLI per configurare noise

### Step 4: Tone Injection

- Implementare `inject_tone()` per aggiungere tono sinusoidale
- Parametri `tone_freq_hz` e `tone_level_db`
- Aggiungere ENV/CLI per configurare tone

---

## 🧪 Note di Implementazione

### Perché no-op in Step 1?

**Step 1** è progettato come **proof-of-concept dell'infrastruttura**:

1. Verifica che i punti di hook siano corretti (dopo decode, prima di alBufferData)
2. Verifica che il logging sia chiaro e parsabile
3. Verifica che ENV/CLI args funzionino correttamente
4. Nessun rischio di corrompere l'audio (no trasformazioni reali)

Una volta verificato che tutto funziona, gli step successivi implementeranno le trasformazioni reali.

### Separazione dai Sistemi Esistenti

Il framework **non rimuove** né interferisce con il vecchio sistema `audio_obf.*`:

- `audio_obf.*` → Vecchio sistema pitch shift (già funzionante)
- `audio_runtime_obf.*` → **Nuovo** framework (Step 1+, più completo)

In futuro, potremmo deprecare il vecchio sistema e usare solo il nuovo.

### Thread Safety

**Step 1** non ha problemi di thread safety perché:

- `aro_init_from_env_and_cli()` è chiamata **una volta** all'avvio (main thread)
- `aro_process_pcm_int16()` è chiamata nel thread di caricamento audio (OpenAL)
- **Non ci sono scritture concorrenti** a `g_profile` dopo l'init

Se in futuro vogliamo modificare `g_profile` a runtime (es. da GUI), dovremo aggiungere mutex.

---

## 📦 File Generati

1. **`patch_runtime_framework.diff`**: Diff completo delle modifiche
2. **`RUNTIME_FRAMEWORK_SUMMARY.md`**: Questo documento

---

## 🎯 Conclusioni Step 1

✅ **Infrastruttura completata:**
- Nuovi file: `audio_runtime_obf.h`, `audio_runtime_obf.cpp`
- Hook: `main.cpp` (init), `openal.cpp` (OGG/WAV)
- Build: `Makefile` aggiornato
- ENV/CLI: `AC_AUDIO_OBF=0|1`, `--audio-obf on|off`

✅ **Logging funzionante:**
- `[AUDIO_OBF] enabled=...` all'avvio
- `[AUDIO_OBF] <soundname> → ...` per ogni suono caricato

✅ **No modifiche audio:**
- Step 1 è **non invasivo** (no-op)
- Buffer PCM non viene alterato

✅ **Pronto per Step 2+:**
- Struttura `ARO_Profile` pronta per pitch/noise/tone
- Helper `int16_to_float` e `float_to_int16` implementati
- Punto di applicazione (`aro_process_pcm_int16`) identificato

**Step 1 completato con successo! 🚀**

---

**Prossimo passo:** Implementare pitch shifting reale in Step 2.

