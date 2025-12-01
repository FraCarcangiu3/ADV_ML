# Procedura Operativa: Test Offline Pitch Shift per Audio Anti-Cheat

**Scopo:** Guidare l'esecuzione sistematica di test offline di trasformazioni audio (pitch shift) su asset di AssaultCube, raccogliendo dati quantitativi (SNR, latenza, CPU%) e qualitativi (percezione soggettiva) per validare la fattibilità tecnica di tecniche di obfuscation/watermarking.

**Versione:** 1.1  
**Data:** 15 Ottobre 2024  
**Prerequisito:** Familiarità con terminale Unix/macOS, nozioni di audio digitale.

---

## 1. Requisiti

### 1.1 Software (Obbligatorio)

**macOS (Homebrew):**
```bash
# Installazione Homebrew (se non presente)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Installazione dipendenze
brew install libsndfile sound-touch ffmpeg python@3.11

# Pacchetti Python
pip3 install soundfile numpy matplotlib scipy
```

**Linux (Debian/Ubuntu):**
```bash
sudo apt update
sudo apt install -y build-essential libsndfile1-dev libsoundtouch-dev \
                    ffmpeg python3 python3-pip git

pip3 install --user soundfile numpy matplotlib scipy
```

**Verifica installazione:**
```bash
ffmpeg -version          # Deve mostrare ffmpeg versione ≥5.0
python3 --version        # Deve mostrare Python ≥3.9
c++ --version            # Deve mostrare clang/gcc con supporto C++17
brew list libsndfile sound-touch   # (macOS) Deve elencare le librerie
```

### 1.2 Hardware Consigliato

- **CPU:** Dual-core 2.0+ GHz (test basic), Quad-core 3.0+ GHz (test estensivi).
- **RAM:** 4GB minimo, 8GB consigliato.
- **Audio:** Cuffie di riferimento (es. Audio-Technica ATH-M50x, Beyerdynamic DT 770 Pro, Sennheiser HD 600) per test percettivi. Speaker desktop OK per test preliminari.
- **Storage:** ~500MB per campioni audio e risultati.

### 1.3 Workspace Setup

**Creazione cartelle:**
```bash
cd "/Users/francesco03/Documents/GitHub/AssaultCube Server"   # Adattare al tuo path
mkdir -p AC/tools/samples AC/tools/results
```

**Struttura attesa:**
```
AC/
├── tools/
│   ├── pitch_test.cpp           # PoC pitch shift (sorgente)
│   ├── snrdiff.py               # Calcolo SNR (script Python)
│   ├── build_pitch_test.sh      # Script compilazione macOS
│   ├── README_poc.txt           # Istruzioni brevi
│   ├── samples/                 # File WAV estratti per test (input)
│   └── results/                 # File trasformati e log (output)
└── packages/audio/              # Asset audio originali AssaultCube
    ├── weapon/
    ├── player/
    ├── voicecom/
    └── ...
```

---

## 2. Preparazione Dati

### 2.1 Estrazione WAV da Asset OGG

Gli asset audio di AssaultCube sono in formato OGG Vorbis (lossy). Per test consistenti, convertiamo in WAV (PCM non compresso) con sample rate e canali uniformi.

**Comando base (mono, 44.1 kHz):**
```bash
ffmpeg -i AC/packages/audio/weapon/shotgun.ogg \
       -ar 44100 -ac 1 AC/tools/samples/shotgun_ref.wav
```

**Parametri:**
- `-ar 44100`: Sample rate 44100 Hz (standard CD quality).
- `-ac 1`: Mono (1 canale). Usare `-ac 2` per stereo se necessario.

**Batch conversion (esempio per categoria weapon):**
```bash
for file in AC/packages/audio/weapon/*.ogg; do
    basename=$(basename "$file" .ogg)
    ffmpeg -i "$file" -ar 44100 -ac 1 "AC/tools/samples/${basename}_ref.wav" -y
done
```

