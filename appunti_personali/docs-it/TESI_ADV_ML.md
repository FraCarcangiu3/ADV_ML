## 7. Cartella ADV_ML: Testing e Machine Learning

### 7.1 Struttura e Scopo

Ho organizzato tutto il workflow di testing automatico e preparazione ML in una cartella dedicata `ADV_ML/`:

```
ADV_ML/
├── dataset/              # File audio originali e obfuscated
│   ├── original/        # Suoni originali (.wav)
│   └── obfuscated/      # Varianti con trasformazioni
├── features/            # Feature estratte (MFCC)
│   ├── X.npy           # Matrice feature (n_samples, n_features)
│   └── y.npy           # Etichette (0=original, 1=obfuscated)
├── scripts/             # Script Python principali
│   ├── audio_converter.py
│   ├── extract_features.py
│   ├── generate_variants.py
│   └── generate_reports.py
├── tests/               # File di test e risultati
│   ├── run_all_tests.sh
│   ├── TEST_RESULTS_COARSE.csv
│   ├── TEST_RESULTS_FINE.csv
│   ├── subjective_results.csv
│   └── TEST_SUMMARY_FINE.md
├── listening_set/       # File audio per test manuali
├── plots/              # Grafici SNR vs pitch
├── docs/               # Guide e documentazione
└── archive/            # File obsoleti/temporanei
```

**Scopo principale**:
1. **Generazione automatica varianti audio** con parametri controllati
2. **Estrazione feature MFCC** per training ML
3. **Test soggettivi strutturati** con CSV di registrazione
4. **Preparazione dataset** per validazione finale (post-randomizzazione)

### 7.2 Generazione Varianti Audio

**Script**: `ADV_ML/scripts/generate_variants.py`

**Funzionalità**:
- Legge OGG da `AC/packages/audio/`
- Converte in WAV mono 44.1 kHz
- Applica trasformazioni (pitch, noise, EQ, filtri)
- Salva in `archive/output/` con metadata `.txt`

**Esempio utilizzo**:
```bash
cd ADV_ML/scripts
python3 generate_variants.py --coarse-only   # Sweep coarse
python3 generate_variants.py --fine-only     # Sweep fine
```

### 7.3 Estrazione Feature MFCC

**Script**: `ADV_ML/scripts/extract_features.py`

**Feature estratte**:
- **MFCC** (13 coefficienti): Rappresentazione compatta spettro audio
- **Media temporale**: Riduce dimensionalità (13 valori per file)
- **Etichette**: 0 = original, 1 = obfuscated

**Output**:
- `features/X.npy`: Matrice (n_samples, 13)
- `features/y.npy`: Vettore (n_samples,)

**Utilizzo futuro** (Step 3):
1. Addestrare classificatore SVM/RF/CNN su dataset R₀+A
2. Testare accuracy su dataset R₁+A (diverso R₁)
3. Misurare degradazione accuracy come metrica di efficacia

### 7.4 Test Soggettivi con CSV

**File**: `ADV_ML/tests/subjective_results.csv`

**Schema**:
```csv
subject,file,value,type,perceived_change,severity,notes,timestamp
Francesco,auto_pitch_p100.wav,100,pitch,Y,2,Appena percettibile,2025-10-30T14:23:10
Francesco,auto_noise_35.wav,35,noise,N,1,Impercettibile,2025-10-30T14:25:43
```

**Processo**:
1. Generare varianti con `generate_audible_variants.py`
2. Ascoltare con `human_listen_and_label.py` (CLI interattiva)
3. Annotare percezione (Y/N) e severity (1-5)
4. Analizzare risultati per determinare range finali

**Script CLI**:
```bash
python3 ADV_ML/tests/human_listen_and_label.py \
  ADV_ML/tests/output/audible_variants/auto \
  --subject Francesco --types pitch noise eq_tilt --randomize
```

-----------------------------------------------------------------------------------------------------------------

## 8. Step 3: Randomizzazione Parametri (PLACEHOLDER)

**⚠️ NOTA**: Questa sezione descrive il lavoro **pianificato** ma **non ancora implementato**. L'implementazione di Step 3 avverrà dopo il completamento della calibrazione soggettiva per tutti i suoni chiave del gioco.

### 8.1 Obiettivi Step 3

Nello Step 2 (attuale), tutti i parametri sono **deterministici**: stesso suono = sempre stessi parametri (midpoint dei range). Step 3 introdurrà:

