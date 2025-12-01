# Setup Adversarial Machine Learning per Audio AntiCheat

## 📋 Indice

1. [Introduzione](#introduzione)
2. [Prerequisiti](#prerequisiti)
3. [Installazione dell'Ambiente](#installazione-dellambiente)
4. [Struttura del Progetto](#struttura-del-progetto)
5. [Concetti Base](#concetti-base)
6. [Preparazione Dataset](#preparazione-dataset)
7. [Estrazione delle Feature](#estrazione-delle-feature)
8. [Verifica dell'Installazione](#verifica-dellinstallazione)
9. [Prossimi Step](#prossimi-step)

---

## Introduzione

Questa è la sezione **Adversarial Machine Learning** del progetto AssaultCube AntiCheat!

In questa parte della tesi, utilizzeremo tecniche di Machine Learning per:
1. **Riconoscere** se un file audio è stato modificato (pitch shift)
2. **Creare** modifiche audio che ingannano i classificatori
3. **Difenderci** da questi attacchi adversarial

Questa guida è pensata per chi si avvicina per la prima volta al Machine Learning applicato all'audio.

---

## Prerequisiti

### Cosa ti serve

- **Python 3.8+** installato sul tuo sistema
- **pip** (package manager di Python)
- Circa **500 MB** di spazio disco per le librerie
- Connessione internet per scaricare i pacchetti

### Verifica Python

Apri il terminale e digita:

```bash
python3 --version
```

Dovresti vedere qualcosa come `Python 3.9.7` o superiore.

---

## Installazione dell'Ambiente

### Step 1: Creare un Virtual Environment (Consigliato)

Un virtual environment isola le librerie di questo progetto dal resto del sistema.

```bash
# Naviga nella cartella del progetto
cd "/Users/francesco03/Documents/GitHub/AssaultCube Server/ADV_ML"

# Crea il virtual environment
python3 -m venv venv

# Attiva il virtual environment
# Su macOS/Linux:
source venv/bin/activate

# Su Windows:
# venv\Scripts\activate
```

Quando attivato, vedrai `(venv)` all'inizio della riga di comando.

### Step 2: Installare le Librerie Necessarie

**Metodo Rapido (Consigliato):**

```bash
# Aggiorna pip
pip install --upgrade pip

# Installa tutte le dipendenze in un colpo solo
pip install -r requirements.txt
```

**Metodo Alternativo (Manuale):**

Se preferisci installare manualmente:

```bash
# Aggiorna pip
pip install --upgrade pip

# Librerie per l'elaborazione audio
pip install librosa soundfile

# Librerie per il Machine Learning
pip install numpy scikit-learn scipy matplotlib

# Deep Learning & Adversarial ML
pip install torch torchvision secml-torch

# Utilità
pip install tqdm
```

**Tempo stimato:** 5-10 minuti a seconda della connessione.

**✅ NOTA SU SECML-TORCH:** Invece della vecchia libreria SecML, usiamo **SecML-Torch**, la versione moderna compatibile con Python 3.13 e PyTorch. Questa libreria offre le stesse funzionalità adversarial ML ma con supporto per deep learning e PyTorch.

### Step 3: Verifica Installazione

Testa che tutto sia installato correttamente:

```bash
python3 -c "import librosa, sklearn, numpy, matplotlib, tqdm, secmlt, torch; print('✅ Tutto installato correttamente!')"
```

Se vedi il messaggio di conferma, sei pronto!

**Verifica le versioni:**

```bash
python3 -c "import secmlt, torch; print('SecML-Torch:', secmlt.__version__); print('PyTorch:', torch.__version__)"
```

---

## Struttura del Progetto

La cartella `ADV_ML/` è organizzata così:

```
ADV_ML/
├── SETUP_ADV_ML.md          ← Questa guida
├── venv/                     ← Virtual environment (se creato)
├── dataset/                  ← I tuoi file audio
│   ├── original/             ← Suoni del gioco NON modificati
│   │   ├── machinegun_1.wav
│   │   ├── machinegun_2.wav
│   │   └── ...
│   └── obfuscated/           ← Suoni con pitch shift applicato
│       ├── machinegun_1_shifted.wav
│       ├── machinegun_2_shifted.wav
│       └── ...
├── scripts/                  ← Script Python del progetto
│   └── extract_features.py   ← Estrae MFCC dai file audio
└── features/                 ← Feature estratte (creata automaticamente)
    ├── X.npy                 ← Matrice delle feature
    └── y.npy                 ← Etichette (0=original, 1=obfuscated)
```

---

## Concetti Base

### Cos'è il Machine Learning?

Il **Machine Learning** (ML) è un modo per insegnare al computer a riconoscere pattern nei dati senza programmare regole esplicite.

**Esempio pratico:**
- Invece di dire "se il pitch è +5 allora è modificato"
- Diciamo "guarda questi 100 esempi e impara da solo a distinguere"

### Cos'è un Classificatore?

Un **classificatore** è un algoritmo che impara a mettere i dati in categorie.

Nel nostro caso:
- **Input:** un file audio
- **Output:** "originale" o "modificato"

### Cosa sono le MFCC?

**MFCC** = Mel-Frequency Cepstral Coefficients

Sono una rappresentazione matematica dell'audio che cattura:
- Le caratteristiche timbriche del suono
- Come il suono è percepito dall'orecchio umano
- Informazioni compatte (13-20 numeri invece di migliaia di sample)

**Perché si usano?**
1. **Dimensionalità ridotta:** Un file audio ha migliaia di sample, le MFCC sono solo 13-20 numeri
2. **Efficienza:** I modelli ML lavorano meglio con pochi dati ben scelti
3. **Robustezza:** Catturano l'essenza del suono ignorando dettagli irrilevanti
4. **Standard:** Usate in speech recognition, music information retrieval, etc.

**Visualizzazione:**

```
File Audio (48000 sample)  →  [Trasformata]  →  MFCC (13 coefficienti)
[0.1, 0.2, -0.1, ...]      →  [Estrazione]   →  [2.3, -1.1, 0.5, ...]
        ↓                                              ↓
   Difficile per ML                              Perfetto per ML
```

### Cos'è l'Adversarial Machine Learning?

**Adversarial ML** studia come ingannare i modelli di ML e come difendersi.

**Scenario del nostro progetto:**
1. **Attaccante (cheater):** Vuole modificare l'audio (pitch shift) senza essere scoperto
2. **Difensore (anticheat):** Vuole rilevare le modifiche
3. **Adversarial attack:** Modifiche "intelligenti" che ingannano il classificatore
4. **Adversarial defense:** Tecniche per rendere il classificatore più robusto

### Cos'è SecML-Torch?

**SecML-Torch** (SecMLT) è una libreria Python moderna per:
- Generare **esempi adversarial** per audio, immagini, etc.
- Valutare la **robustezza** dei modelli ML contro attacchi
- Implementare **attacchi** come PGD, FGSM, C&W
- Integrare con **PyTorch** per deep learning

**Vantaggi:**
- ✅ Compatibile con Python 3.13
- ✅ Integrazione nativa con PyTorch
- ✅ Attacchi pre-implementati (PGD, FGSM, etc.)
- ✅ Support per debugging con TensorBoard
- ✅ Modular e estensibile

---

## Preparazione Dataset

### Step 1: Raccogli i File Audio

Devi avere due set di file audio:

#### Dataset Original

File audio **originali** del gioco AssaultCube, ad esempio:
- `weapon/machinegun.wav`
- `player/footsteps.wav`
- Altri suoni rilevanti per il gameplay

**Dove trovarli:**
Nella cartella del gioco: `AC/packages/audio/weapon/` e `AC/packages/audio/player/`

#### Dataset Obfuscated

File audio **modificati** con pitch shift, creati con il tuo script di test.

**Come crearli:**
Usa il tool `pitch_test` che hai già nel progetto:

```bash
cd "/Users/francesco03/Documents/GitHub/AssaultCube Server/AC/tools"
./pitch_test ../packages/audio/weapon/machinegun.ogg 5
# Questo crea una versione con +5 semitoni
```

### Step 2: Copia i File nelle Cartelle

```bash
# Copia i file originali
cp AC/packages/audio/weapon/*.wav ADV_ML/dataset/original/

# Copia i file modificati
cp AC/tools/results/*_shifted.wav ADV_ML/dataset/obfuscated/
```

### Step 3: Converti .ogg in .wav (se necessario)

Se i file sono in formato `.ogg`, convertili in `.wav`:

```bash
# Installa ffmpeg se non lo hai
# Su macOS: brew install ffmpeg
# Su Linux: sudo apt-get install ffmpeg

# Converti un file
ffmpeg -i input.ogg output.wav
```

### Requisiti Minimi Dataset

Per un primo test:
- **Almeno 20 file** per categoria (original/obfuscated)
- **Stessa durata** (o taglia i file alla stessa lunghezza)
- **Stesso sample rate** (preferibilmente 44100 Hz o 48000 Hz)

---

## Estrazione delle Feature

### Cos'è extract_features.py?

È lo script che:
1. Legge tutti i file `.wav` dalle cartelle `original/` e `obfuscated/`
2. Calcola le **MFCC** per ogni file
3. Crea due array:
   - `X`: matrice delle feature (una riga per file)
   - `y`: array delle etichette (0 = original, 1 = obfuscated)
4. Salva tutto in file `.npy` (formato NumPy)

### Come Usarlo

```bash
# Attiva il virtual environment (se non già attivo)
source venv/bin/activate

# Naviga nella cartella scripts
cd ADV_ML/scripts

# Esegui lo script
python3 extract_features.py
```

### Output Atteso

```
🎵 Inizio estrazione feature audio...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📁 Lettura dataset original...
   ✓ Trovati 25 file audio
📁 Lettura dataset obfuscated...
   ✓ Trovati 25 file audio

🔍 Estrazione MFCC...
original: 100%|████████████████| 25/25 [00:12<00:00]
obfuscated: 100%|████████████████| 25/25 [00:12<00:00]

💾 Salvataggio feature...
   ✓ X.npy salvato (50 sample, 13 feature)
   ✓ y.npy salvato (50 label)

✅ Estrazione completata!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Cosa Sono X e y?

**X.npy** (Feature Matrix)
```
Shape: (n_samples, n_features)
Esempio: (50, 13)

[[2.3, -1.1, 0.5, ...],   ← File 1
 [1.8, -0.9, 0.3, ...],   ← File 2
 [2.1, -1.0, 0.4, ...],   ← File 3
 ...]
```

**y.npy** (Labels)
```
Shape: (n_samples,)
Esempio: (50,)

[0, 0, 0, ..., 1, 1, 1, ...]
 ↑             ↑
 original      obfuscated
```

---

## Verifica dell'Installazione

### Test Rapido

Crea un piccolo script di test:

```bash
cd ADV_ML/scripts
nano test_installation.py
```

Incolla questo codice:

```python
import librosa
import numpy as np
import sklearn
from secml.array import CArray

print("✅ librosa version:", librosa.__version__)
print("✅ numpy version:", np.__version__)
print("✅ scikit-learn version:", sklearn.__version__)
print("✅ SecML importato correttamente")
print("\n🎉 Tutto funziona! Sei pronto per iniziare.")
```

Esegui:

```bash
python3 test_installation.py
```

### Risoluzione Problemi Comuni

#### Errore: "No module named 'librosa'"

**Soluzione:** Assicurati di aver attivato il virtual environment

```bash
source venv/bin/activate
pip install librosa
```

#### Errore: "Could not find a version that satisfies the requirement"

**Soluzione:** Aggiorna pip

```bash
pip install --upgrade pip
```

#### Errore: "Permission denied"

**Soluzione:** Non usare `sudo` con pip nel virtual environment. Ricrea il venv.

---

## Prossimi Step

Congratulazioni! Hai completato il setup dell'ambiente. 🎉

### Cosa Abbiamo Fatto Finora

✅ Installato tutte le librerie necessarie  
✅ Creato la struttura delle cartelle  
✅ Capito cosa sono MFCC e Adversarial ML  
✅ Preparato lo script di estrazione feature  

### Cosa Faremo nel Prossimo Step

Nel prossimo capitolo creeremo:

1. **train_classifier.py** - Un classificatore SVM (Support Vector Machine) semplice che:
   - Carica le feature estratte (X.npy, y.npy)
   - Divide in training set e test set
   - Addestra il modello
   - Valuta l'accuratezza

2. **Metriche di Valutazione:**
   - Accuracy (precisione generale)
   - Confusion Matrix (dove sbaglia?)
   - ROC curve (quanto è bravo il modello?)

3. **Salvataggio del Modello:**
   - Salvare il classificatore addestrato
   - Testarlo su nuovi file audio

### Domande per Riflettere

Prima di procedere, assicurati di aver compreso:


---

## Risorse Utili

### Documentazione

- **Librosa:** https://librosa.org/doc/latest/index.html
- **Scikit-learn:** https://scikit-learn.org/stable/
- **SecML-Torch:** https://github.com/pralab/secml-torch
- **PyTorch:** https://pytorch.org/docs/stable/index.html
- **PyTorch Audio:** https://pytorch.org/audio/stable/index.html

### Tutorial Consigliati

- [Intro to MFCC](https://haythamfayek.com/2016/04/21/speech-processing-for-machine-learning-filter-banks-mel-frequency-cepstral-coefficients-mfccs.html)
- [Audio Processing with Librosa](https://www.youtube.com/watch?v=MhOdbtPhbLU)
- [Adversarial ML Basics](https://adversarial-ml-tutorial.org/)

### Paper di Riferimento

- Carlini & Wagner (2018) - "Audio Adversarial Examples"
- Goodfellow et al. (2014) - "Explaining and Harnessing Adversarial Examples"

---

## Note Finali

Questo setup è il fondamento per tutto il lavoro successivo. Prenditi il tempo necessario per:

1. Capire ogni concetto
2. Eseguire tutti i comandi
3. Verificare che funzioni tutto
4. Raccogliere un buon dataset

**Non avere fretta!** Un setup solido ti farà risparmiare ore di debugging in seguito.

Se qualcosa non è chiaro, rileggi la sezione corrispondente o consulta le risorse linkate.

---

**Prossimo file da creare:** `scripts/extract_features.py`


