# Discorso per il Professore Relatore - Fase 1 & 2

///Dopo aver completato l'implementazione C++ del sistema di obfuscation audio, mi sono concentrato sulla creazione di un framework Python per replicare offline gli stessi effetti audio e applicarli ai dataset del collega per testare l'efficacia contro modelli di machine learning.

Ho implementato un modulo Python (`audio_effects.py`) che replica esattamente la logica DSP del client C++: pitch shift usando librosa (equivalente a SoundTouch), white noise e pink noise generati con numpy seguendo le stesse formule matematiche del client, EQ tilt e filtri HP/LP usando scipy con gli stessi coefficienti Butterworth. Tutti gli effetti sono allineati ai range calibrati per la pistola nel file CSV di configurazione.

Successivamente ho creato uno script (`offline_perturb.py`) che permette di applicare queste perturbazioni offline ai file FLAC del dataset del collega. Lo script carica i FLAC, applica una perturbazione specifica (pitch, noise, EQ, filtri o combinazioni), estrae le feature nello stesso formato del collega e genera `X_test_pert` pronto per essere usato nel modello ML. Supporta modalità fixed (valore fisso per test controllati) e random (come nel client, con distribuzione uniforme).

Come suggerito, ho implementato un sistema di sweep parametrico per valutare la correlazione tra livello di rumore e efficacia nel confondere il modello. Ho creato script dedicati (`sweep_noise_levels.py` e `evaluate_perturbation_effectiveness.py`) che permettono di testare diversi livelli di SNR (da 50 dB a 10 dB) e generare automaticamente grafici di correlazione SNR vs Accuracy. Questo permetterà di identificare soglie critiche e capire quale livello di perturbazione è più efficace.

///Ho documentato tutto in due guide: una tecnica completa (`FASE1_FASE2_RIEPILOGO.md`) che spiega l'architettura, gli algoritmi e le strategie di test, e una guida pratica step-by-step (`GUIDA_OFFLINE_PERTURB_STEP_BY_STEP.md`) pensata per studenti, con esempi concreti di comandi e pseudocodice per l'integrazione con il codice ML del collega.

