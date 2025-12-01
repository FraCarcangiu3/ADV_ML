# Riepilogo Integrazione Pitch Shift nel Client AssaultCube

**Data:** 15 Ottobre 2024  
**Branch:** `feat/pitch-shift-client` (in AC/)  
**Commit:** f89eba32

---

## File Creati

### Codice Sorgente (AC/source/src/)

1. **`audio_obf.h`** (85 righe)
   - **Scopo:** Header pubblico API audio obfuscation
   - **Funzioni principali:**
     - `ac_audio_obf_init(int argc, char** argv)` — Inizializzazione runtime
     - `ac_pitch_is_enabled()` — Check abilitazione
     - `ac_pitch_cents()` — Getter valore cents
     - `apply_pitch_inplace(int16_t* samples, ...)` — Trasformazione PCM

2. **`audio_obf.cpp`** (260 righe)
   - **Scopo:** Implementazione pitch shift con SoundTouch o fallback
   - **Percorso A:** SoundTouch (`#ifdef HAVE_SOUNDTOUCH`)
     - Algoritmo WSOLA, preservazione qualità
     - Conversione int16 ↔ float
   - **Percorso B:** Fallback resampling semplice (se SoundTouch assente)
   - **Validazione:** Clamping cents ∈ [-200, +200], log dettagliati

### Documentazione (root workspace)

3. **`INGAME_PITCH_TEST_PROCEDURE.md`** (650+ righe)
   - **Scopo:** Guida completa ricompilazione e test in-game
   - **Sezioni:**
     - A. Requisiti build (macOS/Linux)
     - B. Ricompilazione (Make/CMake)
     - C. Esecuzione in-game (env vars, CLI args, scenari test)
     - D. Misure e raccolta dati (loopback, SNR, profiling)
     - E. Troubleshooting (errori comuni, soluzioni)
     - F. Checklist pre-report
     - G. Template report risultati
     - H. Riferimenti

4. **`.cursor-output/NEXT_STEPS.txt`** (150 righe)
   - **Scopo:** Riepilogo operativo next steps
   - **Contenuto:**
     - Comandi compilazione rapidi
     - Serie test consigliata (±5, ±10, ±20, ±60 cents)
     - Come disabilitare pitch
     - Checklist raccolta dati per relatore
     - Troubleshooting rapido
     - Lista file generati

5. **`.cursor-output/INTEGRATION_SUMMARY.md`** (questo file)
   - **Scopo:** Riepilogo file creati/modificati

---

## File Modificati

### Codice Sorgente (AC/source/src/)

1. **`openal.cpp`**
   - **Linea 4:** Aggiunto `#include "audio_obf.h"`
   - **Linee 296–326:** Hook pitch shift (OGG path)
     - Posizione: Dopo `ov_read`, prima di `alBufferData`
     - Logica: Cast `char*` → `int16_t*`, calcolo frames, chiamata `apply_pitch_inplace`
     - Log: Prima trasformazione (debug)
   - **Linee 367–393:** Hook pitch shift (WAV path)
     - Posizione: Dopo `SDL_LoadWAV`, prima di `alBufferData`
     - Condizione: Solo 16-bit (`AUDIO_S16`/`AUDIO_U16`)
     - Logica analoga a OGG

2. **`main.cpp`**
   - **Linee 1212–1216:** Inizializzazione audio obfuscation
     - Posizione: Subito dopo `sanitychecks()`, prima di setup audio
     - Chiamata: `ac_audio_obf_init(argc, argv)`
     - Garantisce parsing env/argv prima operazioni audio

### Documentazione (root workspace)

3. **`PROJECT_FULL_LOG.md`**
   - **Sezione 12 aggiunta** (180 righe): "Client Integration — Pitch Shift (PoC in-game)"
     - Panoramica integrazione
     - File aggiunti/modificati (dettagli tecnici)
     - Pipeline end-to-end (6 step: startup → decode → hook → upload → playback)
     - Controlli runtime (env vars, CLI args, esempi)
     - Build con SoundTouch (prerequisiti, flag)
     - Rischi e mitigazioni (4 rischi identificati)
     - Patch e diff (come applicare)
     - Prossimi passi validazione (immediati, medio termine, lungo termine)
   - **Versione aggiornata:** 1.1

4. **`OFFLINE_PITCH_TEST_PROCEDURE.md`**
   - **Sezione 12 aggiunta** (65 righe): "Stato Progetto e Prossimi Passi"
     - Attività completate (test offline)
     - Attività correnti (integrazione client) — ✅ COMPLETATO
     - Prossimi passi (test in-game, analisi risultati, validazione avanzata)
   - **Versione aggiornata:** 1.2

---

## Patch Generati

### .cursor-output/

1. **`patch_pitch_client.diff`**
   - **Formato:** Unified diff Git
   - **Contenuto:** Tutti i cambiamenti (4 file: 3 modificati, 2 aggiunti)
   - **Applicazione:** `git apply patch_pitch_client.diff`

2. **`patch_pitch_client.patch`**
   - **Formato:** Git format-patch (applicabile con `git am`)
   - **Contenuto:** Commit completo con messaggio
   - **Applicazione:** `git am < patch_pitch_client.patch`