**Asset consigliati per test iniziali:**
```bash
# Weapon (percussivi, brevi)
ffmpeg -i AC/packages/audio/weapon/shotgun.ogg -ar 44100 -ac 1 AC/tools/samples/shotgun_ref.wav
ffmpeg -i AC/packages/audio/weapon/sniper.ogg -ar 44100 -ac 1 AC/tools/samples/sniper_ref.wav
ffmpeg -i AC/packages/audio/weapon/auto.ogg -ar 44100 -ac 1 AC/tools/samples/auto_ref.wav
ffmpeg -i AC/packages/audio/weapon/carbine.ogg -ar 44100 -ac 1 AC/tools/samples/carbine_ref.wav

# Player (passi, continui)
ffmpeg -i AC/packages/audio/player/footsteps.ogg -ar 44100 -ac 1 AC/tools/samples/footsteps_ref.wav
ffmpeg -i AC/packages/audio/player/jump.ogg -ar 44100 -ac 1 AC/tools/samples/jump_ref.wav

# Voicecom (voce umana, armoniche complesse)
ffmpeg -i AC/packages/audio/voicecom/affirmative.ogg -ar 44100 -ac 1 AC/tools/samples/vc_affirmative_ref.wav
ffmpeg -i AC/packages/audio/voicecom/negative.ogg -ar 44100 -ac 1 AC/tools/samples/vc_negative_ref.wav
```

**Verifica files estratti:**
```bash
ls -lh AC/tools/samples/
# Atteso: vari file .wav con dimensioni ragionevoli (10KB–500KB per clip <5s)

file AC/tools/samples/shotgun_ref.wav
# Atteso: "RIFF (little-endian) data, WAVE audio, Microsoft PCM, 16 bit, mono 44100 Hz"
```

---

## 3. Compilazione Strumenti PoC

### 3.1 Compilazione pitch_test (macOS, metodo automatico)

```bash
cd AC/tools
./build_pitch_test.sh
```

**Output atteso:**
```
Compilazione pitch_test.cpp...
Homebrew prefix: /opt/homebrew
libsndfile: /opt/homebrew/opt/libsndfile
sound-touch: /opt/homebrew/opt/sound-touch
✓ Compilazione riuscita! Eseguibile: ./pitch_test
```

**Verifica:**
```bash
./pitch_test
# Atteso: "Usage: ./pitch_test <input> <output> --cents <cents>"
```

### 3.2 Compilazione pitch_test (manuale, tutti i sistemi)

**macOS (path Homebrew espliciti):**
```bash
c++ -std=c++17 pitch_test.cpp \
    -I/opt/homebrew/opt/libsndfile/include \
    -I/opt/homebrew/opt/sound-touch/include \
    -L/opt/homebrew/opt/libsndfile/lib \
    -L/opt/homebrew/opt/sound-touch/lib \
    -lsndfile -lSoundTouch \
    -o pitch_test
```

**Linux (path tipici):**
```bash
g++ -std=c++17 pitch_test.cpp \
    -I/usr/include \
    -L/usr/lib/x86_64-linux-gnu \
    -lsndfile -lSoundTouch \
    -o pitch_test
```

**Troubleshooting:**
- **Errore:** `fatal error: 'sndfile.h' file not found`  
  **Soluzione:** Verificare installazione `libsndfile-dev` (Linux) o `libsndfile` (Homebrew).

- **Errore:** `ld: library not found for -lSoundTouch`  
  **Soluzione (macOS):** Verificare che Homebrew abbia installato `sound-touch` (non `soundtouch`). Controllare con `brew list sound-touch`.

- **Errore (Linux):** `undefined reference to 'soundtouch::SoundTouch::...'`  
  **Soluzione:** Assicurarsi che `-lSoundTouch` sia DOPO i file oggetto nel comando di link.

### 3.3 Verifica snrdiff.py

```bash
cd AC/tools
python3 snrdiff.py
# Atteso: "Uso: python snrdiff.py <original_file.wav> <processed_file.wav>"
```

---

## 4. Esempi d'Uso

### 4.1 Applicazione Pitch Shift

**Comando base:**
```bash
AC/tools/pitch_test <input.wav> <output.wav> --cents <N>
```

**Parametri:**
- `<input.wav>`: File WAV/OGG input (path relativo o assoluto).
- `<output.wav>`: File WAV output (sempre formato WAV float32).
- `--cents <N>`: Shift in cents (100 cents = 1 semitono).
  - Positivo: pitch più alto (es. `+5` → frequenze aumentate di ~0.3%).
  - Negativo: pitch più basso (es. `-10` → frequenze diminuite di ~0.6%).
  - Range consigliato: -20 a +20 cents per impercettibilità.

**Esempi pratici:**

