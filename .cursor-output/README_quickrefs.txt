================================================================================
   ASSAULTCUBE AUDIO ANTICHEAT - QUICK REFERENCE
================================================================================

Progetto di tesi: Anti-cheat basato su analisi audio per rilevare modifiche
al pitch dei suoni di gioco (footsteps, gunfire, etc.)

Ultima modifica: 23 Ottobre 2025

================================================================================
📁 STRUTTURA DEL PROGETTO
================================================================================

AssaultCube Server/
│
├── AC/                          # Game files AssaultCube
│   ├── packages/audio/          # File audio originali del gioco
│   ├── tools/pitch_test         # Tool per testare pitch shift
│   └── config/                  # Configurazioni server
│
├── ADV_ML/                      # ★ NUOVO: Adversarial Machine Learning
│   ├── SETUP_ADV_ML.md          # Guida setup completa
│   ├── dataset/                 # Dataset audio
│   │   ├── original/            # Audio non modificati
│   │   └── obfuscated/          # Audio con pitch shift
│   ├── scripts/                 # Script Python ML
│   │   └── extract_features.py  # Estrazione MFCC
│   └── features/                # Feature estratte (X.npy, y.npy)
│
├── docs-it/                     # Documentazione italiana
│   ├── README.md
│   ├── TEST_PLAN.md
│   └── PROJECT_FULL_LOG.md
│
├── docs-en/                     # Documentazione inglese
│   └── Research_Proposal_Audio_AntiCheat.md
│
├── STATO_PROGETTO.md            # Stato avanzamento progetto
├── TESI_ANTICHEAT.md            # Contenuto tesi (italiano)
└── THESIS_ANTICHEAT.md          # Contenuto tesi (inglese)

================================================================================
🎵 ADVERSARIAL MACHINE LEARNING - SETUP
================================================================================

📍 FASE CORRENTE: Setup iniziale e estrazione feature

OBIETTIVO:
Usare Machine Learning per rilevare modifiche audio (pitch shift) e studiare
come gli attaccanti possono aggirare questi sistemi.

──────────────────────────────────────────────────────────────────────────────
STEP 1: Setup Ambiente
──────────────────────────────────────────────────────────────────────────────

Posizione: ADV_ML/

1. Crea virtual environment:
   $ cd ADV_ML
   $ python3 -m venv venv
   $ source venv/bin/activate  # macOS/Linux

2. Installa dipendenze:
   $ pip install --upgrade pip
   $ pip install librosa numpy scikit-learn matplotlib tqdm secml-torch
   # NOTA: Usiamo SecML-Torch (versione moderna) invece di SecML

3. Verifica installazione:
   $ python3 -c "import librosa, sklearn, numpy, matplotlib, tqdm, secmlt, torch; print('OK')"
   $ python3 -c "import secmlt, torch; print('SecML-Torch:', secmlt.__version__)"

──────────────────────────────────────────────────────────────────────────────
STEP 2: Preparazione Dataset
──────────────────────────────────────────────────────────────────────────────

STRUTTURA:
ADV_ML/dataset/
├── original/     → File .wav originali del gioco
└── obfuscated/   → File .wav con pitch shift applicato

COME CREARE DATASET:

a) File originali:
   $ cp AC/packages/audio/weapon/*.wav ADV_ML/dataset/original/

b) File obfuscati (con pitch_test):
   $ cd AC/tools
   $ ./pitch_test ../packages/audio/weapon/machinegun.ogg 5
   $ cp results/*_shifted.wav ../../ADV_ML/dataset/obfuscated/

REQUISITI MINIMI:
- Almeno 20 file per categoria
- Formato .wav
- Sample rate uniforme (preferibilmente 44100 Hz o 48000 Hz)

──────────────────────────────────────────────────────────────────────────────
STEP 3: Estrazione Feature (MFCC)
──────────────────────────────────────────────────────────────────────────────

SCRIPT: ADV_ML/scripts/extract_features.py

COSA FA:
1. Legge tutti i .wav da original/ e obfuscated/
2. Estrae MFCC (Mel-Frequency Cepstral Coefficients)
3. Salva feature in X.npy e label in y.npy

ESECUZIONE:
$ cd ADV_ML/scripts
$ python3 extract_features.py

OUTPUT:
ADV_ML/features/
├── X.npy    → Matrice feature (n_samples, 13)
└── y.npy    → Etichette (0=original, 1=obfuscated)

PARAMETRI MFCC:
- n_mfcc = 13         (numero di coefficienti)
- sample_rate = 22050 (Hz)
- hop_length = 512
- n_fft = 2048

──────────────────────────────────────────────────────────────────────────────
STEP 4: Prossimi Step (TODO)
──────────────────────────────────────────────────────────────────────────────

[ ] train_classifier.py    → Addestrare SVM su feature MFCC
[ ] evaluate_model.py      → Testare accuratezza e metriche
[ ] adversarial_attack.py  → Creare esempi adversarial
[ ] defense_strategy.py    → Implementare difese

================================================================================
🔧 PITCH TEST - TESTING MANUALE
================================================================================

TOOL: AC/tools/pitch_test

COMPILAZIONE:
$ cd AC/tools
$ ./build_pitch_test.sh

USO:
$ ./pitch_test <input.ogg> <semitones>

ESEMPI:
$ ./pitch_test ../packages/audio/weapon/machinegun.ogg 5    # +5 semitoni
$ ./pitch_test ../packages/audio/player/footsteps.ogg -3    # -3 semitoni

OUTPUT:
- results/<filename>_<shift>.wav

RANGE CONSIGLIATI:
- Footsteps: ±2-4 semitoni (rilevante per gameplay)
- Gunfire: ±3-6 semitoni

================================================================================
📚 CONCETTI CHIAVE
================================================================================

MFCC (Mel-Frequency Cepstral Coefficients):
    Rappresentazione compatta dell'audio che cattura caratteristiche timbriche.
    Da migliaia di sample → 13 numeri che descrivono "com'è fatto" il suono.
    
    Perché si usano?
    ✓ Dimensionalità ridotta
    ✓ Cattura timbro e tono
    ✓ Standard in speech/music processing
    ✓ Efficiente per ML

ADVERSARIAL MACHINE LEARNING:
    Studio di come ingannare modelli ML e come difendersi.
    
    Scenario AntiCheat:
    • Attaccante → modifica audio senza essere rilevato
    • Difensore → rileva modifiche con ML
    • Adversarial Attack → modifica "intelligente" che inganna il modello
    • Adversarial Defense → rendere il modello più robusto

SECML-TORCH:
    Libreria Python moderna per Adversarial ML con PyTorch.
    
    Funzionalità:
    ✓ Generare esempi adversarial
    ✓ Valutare robustezza dei modelli
    ✓ Attacchi pre-implementati (PGD, FGSM, C&W)
    ✓ Integrazione con PyTorch e TensorBoard
    ✓ Compatibile con Python 3.13
    
    Esempio di uso:
    from secmlt.adv.evasion.pgd import PGD
    attack = PGD(epsilon=0.4, num_steps=100)
    adversarial_data = attack(model, data_loader)

CLASSIFICATORE (Classifier):
    Algoritmo che impara a categorizzare dati.
    Input: file audio → Output: "originale" o "modificato"
    
    Tipi usati in questo progetto:
    • SVM (Support Vector Machine) → Primo modello baseline
    • Deep Neural Network → Modello avanzato (fase successiva)

DATASET BILANCIATO:
    Avere lo stesso numero di esempi per ogni classe.
    Es: 50 original + 50 obfuscated = 100 totali (50/50)
    
    Perché importante?
    → Se non bilanciato, il modello impara a "barare" (predice sempre
       la classe più frequente)

================================================================================
🚀 COMANDI QUICK START
================================================================================

# Setup completo da zero
cd "/Users/francesco03/Documents/GitHub/AssaultCube Server/ADV_ML"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt  # Tutte le dipendenze

# Prepara dataset
mkdir -p dataset/original dataset/obfuscated
cp ../AC/packages/audio/weapon/*.wav dataset/original/

# Estrai feature
cd scripts
python3 extract_features.py

# Verifica output
ls -lh ../features/

================================================================================
📊 METRICHE DI VALUTAZIONE (per fase successiva)
================================================================================

ACCURACY:
    Percentuale di predizioni corrette sul totale.
    Formula: (TP + TN) / (TP + TN + FP + FN)

CONFUSION MATRIX:
                   Predetto
                 0        1
    Reale   0   TN       FP     TN = True Negative
            1   FN       TP     TP = True Positive
                                FN = False Negative
                                FP = False Positive

PRECISION:
    Delle predizioni positive, quante sono corrette?
    Formula: TP / (TP + FP)

RECALL:
    Dei sample positivi reali, quanti li trova?
    Formula: TP / (TP + FN)

F1-SCORE:
    Media armonica di Precision e Recall
    Formula: 2 * (Precision * Recall) / (Precision + Recall)

ROC CURVE:
    Grafico che mostra trade-off tra True Positive Rate e False Positive Rate
    AUC (Area Under Curve) → quanto è bravo il modello (1.0 = perfetto)

================================================================================
🔗 RISORSE UTILI
================================================================================

DOCUMENTAZIONE:
• Librosa:       https://librosa.org/doc/latest/
• Scikit-learn:  https://scikit-learn.org/stable/
• SecML-Torch:   https://github.com/pralab/secml-torch
• PyTorch:       https://pytorch.org/docs/stable/index.html
• NumPy:         https://numpy.org/doc/

TUTORIAL:
• MFCC Explained:  https://haythamfayek.com/2016/04/21/speech-processing-for-machine-learning-filter-banks-mel-frequency-cepstral-coefficients-mfccs.html
• Audio ML:        https://www.youtube.com/watch?v=MhOdbtPhbLU
• Adversarial ML:  https://adversarial-ml-tutorial.org/

PAPER:
• Carlini & Wagner (2018) - "Audio Adversarial Examples"
• Goodfellow et al. (2014) - "Explaining and Harnessing Adversarial Examples"

================================================================================
⚠️ TROUBLESHOOTING
================================================================================

PROBLEMA: "No module named 'librosa'"
SOLUZIONE: 
    $ cd ADV_ML
    $ source venv/bin/activate  # SEMPRE attivare il virtual environment!
    $ python3 -c "import librosa; print('OK')"

PROBLEMA: "Could not find a version that satisfies the requirement"
SOLUZIONE:
    $ pip install --upgrade pip

PROBLEMA: File .ogg invece di .wav
SOLUZIONE:
    $ ffmpeg -i input.ogg output.wav
    (installa ffmpeg: brew install ffmpeg su macOS)

PROBLEMA: Sample rate diversi nei file
SOLUZIONE:
    Librosa ricampiona automaticamente a 22050 Hz, ma è meglio normalizzare:
    $ ffmpeg -i input.wav -ar 22050 output.wav

PROBLEMA: "Permission denied" quando esegui script
SOLUZIONE:
    $ chmod +x script.py
    $ python3 script.py

================================================================================
📝 NOTE AGGIUNTIVE
================================================================================

• Tutti i file Python sono commentati riga per riga
• Ogni concetto è spiegato come se fossi uno studente al primo progetto ML
• La documentazione in SETUP_ADV_ML.md è ancora più dettagliata
• Per domande teoriche, consulta i paper linkati sopra
• Per domande pratiche, leggi i commenti negli script

BEST PRACTICES:
✓ Usa sempre il virtual environment
✓ Salva spesso i modelli addestrati
✓ Documenta ogni esperimento (accuratezza, parametri, etc.)
✓ Fai backup del dataset
✓ Testa su dati mai visti prima (test set separato)

================================================================================
Fine Quick Reference - Ultima modifica: 23 Ottobre 2025
================================================================================