1. **Randomizzazione range**: Invece di midpoint fisso, ogni volta che un suono viene caricato, i parametri verranno scelti **casualmente** all'interno dei range calibrati `[min, max]`.

2. **RNG vero**: Attualmente uso seed fisso (12345/12346) per reproducibilità. Step 3 userà seed da `std::chrono` o `/dev/urandom` per entropia reale.

3. **CLI override**: Comandi come `--obf-override pitch=150 eq=6 snr=30` per testare parametri specifici senza modificare CSV.

4. **CLI select**: Comando `--obf-select pitch,eq_tilt` per abilitare solo effetti specifici (utile per debug).

5. **Distribuzione non uniforme** (opzionale avanzato): Invece di `uniform(min, max)`, usare distribuzioni Beta/Normal concentrate vicino a "sweet spot".

### 8.2 Implementazione Pianificata

**Cambio in `audio_runtime_obf.cpp`**:

```cpp
// Step 2 (attuale): Midpoint deterministico
int pitch_cents = (profile.min_pitch_cents + profile.max_pitch_cents) / 2;

// Step 3 (futuro): Random uniforme
std::random_device rd;
std::mt19937 gen(rd());  // Seed da entropia reale
std::uniform_int_distribution<> dis(profile.min_pitch_cents, profile.max_pitch_cents);
int pitch_cents = dis(gen);
```

**Per ogni suono caricato**:
- Genera parametri casuali all'interno dei range
- Applica trasformazioni
- Log parametri effettivi (per audit/debug)

### 8.3 Collegamento con Modello R₀/R₁

La randomizzazione è **essenziale** per il modello R₀ vs R₁:

**Senza randomizzazione** (Step 2):
- Ogni client ha gli stessi parametri fissi (es. sempre pitch +150 cents)
- Un attaccante può registrare una volta, addestrare su quei parametri fissi, e il suo modello funzionerà sempre
- **Non c'è invalidazione del modello nel tempo**

**Con randomizzazione** (Step 3):
- Ogni sessione/mappa ha parametri diversi (es. pitch +120, +280, +350 cents in tre partite diverse)
- Un attaccante che addestra su R₀ (registrato in una partita) avrà accuracy degradata in partite successive con R₁ diverso
- **Il modello dell'attaccante invecchia rapidamente**

### 8.4 Configurazione Seed per Sessione

**Opzione 1: Seed per Client** (stesso per tutta la sessione):
```cpp
// All'avvio client, genera un seed unico
uint64_t session_seed = std::chrono::system_clock::now().time_since_epoch().count();
// Usa questo seed per tutti i suoni in questa sessione
```
**Pro**: Reproducibile (stesso seed = stessi suoni in replay)  
**Contro**: Un attaccante può registrare una sessione intera e addestrare su quei parametri specifici

**Opzione 2: Seed per Mappa** (cambia ogni mappa):
```cpp
// All'inizio di ogni mappa, rigenera seed
uint64_t map_seed = hash(map_name) ^ std::chrono::now();
```
**Pro**: Parametri diversi per ogni mappa  
**Contro**: Più variabilità, ma attaccante può adattarsi per-map

**Opzione 3: Seed per Suono** (cambia ogni caricamento):
```cpp
// Ogni volta che un suono viene caricato, seed diverso
uint64_t sound_seed = std::chrono::now() ^ hash(sound_name);
```
**Pro**: Massima variabilità  
**Contro**: Stesso suono può avere parametri diversi in partita (meno coerente)

**Scelta consigliata**: **Opzione 1 (seed per sessione)** per Step 3 iniziale, con possibilità di passare a Opzione 2 (per mappa) in future iterazioni.

### 8.5 Test e Validazione

Dopo implementazione Step 3:
1. **Test in-game**: Verificare che parametri varino tra sessioni
2. **Log audit**: Registrare tutti i parametri applicati per post-analysis
3. **Percezione**: Confermare che range randomizzati siano ancora accettabili
4. **ML validation**: Addestrare modello su R₀, testare su R₁ (con seed diverso), misurare degradazione accuracy

---

## 9. Validazione Machine Learning (Lavoro Futuro)

**⚠️ NOTA**: Questa sezione descrive il lavoro ML **pianificato** ma **non ancora eseguito**. L'esecuzione dei test ML avverrà dopo il completamento di Step 3 (randomizzazione), come richiesto dal professore, per testare il sistema in condizioni realistiche con rumori variabili R₁.