```bash
# Shift minimo (+2 cents, impercettibile)
AC/tools/pitch_test AC/tools/samples/shotgun_ref.wav \
                    AC/tools/results/shotgun_p2.wav --cents 2

# Shift moderato (+5 cents, target obfuscation)
AC/tools/pitch_test AC/tools/samples/shotgun_ref.wav \
                    AC/tools/results/shotgun_p5.wav --cents 5

# Shift negativo (-10 cents)
AC/tools/pitch_test AC/tools/samples/shotgun_ref.wav \
                    AC/tools/results/shotgun_m10.wav --cents -10

# Shift percettibile (+20 cents, test limite)
AC/tools/pitch_test AC/tools/samples/shotgun_ref.wav \
                    AC/tools/results/shotgun_p20.wav --cents 20
```

**Output atteso:**
```
Input: 13804 frames, 1 ch, 44100 Hz
Output: 13804 frames (pitch shift: 5.0 cents) → AC/tools/results/shotgun_p5.wav
```

**Interpretazione:**
- `13804 frames`: Numero campioni audio (durata ~0.31s a 44100 Hz).
- `1 ch`: Mono.
- `pitch shift: 5.0 cents`: Trasformazione applicata correttamente.

### 4.2 Calcolo SNR

**Comando:**
```bash
python3 AC/tools/snrdiff.py <original.wav> <transformed.wav>
```

**Esempio:**
```bash
python3 AC/tools/snrdiff.py AC/tools/samples/shotgun_ref.wav \
                            AC/tools/results/shotgun_p5.wav
```

**Output atteso:**
```
SNR tra 'AC/tools/samples/shotgun_ref.wav' e 'AC/tools/results/shotgun_p5.wav': 38.42 dB
```

**Interpretazione SNR:**
- **>40 dB:** Differenza trascurabile, impercettibile.
- **30–40 dB:** Differenza minima, percettibile solo in ascolto critico.
- **20–30 dB:** Differenza moderata, potenzialmente percettibile in-game.
- **<20 dB:** Differenza significativa, degradazione evidente.

**Nota:** SNR dipende da:
- Entità shift (cents): più alto lo shift, più basso SNR.
- Contenuto audio: toni puri (armoniche) sono più sensibili; rumore/percussivi meno.
- Algoritmo: SoundTouch usa WSOLA (buona preservazione qualità).

### 4.3 Ascolto Comparativo

**macOS:**
```bash
afplay AC/tools/samples/shotgun_ref.wav     # Originale
afplay AC/tools/results/shotgun_p5.wav      # Trasformato
```

**Linux:**
```bash
aplay AC/tools/samples/shotgun_ref.wav
aplay AC/tools/results/shotgun_p5.wav
```

**Audacity (GUI, tutti i sistemi):**
1. Aprire Audacity.
2. File → Open → selezionare `shotgun_ref.wav`.
3. File → Open → selezionare `shotgun_p5.wav` (si apre in traccia separata).
4. Usare "Mute/Solo" per alternare ascolto.
5. Visualizzare spettrogramma: Analyze → Plot Spectrum.

**Checklist ascolto:**
- [ ] Tonalità generale percettibilmente diversa? (SÌ/NO)
- [ ] Artefatti udibili (phasiness, aliasing, clicks)? (SÌ/NO)
- [ ] Percezione soggettiva: impercettibile / leggermente percettibile / percettibile / molto percettibile

---

## 5. Procedure di Test Consigliate

### 5.1 Test di Base (1–3 file, vari cents)

**Obiettivo:** Stabilire baseline SNR e percezione per shift standard.

**Procedura:**
1. Selezionare 3 asset rappresentativi (es. `shotgun`, `footsteps`, `vc_affirmative`).
2. Applicare shift: +2, +5, +10, +20 cents (4 varianti per asset).
3. Calcolare SNR per ciascuna coppia (originale, trasformato).
4. Ascolto comparativo con cuffie.
5. Compilare tabella risultati (vedi Sezione 6).

**Comando batch esempio:**
```bash
# Asset: shotgun
for cents in 2 5 10 20; do
    AC/tools/pitch_test AC/tools/samples/shotgun_ref.wav \
                        AC/tools/results/shotgun_p${cents}.wav --cents $cents
    python3 AC/tools/snrdiff.py AC/tools/samples/shotgun_ref.wav \
                                AC/tools/results/shotgun_p${cents}.wav \
            >> AC/tools/results/snr_log_shotgun.txt
done
```

### 5.2 Test di Sensibilità (Scalare cents fino a percepibile)

**Obiettivo:** Determinare soglia percettibilità per asset specifico.