---

## Hook Posizioni Esatte

### OGG Decode (openal.cpp)

```
File: AC/source/src/openal.cpp
Range: Linee 296–326
Posizione: Dopo decode ov_read, prima di alBufferData
Trigger: if (ac_pitch_is_enabled())
Buffer: buf.getbuf() (char* ma contiene int16)
Frames: buf.length() / (sizeof(int16_t) * channels)
```

### WAV Load (openal.cpp)

```
File: AC/source/src/openal.cpp
Range: Linee 367–393
Posizione: Dopo SDL_LoadWAV, prima di alBufferData
Trigger: if (ac_pitch_is_enabled() && formato 16-bit)
Buffer: wavbuf (uint8_t* ma contiene int16 se AUDIO_S16)
Frames: wavlen / (sizeof(int16_t) * channels)
```

---

## Controlli Runtime

### Variabili d'Ambiente

```bash
export AC_ANTICHEAT_PITCH_ENABLED=1  # 0=off (default), 1=on
export AC_ANTICHEAT_PITCH_CENTS=20   # -200..+200, default 0
```

### Argomenti CLI (precedenza su env)

```bash
./assaultcube_client --pitch-enable --pitch-cents 60
```

### Esempio Combinato

```bash
# Impercettibilità (target obfuscation)
AC_ANTICHEAT_PITCH_ENABLED=1 AC_ANTICHEAT_PITCH_CENTS=5 ./assaultcube_client

# Test stress
./assaultcube_client --pitch-enable --pitch-cents 60
```

---

## Log Attesi

### Startup con SoundTouch

```
[audio_obf] Pitch shift ENABLED: +20 cents
[audio_obf] Using SoundTouch library for high-quality pitch shift
...
[openal.cpp] Applying pitch shift to OGG: 13804 frames, 1 ch, 22050 Hz, +20 cents
[openal.cpp] Applying pitch shift to WAV: 8192 frames, 2 ch, 44100 Hz, +20 cents
```

### Startup senza SoundTouch (fallback)

```
[audio_obf] Pitch shift ENABLED: +20 cents
[audio_obf] WARNING: SoundTouch not available, fallback mode active
[audio_obf]          (Fallback: AL_PITCH will be used if supported)
...
[audio_obf] Fallback resampling (pitch_factor=1.012)
[audio_obf] NOTE: This is NOT true pitch shift (changes duration)
[audio_obf] Rebuild with SoundTouch for proper pitch shifting.
```

### Startup disabilitato (default)

```
[audio_obf] Pitch shift DISABLED (default)
```

---

## Metriche Target (da validare con test in-game)

| Metrica | Target | Metodo Misurazione |
|---|---|---|
| SNR (±5 cents) | >40 dB | snrdiff.py su clip loopback |
| SNR (±20 cents) | >25 dB | snrdiff.py su clip loopback |
| Percezione (±5 cents) | Impercettibile (qualità 4-5) | Scala Likert 1-5 |
| Percezione (±20 cents) | Leggermente percettibile (qualità 3) | Scala Likert 1-5 |
| Latency init-time | <10ms per asset | /usr/bin/time -l, Instruments |
| CPU overhead | <5% tempo init totale | perf, Instruments |
| Crash/artefatti | 0 | Test gameplay 10-30 min |

---

## Statistiche Codice

| File | Righe | Tipo | Stato |
|---|---:|---|---|
| audio_obf.h | 85 | Nuovo | ✅ |
| audio_obf.cpp | 260 | Nuovo | ✅ |
| openal.cpp | +65 | Modificato | ✅ |
| main.cpp | +5 | Modificato | ✅ |
| **Totale** | **415** | **4 file** | **✅** |

---

## Commit Message (già applicato)

```
feat(audio): PoC pitch-shift hook after decode (client-side, opt-in)

- Add audio_obf.{h,cpp} with SoundTouch-based pitch shifting (fallback to simple resampling)
- Runtime controls via env/argv: AC_ANTICHEAT_PITCH_ENABLED, AC_ANTICHEAT_PITCH_CENTS or --pitch-enable/--pitch-cents
- Hook placed before alBufferData to transform PCM once per buffer (OGG and WAV paths)
- Disabled by default; no behavior change unless enabled
- Initialization in main() before audio system startup
```

---

## Prossimi Passi Operativi

1. ✅ **Codice integrato** (questo step)
2. ⏳ **Ricompilare client** (vedi INGAME_PITCH_TEST_PROCEDURE.md sez. B)
3. ⏳ **Test in-game serie parametrizzata** (±5, ±10, ±20, ±60 cents)
4. ⏳ **Compilare tabella percezione** (INGAME_PITCH_TEST_PROCEDURE.md sez. C.4)
5. ⏳ **Registrare audio loopback** (opzionale, sez. D)
6. ⏳ **Calcolare SNR in-game** (opzionale, sez. D.3)
7. ⏳ **Report finale** al relatore (template in sez. G)

---

**Fine Riepilogo**  
**Autore:** Francesco Carcangiu  
**Data Integrazione:** 15 Ottobre 2024