### 9.1 Dataset e Feature Extraction

**Dataset attuale** (preparato in `ADV_ML/`):
- 6 file audio: 3 originali + 3 obfuscated (pitch +100 cents)
- Feature estratte: 13 MFCC (Mel-Frequency Cepstral Coefficients)
- Formato: `X.npy` (6×13), `y.npy` (6,)

**Dataset esteso** (da generare per validazione finale):
- 100-200 file per classe (original vs obfuscated)
- Diversi parametri R₀ (es. pitch ±50-200, noise 30-40 dB, EQ ±3)
- Diversi parametri R₁ (es. pitch ±100-500, noise 20-35 dB, EQ ±6)
- Bilanciamento 50/50 tra classi

**Feature usate**:
- MFCC standard (13 coefficienti)
- Media temporale per ridurre dimensionalità
- Possibile estensione: spectral centroid, ZCR, chroma

### 9.2 Classificatore Baseline

**Modello proposto**: SVM con kernel RBF

**Addestramento**:
1. Split 80/20 train/test su dataset R₀+A
2. Cross-validation 5-fold per tuning hyperparameter (C, gamma)
3. Valutazione accuracy, precision, recall, F1-score
4. **Accuracy attesa**: ~90-95% (task "facile" per ML)

**Alternative** (se tempo disponibile):
- Random Forest (più robusto al noise)
- CNN su mel-spectrogrammi (più potente ma richiede più dati)
- Ensemble (SVM + RF + CNN)

### 9.3 Test Adversarial (R₀ vs R₁)

**Scenario di test**:
1. Addestrare modello su R₀+A (es. pitch +100, noise 40 dB)
2. Testare su R₀+A (control) → accuracy ~95%
3. Testare su R₁+A (es. pitch +300, pink noise 35 dB, EQ +3 dB) → accuracy attesa ~60-70%
4. **Degradazione** = (accuracy_R₀ - accuracy_R₁) / accuracy_R₀ × 100

**Metriche di successo**:
- Degradazione ≥20% → sistema efficace
- Degradazione ≥30% → sistema molto efficace
- Degradazione <10% → sistema inefficace (attaccante troppo robusto)

### 9.4 Contromisure dell'Attaccante (Analisi)

**Data Augmentation**:
- L'attaccante potrebbe addestrare su dataset con pitch shift random
- **Test**: Addestrare su R₀_augmented (pitch ±200 random) → testare su R₁ (pitch +300 fisso)
- **Ipotesi**: Degradazione si riduce ma non scompare (combinazione multi-effetto resiste)

**Feature Invarianti**:
- Usare feature normalizzate (MFCC con mean subtraction)
- **Test**: Confrontare accuracy su MFCC raw vs normalized
- **Ipotesi**: Normalizzazione riduce efficacia obfuscation per pitch, ma non per noise/EQ

**Adversarial Training**:
- Addestrare esplicitamente su coppie (R₀+A, R₁+A)
- **Contromisura**: Aumentare spazio di trasformazione (R₀, R₁, R₂, ...)
- **Limite**: Spazio infinito → impossibile coprire tutto

### 9.5 Pianificazione Esperimenti

**Esperimento 1: Single-effect obfuscation**:
- R₀: pitch +100 → R₁: pitch +300
- R₀: white noise 40 dB → R₁: white noise 30 dB
- R₀: EQ +3 dB → R₁: EQ -6 dB
- **Obiettivo**: Misurare efficacia singolo effetto

**Esperimento 2: Multi-effect obfuscation**:
- R₀: pitch +100 + noise 40 → R₁: pitch +300 + pink noise 35 + EQ +3
- **Obiettivo**: Misurare efficacia combinazione

**Esperimento 3: Augmentation robustness**:
- Training su R₀_augmented (pitch ±200 random)
- Test su R₁ (pitch +500 fisso + EQ +6 + HP 200)
- **Obiettivo**: Testare limite del sistema vs attaccante sofisticato

**Output attesi**:
- Tabelle accuracy per ogni esperimento
- Grafici degradation vs parametri trasformazione
- Confusion matrix per analisi errori
- Esempi audio "hard" (classificati male)

### 9.6 Integrazione Risultati ML nella Tesi