**Procedura:**
1. Partire da +1 cent, incrementare progressivamente (+1, +2, +3, ..., +15).
2. Per ogni shift, ascolto ABX (alternare originale/trasformato senza guardare quale).
3. Annotare primo valore di cents dove l'ascoltatore rileva differenza con confidenza >70%.
4. Ripetere con shift negativo (-1, -2, ..., -15).

**Esempio script incrementale:**
```bash
for cents in $(seq 1 15); do
    AC/tools/pitch_test AC/tools/samples/vc_affirmative_ref.wav \
                        AC/tools/results/vc_aff_p${cents}.wav --cents $cents
    echo "Test +${cents} cents - Premi ENTER dopo ascolto"
    afplay AC/tools/results/vc_aff_p${cents}.wav
    read
done
```

### 5.3 Test Across Devices

**Obiettivo:** Verificare che impercettibilità si mantenga su dispositivi audio diversi.

**Dispositivi consigliati:**
- Cuffie studio (es. ATH-M50x) — reference.
- Cuffie consumer (es. Apple EarPods, Sony WH-1000XM).
- Speaker desktop (es. Logitech Z200, monitor integrati).
- Speaker gaming (es. Razer Nommo).
- Smartphone (iPhone, Android con auricolari stock).

**Procedura:**
1. Preparare 3–5 coppie (originale, trasformato +5 cents).
2. Per ciascun dispositivo: ascolto comparativo, annotare percezione.
3. Se disponibile, misurare risposta in frequenza del dispositivo (pink noise test).

**Template annotazione:**
| dispositivo | asset | cents | percettibile? | note |
|---|---|---:|---|---|
| ATH-M50x | shotgun | +5 | NO | Nessuna differenza rilevata |
| iPhone Speaker | shotgun | +5 | SÌ | Leggera nasalità percepita |
| ... | ... | ... | ... | ... |

### 5.4 Test di Robustezza (Ricampionamento/Compressione)

**Obiettivo:** Verificare che trasformazione sopravviva a pipeline realistiche (streaming, VoIP).

**Scenari:**
1. **Ricampionamento:** 44100 Hz → 22050 Hz → 44100 Hz.
2. **Compressione MP3:** WAV → MP3 (128 kbps) → WAV.
3. **Compressione Opus:** WAV → Opus (64 kbps, Discord/VoIP) → WAV.

**Comandi esempio:**

**Ricampionamento:**
```bash
# Downsampling
ffmpeg -i AC/tools/results/shotgun_p5.wav -ar 22050 AC/tools/results/shotgun_p5_22k.wav
# Upsampling
ffmpeg -i AC/tools/results/shotgun_p5_22k.wav -ar 44100 AC/tools/results/shotgun_p5_resampled.wav
# SNR post-ricampionamento
python3 AC/tools/snrdiff.py AC/tools/samples/shotgun_ref.wav \
                            AC/tools/results/shotgun_p5_resampled.wav
```

**Compressione MP3:**
```bash
ffmpeg -i AC/tools/results/shotgun_p5.wav -b:a 128k AC/tools/results/shotgun_p5.mp3
ffmpeg -i AC/tools/results/shotgun_p5.mp3 AC/tools/results/shotgun_p5_mp3dec.wav
python3 AC/tools/snrdiff.py AC/tools/samples/shotgun_ref.wav \
                            AC/tools/results/shotgun_p5_mp3dec.wav
```

**Compressione Opus (VoIP):**
```bash
ffmpeg -i AC/tools/results/shotgun_p5.wav -c:a libopus -b:a 64k AC/tools/results/shotgun_p5.opus
ffmpeg -i AC/tools/results/shotgun_p5.opus AC/tools/results/shotgun_p5_opusdec.wav
python3 AC/tools/snrdiff.py AC/tools/samples/shotgun_ref.wav \
                            AC/tools/results/shotgun_p5_opusdec.wav
```

**Interpretazione:**
- Se SNR rimane >30 dB dopo pipeline, trasformazione è robusta.
- Se SNR scende <20 dB, trasformazione è vulnerabile (cheat potrebbe normalizzare).

---

## 6. Template Raccolta Dati

### 6.1 Tabella Risultati (Markdown)

Copiare in file `AC/tools/results/test_results_YYYYMMDD.md` e compilare durante test.