Ho anche corretto un problema importante: inizialmente il rumore veniva aggiunto anche al silenzio, ma come suggerito dal professore, ora viene applicato solo durante lo sparo (dove c'è segnale). Questo simula meglio il comportamento reale del gioco dove il rumore appare solo quando viene riprodotto il suono della pistola.

Un'importante considerazione emersa durante i test è la differenza tra effetti audio in-game e offline: in gioco gli spari durano pochi millisecondi, mentre gli audio del dataset del collega sono più lunghi (diversi secondi). Questo significa che per ottenere la stessa percettibilità del rumore, in-game posso permettermi valori SNR meno aggressivi rispetto a quelli necessari offline. Durante l'ascolto comparativo tra audio originali e modificati, ho notato che per rendere il rumore chiaramente percettibile negli audio lunghi del dataset servono SNR più bassi (più rumore) rispetto a quanto necessario in-game dove il suono è più breve e il rumore risulta più evidente anche con valori SNR più alti.

Per la creazione del dataset, ho implementato sia modalità fixed (valore fisso per test controllati e riproducibili) che random (come nel client, con distribuzione uniforme per massimizzare la variabilità e rendere più difficile l'apprendimento del modello). La scelta tra le due dipende dall'obiettivo: fixed per analisi parametriche precise, random per simulare meglio il comportamento reale del sistema in produzione.

Il sistema è ora pronto per essere usato: il collega può generare dataset perturbati con diversi livelli di rumore, valutarli sul suo modello RandomForest e analizzare come la degradazione dell'accuracy varia in funzione dell'intensità della perturbazione. Questo ci permetterà di dimostrare empiricamente l'efficacia del sistema di obfuscation contro algoritmi di riconoscimento automatico.

---

# Speech for my Supervisor - Phase 1 & 2



I implemented a Python module (`audio_effects.py`) that exactly replicates the DSP logic from the C++ client: pitch shift using librosa (equivalent to SoundTouch), white noise and pink noise generated with numpy following the same mathematical formulas as the client, EQ tilt and HP/LP filters using scipy with the same Butterworth coefficients. All effects are aligned with the calibrated ranges for the pistol in the CSV configuration file.

Then I created a script (`offline_perturb.py`) that allows applying these perturbations offline to the Giovanni's FLAC dataset files. The script loads FLAC files, applies a specific perturbation (pitch, noise, EQ, filters, or combinations), extracts features in the same format as of Giovanni, and generates `X_test_pert` ready to be used in the ML model. It supports fixed mode (fixed value for controlled tests) and random mode (like the client, with uniform distribution).

As suggested, I implemented a parametric sweep system to evaluate the correlation between noise level and effectiveness in confusing the model. I created dedicated scripts (`sweep_noise_levels.py` and `evaluate_perturbation_effectiveness.py`) that allow testing different SNR levels (from 50 dB to 10 dB) and automatically generate SNR vs Accuracy correlation plots. This will allow identifying critical thresholds and understanding which perturbation level is most effective.

I also fixed an important issue: initially noise was added to silence too, but as suggested by the professor, it's now applied only during the gunshot (where there's signal). This better simulates the real game behavior where noise appears only when the pistol sound is played.

An important consideration that emerged during testing is the difference between in-game and offline audio effects: 
in-game gunshots last a few milliseconds, while the colleague's dataset audio files are longer (several seconds). This means that to achieve the same noise perceptibility, in-game I can afford less aggressive SNR values compared to those needed offline. During comparative listening between original and modified audio, 

I noticed that to make noise clearly perceptible in the long dataset audio files, lower SNRs (more noise) are needed compared to what's necessary in-game, where the shorter sound duration makes noise more evident even with higher SNR values.

For dataset creation, I implemented both fixed mode (fixed value for controlled and reproducible tests) and random mode (like the client, with uniform distribution to maximize variability and make model learning more difficult). The choice between the two depends on the objective: fixed for precise parametric analysis, random to better simulate real system behavior in production.

The system is now ready to use: the colleague can generate perturbed datasets with different noise levels, evaluate them on his RandomForest model, and analyze how accuracy degradation varies as a function of perturbation intensity. This will allow us to empirically demonstrate the effectiveness of the obfuscation system against automatic recognition algorithms.

---


### 🎧 Audio da Far Ascoltare

**Cartella:** `ADV_ML/demo_audio_for_professors/`

1. **Inizia con originale** (`00_ORIGINALI/`)
   - Fai ascoltare uno sparo originale
   - Spiega: "Questo è lo sparo senza modifiche"

2. **Pitch Shift** (`01_PITCH/`)
   - Confronta originale vs P2_medium (+150 cents)
   - Mostra differenza acuto/grave
   - "Questo modifica la frequenza mantenendo la durata"

3. **White Noise** (`02_WHITE_NOISE/`)
   - Confronta originale vs W2_medium (SNR 40 dB)
   - "Aggiunge rumore solo durante lo sparo, non sul silenzio"
   - Mostra che il silenzio rimane pulito

4. **Pink Noise** (`03_PINK_NOISE/`)
   - Confronta con white noise
   - "Rumore più naturale, meno fastidioso"

### 💻 Codice da Mostrare
1. **Implementazione C++** (`AC/source/src/audio_runtime_obf.cpp`)
   - Mostra hook OpenAL (righe ~80-120)
   - Mostra funzione di randomizzazione (righe ~650-700)
   - Spiega: "Sistema minimamente invasivo, hook solo quando necessario"

2. **Sistema Python** (`ADV_ML/audio_effects.py`)
   - Mostra funzione `add_white_noise()` con `only_on_signal=True`
   - Spiega maschera: "Rumore solo dove c'è segnale"
   - Mostra corrispondenza con formule C++

3. **Script Generazione** (`ADV_ML/offline_perturb.py`)
   - Mostra esempio comando
   - Spiega output CSV
   - "Genera dati pronti per test ML"






**Example command with inline comments:**

```bash
# Activate Python virtual environment (contains required dependencies: librosa, numpy, scipy, soundfile)
source ADV_ML/venv/bin/activate                    

# Run offline perturbation script to generate ML-ready dataset
python ADV_ML/offline_perturb.py \                 
  --dataset-root COLLEAGUE_BSc_Thesis/Data/audio/audio_loopback_flac \  # Input: FLAC files from colleague's dataset
  --perturbation pitch \                                                  # Apply pitch shift effect (alternative: noise, eq, highpass, lowpass)
  --mode fixed \                                                          # Use fixed value (not random) for reproducible, controlled tests
  --cents 150 \                                                           # Shift pitch by +150 cents (1.5 semitones higher, P2_medium level)
  --num-samples 50 \                                                      # Process 50 audio files from the dataset
  --output-csv ADV_ML/output/pistol_pitch_P2_medium.csv \               # Output: CSV file with extracted features in same format as original dataset
  --verbose                                                               # Show detailed progress for each processed file
```

**What happens when the script runs:**

1. **Loads FLAC files**: Reads audio files from the specified dataset directory
2. **Applies perturbation**: For each file, applies pitch shift (+150 cents) using librosa (same algorithm as C++ SoundTouch)
3. **Extracts features**: Computes audio features (MFCC, spectral features, etc.) in the exact same format as the colleague's ML pipeline
4. **Saves to CSV**: Writes features to `pistol_pitch_P2_medium.csv` with same column structure as original dataset
5. **Ready for ML**: The output CSV can be directly loaded as `X_test_pert` and compared with original `X_test` to measure accuracy degradation

**Output format**: The CSV contains one row per audio file, with feature columns matching the original dataset format. This allows direct evaluation: load both original and perturbed CSVs, run predictions, and compare accuracy to measure adversarial effectiveness.




 python ADV_ML/offline_perturb.py \                 
  --dataset-root COLLEAGUE_BSc_Thesis/Data/audio/audio_loopback_flac \
  --perturbation pitch \
  --mode fixed \
  --cents 150 \
  --num-samples 50 \
  --output-csv ADV_ML/output/pistol_pitch_P2_medium.csv \
  --verbose