Dopo l'esecuzione degli esperimenti, aggiornerò questa sezione con:
1. **Risultati quantitativi**: Tabelle accuracy, precision, recall, F1
2. **Grafici**: SNR vs accuracy, parametri vs degradazione
3. **Analisi qualitativa**: Quali trasformazioni sono più efficaci
4. **Confronto con letteratura**: Riferimenti a paper su adversarial audio
5. **Discussione limitazioni**: Quando il sistema fallisce, perché, come migliorare

**File da aggiungere**:
- `ADV_ML/ml_results/` con CSV risultati
- `ADV_ML/plots/accuracy_degradation.png`
- Sezione estesa nella tesi con analisi completa

---

## 10. Discussione e Limitazioni

### 10.1 Efficacia del Sistema

**Punti di forza**:
1. **Implementazione reale**: Non solo teoria, ma sistema funzionante in gioco complesso
2. **Calibrazione empirica**: Range basati su test soggettivi reali, non su assunzioni
3. **Modulare ed estendibile**: Facile aggiungere nuovi effetti DSP
4. **Zero overhead runtime**: Trasformazioni applicate al caricamento (init-time), non in-game loop
5. **Trasparente al gameplay**: Tutti i test hanno confermato che le trasformazioni sono impercettibili o appena percettibili

**Limitazioni identificate**:
1. **Dataset ML limitato**: Solo 6 samples per proof-of-concept, serve espansione 100-200×
2. **Test su singolo utente**: Percezione soggettiva basata solo su me stesso (serve panel 10-20 persone)
3. **Un solo suono calibrato**: Solo weapon/usp completamente testato (servono altri suoni chiave)
4. **Nessun test contro cheat reale**: Non ho implementato un cheat ML funzionante per misurare degradazione accuracy effettiva
5. **Hardware limitato**: Test solo su macOS M1 (risultati potrebbero variare su Windows/Linux)

### 10.2 Confronto con Letteratura

La letteratura su adversarial audio si concentra principalmente su:
- **Speech recognition attacks** [Carlini et al., 2018]: Perturbazioni small-norm che degradano ASR
- **Audio watermarking** [Cox et al., 2007]: Embedding robusto contro trasformazioni
- **Music genre classification** [Sturm, 2013]: Robustezza feature MFCC a trasformazioni

**Differenza con il mio lavoro**:
- Focus su **gaming audio** (percussivo, breve, contesto rumoroso)
- Vincolo **percettibilità umana** (non solo robustness matematica)
- Trasformazioni **multiple combinate** (non singola perturbazione)
- Applicazione **runtime** (non pre-processing offline)

### 10.3 Estensioni Future

**Step 3 (Randomizzazione)**:
- Implementare sampling non uniforme (Beta distribution)
- Seed variabile per sessione/mappa
- CLI/ENV override per testing rapido

**Espansione suoni**:
- Calibrare range per altri suoni chiave (shotgun, sniper, footsteps, reload)
- Testare combinazioni multi-effetto specifiche per categoria audio

**Validazione ML completa**:
- Generare dataset 100-200 samples per classe
- Addestrare SVM, RF, CNN
- Misurare degradation accuracy R₀ → R₁
- Testare robustness vs data augmentation

**Ottimizzazioni performance**:
- Parallelizzare processing audio (multi-threading)
- Cache di buffer processati (evitare ri-processing)
- GPU acceleration per effetti pesanti (FFT-based)

**Difese avanzate**:
- Distribuzione asimmetrica (più peso su valori sweet spot)
- Cambio parametri periodico (weekly/patch)
- Telemetria server (detect anomalie client-side)

---

## 11. Conclusioni

### 11.1 Cosa Ho Imparato

Questo progetto è stato per me molto più di un esercizio tecnico. Ho imparato:

**Competenze tecniche**:
- **Audio DSP reale**: Non teoria astratta, ma problemi concreti (aliasing, buffer overflow, frame mismatch, clipping)
- **Debugging di sistema**: Capire linker macOS, framework deprecated, path librerie dinamiche
- **C++ moderno**: Uso `std::vector`, `try/catch`, `#ifdef` per portabilità
- **Build system**: Make, Makefile, variabili platform-specific, linking order
- **Python per ML**: Virtual environment, numpy, librosa, soundfile, feature extraction