```markdown
# Risultati Test Pitch Shift - [DATA]

## Configurazione
- Sistema: macOS 14.0 / Ubuntu 22.04
- CPU: [es. Apple M1, Intel i7-12700K]
- Cuffie: [es. Audio-Technica ATH-M50x]
- Sample rate: 44100 Hz
- Formato: Mono (1 ch)

## Dati

| file | cents | SNR_dB | latency_ms | CPU% | percezione | note |
|---|---:|---:|---:|---:|---|---|
| shotgun_ref vs shotgun_p2 | +2 | | | | | |
| shotgun_ref vs shotgun_p5 | +5 | | | | | |
| shotgun_ref vs shotgun_p10 | +10 | | | | | |
| shotgun_ref vs shotgun_p20 | +20 | | | | | |
| shotgun_ref vs shotgun_m5 | -5 | | | | | |
| shotgun_ref vs shotgun_m10 | -10 | | | | | |
| auto_ref vs auto_p5 | +5 | | | | | |
| auto_ref vs auto_p10 | +10 | | | | | |
| footsteps_ref vs footsteps_p5 | +5 | | | | | |
| footsteps_ref vs footsteps_p10 | +10 | | | | | |
| vc_affirmative_ref vs vc_aff_p5 | +5 | | | | | |
| vc_affirmative_ref vs vc_aff_p10 | +10 | | | | | |

## Legenda
- **SNR_dB:** Signal-to-Noise Ratio (da snrdiff.py).
- **latency_ms:** Tempo elaborazione (da /usr/bin/time -l).
- **CPU%:** Utilizzo CPU medio (da /usr/bin/time -l).
- **percezione:** impercettibile | leggermente percettibile | percettibile | molto percettibile.
- **note:** Osservazioni qualitative (artefatti, contesto).
```

### 6.2 Misurazione Latenza e CPU

**macOS:**
```bash
/usr/bin/time -l AC/tools/pitch_test AC/tools/samples/shotgun_ref.wav \
                                      AC/tools/results/shotgun_p5.wav --cents 5 \
              2>&1 | grep -E "real|percent"
```

**Output esempio:**
```
        0.08 real         0.05 user         0.02 sys
   52.3% CPU
```
→ Latency: 80ms, CPU: 52.3%

**Linux:**
```bash
/usr/bin/time -v AC/tools/pitch_test AC/tools/samples/shotgun_ref.wav \
                                      AC/tools/results/shotgun_p5.wav --cents 5 \
              2>&1 | grep -E "Elapsed|CPU"
```

**Interpretazione:**
- Latenza <10ms: Eccellente per init-time loading.
- Latenza 10–50ms: Accettabile per la maggior parte degli scenari.
- Latenza >100ms: Potenzialmente problematico su hardware low-end.
- CPU% <50%: Basso overhead, scalabile a molti asset.
- CPU% >80%: Alto overhead, ottimizzazione necessaria.

### 6.3 Log Completo Test

Salvare output completo in file di log per tracciabilità:

```bash
{
    echo "=== Test Batch $(date) ==="
    echo "Sistema: $(uname -a)"
    echo "CPU: $(sysctl -n machdep.cpu.brand_string)"  # macOS
    # echo "CPU: $(lscpu | grep 'Model name')"         # Linux
    echo ""
    
    for cents in 2 5 10 20; do
        echo "--- Pitch shift: +${cents} cents ---"
        /usr/bin/time -l AC/tools/pitch_test \
            AC/tools/samples/shotgun_ref.wav \
            AC/tools/results/shotgun_p${cents}.wav --cents $cents
        python3 AC/tools/snrdiff.py \
            AC/tools/samples/shotgun_ref.wav \
            AC/tools/results/shotgun_p${cents}.wav
        echo ""
    done
} > AC/tools/results/test_log_$(date +%Y%m%d_%H%M%S).txt 2>&1
```

---

## 7. Analisi Avanzata (Opzionale)

### 7.1 Analisi Spettrografica con sox

**Generazione spettrogramma PNG:**
```bash
sox AC/tools/samples/shotgun_ref.wav -n spectrogram -o AC/tools/results/shotgun_ref_spectrogram.png
sox AC/tools/results/shotgun_p5.wav -n spectrogram -o AC/tools/results/shotgun_p5_spectrogram.png
```

**Apertura con viewer:**
```bash
open AC/tools/results/shotgun_ref_spectrogram.png    # macOS
xdg-open AC/tools/results/shotgun_ref_spectrogram.png # Linux
```

**Cosa osservare:**
- **Shift formanti:** Bande orizzontali (armoniche) spostate verso l'alto (+cents) o basso (-cents).
- **Artefatti:** Bande spurie, aliasing ad alte frequenze (sopra Nyquist).
- **Preservazione envelope:** Transients (es. attacco pistola) devono rimanere sharp.

### 7.2 Script Python per Analisi Spettrale

Salvare come `AC/tools/spectral_analysis.py`:

```python
import soundfile as sf
import matplotlib.pyplot as plt
import numpy as np
import sys

if len(sys.argv) != 3:
    print("Uso: python3 spectral_analysis.py <original.wav> <transformed.wav>")
    sys.exit(1)

data_orig, sr = sf.read(sys.argv[1])
data_trans, _ = sf.read(sys.argv[2])

fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# Waveform
axes[0, 0].plot(data_orig, linewidth=0.5)
axes[0, 0].set_title('Waveform Originale')
axes[0, 0].set_xlabel('Sample')
axes[0, 0].set_ylabel('Amplitude')

axes[0, 1].plot(data_trans, linewidth=0.5, color='orange')
axes[0, 1].set_title('Waveform Trasformato')
axes[0, 1].set_xlabel('Sample')
axes[0, 1].set_ylabel('Amplitude')

# Spectrogram
axes[1, 0].specgram(data_orig, Fs=sr, cmap='viridis', NFFT=1024, noverlap=512)
axes[1, 0].set_title('Spettrogramma Originale')
axes[1, 0].set_xlabel('Time (s)')
axes[1, 0].set_ylabel('Frequency (Hz)')

axes[1, 1].specgram(data_trans, Fs=sr, cmap='viridis', NFFT=1024, noverlap=512)
axes[1, 1].set_title('Spettrogramma Trasformato')
axes[1, 1].set_xlabel('Time (s)')
axes[1, 1].set_ylabel('Frequency (Hz)')

plt.tight_layout()
plt.savefig('AC/tools/results/spectral_comparison.png', dpi=150)
print("Salvato: AC/tools/results/spectral_comparison.png")
```

**Uso:**
```bash
python3 AC/tools/spectral_analysis.py AC/tools/samples/shotgun_ref.wav \
                                      AC/tools/results/shotgun_p5.wav
```

### 7.3 Registrazione Audio Loopback (per test in-game futuro)

**macOS (BlackHole):**
1. Installare BlackHole: `brew install blackhole-2ch`
2. Audio MIDI Setup → Create Multi-Output Device (BlackHole + Built-in Output).
3. Impostare Multi-Output come default in System Preferences.
4. Registrare con Audacity (input: BlackHole).

**Linux (PulseAudio/PipeWire):**
```bash
# Elencare sinks disponibili
pactl list short sinks

# Registrare output sistema
parec --device=<sink>.monitor --file-format=wav > recording.wav
```

**Uso:** Avviare registrazione, riprodurre audio in-game, fermare registrazione, analizzare file registrato.

---

## 8. Script Utili da Aggiungere a AC/tools/

### 8.1 Skeleton: run_all_pitch_tests.sh

Salvare come `AC/tools/run_all_pitch_tests.sh`:

```bash
#!/bin/bash
# Script batch per test sistematici pitch shift
# Uso: ./run_all_pitch_tests.sh

set -e

SAMPLES_DIR="AC/tools/samples"
RESULTS_DIR="AC/tools/results"
PITCH_TEST="AC/tools/pitch_test"
SNRDIFF="AC/tools/snrdiff.py"

# Lista asset da testare (aggiungere a piacere)
ASSETS=(
    "shotgun_ref.wav"
    "auto_ref.wav"
    "footsteps_ref.wav"
    "vc_affirmative_ref.wav"
)

# Lista cents da applicare
CENTS_LIST=(2 5 10 20 -5 -10)

echo "=== Batch Test Pitch Shift ==="
echo "Data: $(date)"
echo "Sistema: $(uname -a)"
echo ""

for asset in "${ASSETS[@]}"; do
    base_name="${asset%_ref.wav}"
    echo "Asset: $asset"
    
    for cents in "${CENTS_LIST[@]}"; do
        if [ $cents -lt 0 ]; then
            suffix="m${cents#-}"
        else
            suffix="p${cents}"
        fi
        
        output="${RESULTS_DIR}/${base_name}_${suffix}.wav"
        
        echo "  Shift: ${cents} cents → ${output}"
        $PITCH_TEST "${SAMPLES_DIR}/${asset}" "$output" --cents $cents
        
        echo -n "  SNR: "
        python3 $SNRDIFF "${SAMPLES_DIR}/${asset}" "$output" | grep "SNR"
        echo ""
    done
    echo ""
done

echo "✓ Test completati. Risultati in $RESULTS_DIR"
```