**Competenze metodologiche**:
- **Ricerca sistematica**: Non improvvisare, ma pianificare → eseguire → misurare → iterare
- **Validazione empirica**: Verificare assunzioni teoriche con test reali (letteratura ≠ realtà applicativa)
- **Documentazione scientifica**: Scrivere in modo rigoroso ma leggibile, con riferimenti, tabelle, grafici
- **Test soggettivi**: Progettare protocolli per raccogliere percezione umana in modo strutturato

**Competenze personali**:
- **Perseveranza**: Problema OpenAL mi ha bloccato 6 ore, ho resistito alla tentazione di workaround hacky
- **Curiosità**: Ogni errore era un'opportunità di capire qualcosa di nuovo (es. come funzionano framework macOS)
- **Autonomia**: Ho dovuto trovare soluzioni senza supervisione diretta, usando documentazione, forum, trial-and-error

### 11.2 Contributo Originale

Il contributo principale di questa tesi è la **dimostrazione pratica** del modello **R₀+A vs R₁+A** in un contesto di gaming reale:

1. **Sistema funzionante**: Non solo simulazione, ma implementazione C++ completa in gioco complesso
2. **Calibrazione empirica**: Range di trasformazione basati su test soggettivi reali, non su letteratura musicale
3. **Framework estendibile**: Architettura modulare che permette di aggiungere nuovi effetti DSP facilmente
4. **Workflow completo**: Dall'analisi codice alla calibrazione range, passando per test automatici e manuali
5. **Dataset preparato**: Infrastruttura ADV_ML/ pronta per validazione ML finale

**Validazione ML** (da completare): Dimostrerò che un modello addestrato su R₀+A subisce degradazione accuracy ≥20-30% quando testato su R₁+A, confermando che l'obfuscation audio è una tecnica efficace contro cheat ML.

### 11.3 Applicabilità ad Altri Giochi

Il sistema sviluppato per AssaultCube è **generalizzabile** ad altri giochi con caratteristiche simili:

**Requisiti minimi**:
- Usa OpenAL o libreria audio simile (SDL_mixer, FMOD, Wwise)
- Asset audio locali sul client (.ogg, .wav, .mp3)
- Possibilità di hook pre-buffer upload (equivalente a `alBufferData`)

**Giochi candidati**:
- **Cube 2: Sauerbraten** (stesso engine di AssaultCube)
- **Quake III Arena** (open-source, OpenAL)
- **Urban Terror** (mod Quake III)
- **Xonotic** (FPS open-source, OpenAL)

**Adattamenti necessari**:
- Identificare punto di hook specifico per architettura audio
- Calibrare range per tipologie audio diverse (sci-fi vs realistico)
- Integrare con sistema anti-cheat esistente (se presente)

### 11.4 Riflessione Finale

Quando ho iniziato, pensavo che il pitch shift fosse "troppo semplice" per essere efficace. I test mi hanno dimostrato che:

1. **Semplice ≠ inefficace**: Anche trasformazioni lineari base possono complicare significativamente il task per attaccanti automatizzati
2. **Percezione umana è resiliente**: Shift che sembrano "evidenti" in ascolto critico sono quasi impercettibili durante gameplay reale
3. **Sicurezza è un gioco di layer**: Nessuna singola tecnica è perfetta, ma combinazioni multiple alzano il costo d'attacco
4. **Empiria batte teoria**: Range trovati empiricamente (±200-500 cents per pistol) sono molto maggiori di quanto suggerito dalla letteratura musicale (±20 cents)

Il limite più grande di questo lavoro è **non aver ancora testato contro un cheat reale**. Lo step finale critico sarà:
1. Implementare Step 3 (randomizzazione)
2. Generare dataset R₀ e R₁ con parametri randomizzati
3. Addestrare classificatore ML su R₀+A
4. Misurare accuracy su R₁+A
5. Documentare degradation quantitativa

Questo è un progetto che completerò nelle prossime 2 settimane e che dimostrerà in modo quantitativo l'efficacia del sistema contro cheat audio basati su machine learning.

---

## 12. Bibliografia

[1] Cox, I. J., Miller, M. L., Bloom, J. A., Fridrich, J., & Kalker, T. (2007). *Digital Watermarking and Steganography*. Morgan Kaufmann.

[2] Carlini, N., & Wagner, D. (2018). "Audio Adversarial Examples: Targeted Attacks on Speech-to-Text." *IEEE Security and Privacy Workshops*.

[3] Zwicker, E., & Fastl, H. (1999). *Psychoacoustics: Facts and Models*. Springer.

[4] Moore, B. C. J. (2012). *An Introduction to the Psychology of Hearing* (6th ed.). Brill.

[5] Yan, J., & Randell, B. (2005). "A Systematic Classification of Cheating in Online Games." *Proceedings of 4th ACM SIGCOMM Workshop on Network and System Support for Games*.

[6] Sturm, B. L. (2013). "Classification Accuracy Is Not Enough: On the Evaluation of Music Genre Recognition Systems." *Journal of Intelligent Information Systems*.

[7] OpenAL Specification and Programmer's Guide. (2024). https://www.openal.org/

[8] Farnell, A. (2010). *Designing Sound*. MIT Press.

[9] Zölzer, U. (Ed.). (2011). *DAFX: Digital Audio Effects* (2nd ed.). Wiley.

[10] Smith, J. O. (2011). *Spectral Audio Signal Processing*. W3K Publishing.

[11] SoundTouch Audio Processing Library. (2024). https://www.surina.net/soundtouch/

[12] libsndfile Documentation. (2024). http://www.mega-nerd.com/libsndfile/

---

## Appendice A: Comandi Rapidi

### Build Client
```bash
cd "/Users/francesco03/Documents/GitHub/AssaultCube Server/AC/source/src"
make clean && make client -j
```

### Test In-Game (con obfuscation)
```bash
cd "/Users/francesco03/Documents/GitHub/AssaultCube Server/AC"
AC_AUDIO_OBF=1 ./ac_client
```

### Modifica CSV per Test
```bash
cat > audio_obf_config.csv << 'EOF'
file_name,min_pitch_cents,max_pitch_cents,noise_type,noise_snr_db,min_freq,max_freq,eq_tilt_db,hp_hz,lp_hz
weapon/usp,0,0,white,35,,,0,0,0
EOF
```

### Generazione Varianti Audio
```bash
cd ADV_ML/scripts
python3 generate_variants.py --coarse-only
```

### Estrazione Feature MFCC
```bash
cd ADV_ML/scripts
python3 extract_features.py
```

---

## Appendice B: Struttura File Progetto

```
AssaultCube Server/
├── AC/
│   ├── source/src/
│   │   ├── audio_runtime_obf.h         # Header framework obfuscation
│   │   ├── audio_runtime_obf.cpp       # Implementation DSP effects
│   │   ├── openal.cpp                  # Hook integrato
│   │   ├── main.cpp                    # Inizializzazione
│   │   ├── Makefile                    # Build system modificato
│   │   └── ac_client                   # Eseguibile compilato
│   ├── audio_obf_config.csv            # Configurazione per-sound
│   ├── packages/audio/                 # Asset audio originali
│   └── .cursor-output/
│       ├── GUIDA_CALIBRAZIONE_RANGE.md
│       ├── CALIBRAZIONE_FINALE_USP.md
│       ├── RANGE_FINALE_USP.txt
│       └── final_patch_summary.txt
├── ADV_ML/
│   ├── README.md                       # Guida tecnica completa
│   ├── dataset/
│   │   ├── original/
│   │   └── obfuscated/
│   ├── features/
│   │   ├── X.npy
│   │   └── y.npy
│   ├── scripts/
│   │   ├── audio_converter.py
│   │   ├── extract_features.py
│   │   ├── generate_variants.py
│   │   └── generate_reports.py
│   ├── tests/
│   │   ├── run_all_tests.sh
│   │   ├── TEST_RESULTS_COARSE.csv
│   │   ├── TEST_RESULTS_FINE.csv
│   │   └── subjective_results.csv
│   ├── listening_set/
│   ├── plots/
│   ├── docs/
│   └── archive/
└── TESI_ANTICHEAT.md                   # Questo file

```

---

**Nota Finale**: Questo documento rappresenta lo stato del progetto al 03/11/2025, dopo il completamento di Step 1 (pitch base), Step 2 (multi-perturbazione deterministica), e calibrazione soggettiva per weapon/usp. Rimangono da completare Step 3 (randomizzazione) e validazione ML finale, previsti entro 15/11/2025.

---

**Parole totali**: ~15000  
**Pagine equivalenti**: ~50 (font 12pt, margini standard)  
**Versione**: 3.0 (completa e narrativa)

**Autore:** Francesco Carcangiu  
**Data Completamento Documento:** 03 Novembre 2025