**Rendere eseguibile:**
```bash
chmod +x AC/tools/run_all_pitch_tests.sh
```

**Esecuzione:**
```bash
./AC/tools/run_all_pitch_tests.sh | tee AC/tools/results/batch_test_$(date +%Y%m%d).log
```

### 8.2 Skeleton: analyze_results.py

Salvare come `AC/tools/analyze_results.py`:

```python
#!/usr/bin/env python3
"""
Analisi statistica risultati test batch.
Legge file log, estrae SNR, genera report e grafici.
"""
import re
import sys
import matplotlib.pyplot as plt
import numpy as np

if len(sys.argv) != 2:
    print("Uso: python3 analyze_results.py <batch_test_log.txt>")
    sys.exit(1)

log_file = sys.argv[1]

# Parsing log (esempio semplice)
pattern = r'Shift: ([+-]?\d+) cents.*SNR.*: ([\d.]+) dB'
results = []

with open(log_file, 'r') as f:
    for line in f:
        match = re.search(pattern, line)
        if match:
            cents = int(match.group(1))
            snr = float(match.group(2))
            results.append((cents, snr))

if not results:
    print("Nessun dato SNR trovato nel log.")
    sys.exit(1)

cents_list = [r[0] for r in results]
snr_list = [r[1] for r in results]

# Statistiche
print(f"Totale test: {len(results)}")
print(f"SNR medio: {np.mean(snr_list):.2f} dB")
print(f"SNR min: {np.min(snr_list):.2f} dB (cents={cents_list[np.argmin(snr_list)]})")
print(f"SNR max: {np.max(snr_list):.2f} dB (cents={cents_list[np.argmax(snr_list)]})")

# Grafico
plt.figure(figsize=(10, 6))
plt.scatter(cents_list, snr_list, alpha=0.6)
plt.axhline(y=30, color='r', linestyle='--', label='Soglia 30 dB')
plt.axhline(y=40, color='g', linestyle='--', label='Soglia 40 dB')
plt.xlabel('Pitch Shift (cents)')
plt.ylabel('SNR (dB)')
plt.title('SNR vs. Pitch Shift')
plt.legend()
plt.grid(True, alpha=0.3)
plt.savefig('AC/tools/results/snr_vs_cents.png', dpi=150)
print("Grafico salvato: AC/tools/results/snr_vs_cents.png")
```

**Uso:**
```bash
python3 AC/tools/analyze_results.py AC/tools/results/batch_test_20241015.log
```

---

## 9. Checklist Controllo Qualità (Pre-Integrazione Client)

Prima di procedere con modifiche al codice di gioco, verificare che:

- [ ] **SNR > 35 dB** per shift target (es. ±5 cents) su almeno 90% asset testati.
- [ ] **Latenza < 10ms** per asset brevi (<1s) su hardware target minimo.
- [ ] **CPU% < 50%** per trasformazione singolo asset.
- [ ] **Test ABX**: <60% accuratezza identificazione (equivalente a guess casuale).
- [ ] **Test multi-device**: Impercettibilità confermata su almeno 3 dispositivi (cuffie studio, speaker desktop, smartphone).
- [ ] **Robustezza**: SNR post-compressione Opus/MP3 > 25 dB.
- [ ] **Documentazione**: Tabella risultati completa, log salvati, spettrogrammi rappresentativi generati.

---

## 10. Annota Qui i Risultati

### 10.1 Template Note Test

```markdown
## Test [DATA] - [DESCRIZIONE BREVE]

**Configurazione:**
- Sistema: 
- CPU: 
- Audio: 
- Asset testati: 

**Risultati chiave:**
- SNR medio: 
- Percezione soggettiva: 
- Problemi riscontrati: 

**File generati:**
- Log: 
- Grafici: 
- Spettrogrammi: 

**Conclusioni:**
[2–3 frasi su cosa è stato appreso e prossimi passi]
```

### 10.2 Come Salvare Prove Sperimentali

**Struttura raccomandata AC/tools/results/:**
```
results/
├── batch_test_20241015.log          # Log completo esecuzione
├── test_results_20241015.md         # Tabella risultati compilata
├── snr_vs_cents.png                 # Grafico SNR vs. shift
├── shotgun_ref_spectrogram.png      # Spettrogramma originale
├── shotgun_p5_spectrogram.png       # Spettrogramma trasformato
├── spectral_comparison.png          # Confronto side-by-side
└── notes_20241015.md                # Note qualitative test
```

**Backup risultati:**
```bash
tar -czf results_backup_$(date +%Y%m%d).tar.gz AC/tools/results/
```

---

## 11. Riferimenti

**Documenti correlati:**
- `PROJECT_FULL_LOG.md` — Log completo progetto per tesi.
- `AC/tools/README_poc.txt` — Istruzioni brevi PoC.
- `.cursor-output/patch_candidates.md` — Hook points identificati.
- `.cursor-output/README_quickrefs.txt` — Comandi e file analisi codice.

**Strumenti esterni:**
- SoundTouch: https://www.surina.net/soundtouch/
- libsndfile: http://www.mega-nerd.com/libsndfile/
- sox: http://sox.sourceforge.net/
- Audacity: https://www.audacityteam.org/

---

---

## 12. Stato Progetto e Prossimi Passi

### ✅ Attività Completate (Test Offline)

- ✅ Creato branch Git `feat/pitch-shift-poc` in `AC/` (strumenti offline).
- ✅ Creati strumenti PoC offline:
  - `AC/tools/pitch_test.cpp` (compilazione verificata su macOS/Homebrew)
  - `AC/tools/snrdiff.py` (SNR tra file WAV)
  - `AC/tools/build_pitch_test.sh` (rileva path Homebrew e compila)
  - `AC/tools/README_poc.txt` (istruzioni consolidate)
- ✅ Esecuzione smoke-test su asset `auto.ogg`, `shotgun.ogg` → output WAV validi.
- ✅ Creata infrastruttura: `AC/tools/results/`, `AC/tools/samples/`.
- ✅ Pipeline offline validata: estrazione WAV → pitch shift → SNR → ascolto.
- ✅ Documentazione tecnica completa: `PROJECT_FULL_LOG.md`, `OFFLINE_PITCH_TEST_PROCEDURE.md`.

### 🔄 Attività Correnti (Integrazione Client)

**Obiettivo:** Integrare pitch shift nel client AssaultCube per test in-game.

**Stato:** ✅ **COMPLETATO** (codice scritto, patch generati, documenti aggiornati)

**File creati/modificati:**
- ✅ `AC/source/src/audio_obf.h` — API pitch shift runtime
- ✅ `AC/source/src/audio_obf.cpp` — Implementazione SoundTouch + fallback
- ✅ `AC/source/src/openal.cpp` — Hook before alBufferData (OGG + WAV)
- ✅ `AC/source/src/main.cpp` — Inizializzazione ac_audio_obf_init()
- ✅ `.cursor-output/patch_pitch_client.diff` — Diff completo modifiche
- ✅ `.cursor-output/patch_pitch_client.patch` — Patch applicabile (git am)
- ✅ `INGAME_PITCH_TEST_PROCEDURE.md` — Guida ricompilazione e test in-game
- ✅ `.cursor-output/NEXT_STEPS.txt` — Riepilogo next steps

**Prossima azione manuale richiesta:**
1. **Ricompilare client** (vedi `INGAME_PITCH_TEST_PROCEDURE.md` sezione B).
2. **Eseguire test in-game** con cents: ±5, ±10, ±20, ±60 (sezione C).
3. **Compilare tabella percezione** soggettiva (sezione C.4).
4. **(Opzionale)** Registrare audio loopback e calcolare SNR in-game (sezione D).

### 🧭 Prossimi Passi (Post-Test In-Game)

1. **Analisi risultati in-game:**
   - Compilare tabella percezione (INGAME_PITCH_TEST_PROCEDURE.md C.4)
   - Calcolare SNR su clip registrati (se disponibili)
   - Annotare osservazioni: latency, CPU%, artefatti

2. **Documentazione finale:**
   - Aggiornare PROJECT_FULL_LOG.md con risultati in-game
   - Aggiungere screenshot/log in appendice (opzionale)

3. **Validazione tecnica avanzata (opzionale):**
   - Profiling CPU (Instruments/perf) su caricamento asset
   - Test cross-platform (macOS, Linux, Windows se disponibile)
   - Stress test: 100+ asset con pitch abilitato

4. **Estensioni future (tesi):**
   - Parametrizzazione cents per client_id (watermarking univoco)
   - Telemetria: hash PCM post-transform → validazione server
   - Spread-spectrum watermarking (FFT-based)

---

**Ultimo aggiornamento:** 15 Ottobre 2024  
**Versione:** 1.2 (integrazione client completata, pronta per test in-game)  
**Autore:** Francesco Carcangiu

