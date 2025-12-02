# Guida Training sul Server - Modelli Clean (9-fold CV)

Guida operativa per preparare l'ambiente e lanciare il training 9-fold dei modelli deep learning sul server.

---

## Step 0 – Aggiornare il codice dal Mac al server

### Sul Mac (dove lavori):
```bash
cd "/Users/francesco03/Documents/GitHub/AssaultCube Server"
git add .
git commit -m "Update training code"
git push
```

### Sul server (dove fai il training):
```bash
cd /path/to/AssaultCube\ Server  # sostituisci con il percorso reale
git pull
```

**Cosa mi aspetto:** Il codice viene aggiornato sul server con le ultime modifiche dal Mac.

---

## Step 1 – Creare/attivare l'ambiente conda sul server

```bash
# Crea l'ambiente conda (se non esiste già)
conda create -n ac_ml python=3.10 -y

# Attiva l'ambiente
conda activate ac_ml
```

**Cosa mi aspetto:** Vedi `(ac_ml)` all'inizio della riga del terminale, che indica che l'ambiente è attivo.

**Nota:** Se l'ambiente esiste già, puoi saltare il comando `conda create` e usare direttamente `conda activate ac_ml`.

---

## Step 2 – Installare le dipendenze

```bash
# Vai nella cartella del progetto ML
cd COLLEAGUE_BSc_Thesis

# Installa le dipendenze base dal requirements.txt
pip install -r requirements.txt

# Installa PyTorch (versione CPU - adatta per server senza GPU)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Verifica che le librerie audio siano installate (dovrebbero essere già in requirements.txt)
pip install librosa soundfile scipy
```

**Cosa mi aspetto:** Tutte le librerie vengono installate senza errori. Se vedi warning, di solito vanno bene.

**Nota:** Se il server ha una GPU NVIDIA, puoi installare PyTorch con supporto CUDA invece della versione CPU. In quel caso usa:
```bash
pip install torch torchvision torchaudio
```

---

## Step 2.5 – Verificare che i dati siano presenti

Prima di lanciare il training, assicurati che i file di dati siano presenti nelle cartelle corrette.

```bash
cd COLLEAGUE_BSc_Thesis

# Verifica che esistano le cartelle
ls -la Data/csv/audio_loopback_csv/ | head -5
ls -la Data/csv/labels_csv/ | head -5

# Conta quanti file audio CSV ci sono
echo "File audio CSV trovati:"
ls Data/csv/audio_loopback_csv/audio_event_*.csv 2>/dev/null | wc -l

# Conta quanti file label CSV ci sono
echo "File label CSV trovati:"
ls Data/csv/labels_csv/*.csv 2>/dev/null | wc -l
```

**Cosa mi aspetto:**
- La cartella `Data/csv/audio_loopback_csv/` contiene file tipo `audio_event_<uuid>.csv`
- La cartella `Data/csv/labels_csv/` contiene file tipo `<uuid>.csv` o `labels_<uuid>.csv`
- Il numero di file audio dovrebbe essere simile al numero di file label (devono essere accoppiati)

**Se i dati non ci sono:**
- I dati potrebbero essere in un'altra posizione sul server
- Potresti dover copiare/scaricare i dati dal Mac o da un'altra fonte
- Verifica il percorso completo: il codice cerca i dati in `COLLEAGUE_BSc_Thesis/Data/csv/audio_loopback_csv/` e `COLLEAGUE_BSc_Thesis/Data/csv/labels_csv/`

**Nota:** Se i dati sono in un'altra posizione, puoi usare variabili d'ambiente per indicare al codice dove trovarli (vedi troubleshooting).

---

## Step 3 – Lanciare il training 9-fold

### Versione base (foreground):
```bash
cd COLLEAGUE_BSc_Thesis
python -m model_classifier.deep_cv
```

### Versione con background e logging (consigliata):
```bash
cd COLLEAGUE_BSc_Thesis
nohup python -m model_classifier.deep_cv > logs_deep_cv.txt 2>&1 &
```

**Cosa mi aspetto:**
- Con la versione base: vedi l'output del training direttamente nel terminale.
- Con la versione background: il processo parte in background e puoi chiudere il terminale senza interrompere il training. L'output viene salvato in `logs_deep_cv.txt`.

**Nota:** Il training 9-fold allena 3 modelli diversi (resnet18_mel96, crnn_mel80, conv1d_sep_ds48k) per ogni fold, quindi può richiedere diverse ore. Usa la versione background se vuoi che continui anche dopo aver chiuso la sessione SSH.

---

## Step 4 – Controllare che il training sia andato a buon fine

### Verificare l'output in tempo reale:
```bash
# Se hai lanciato in background, guarda i log
tail -f COLLEAGUE_BSc_Thesis/logs_deep_cv.txt
```
Premi `Ctrl+C` per uscire dal tail.

### Verificare che i checkpoint siano stati creati:
```bash
cd COLLEAGUE_BSc_Thesis
ls -lh model_classifier/checkpoints/
```

**Cosa mi aspetto di vedere:**
- File con nomi tipo `resnet18_mel96_fold1.pth`, `resnet18_mel96_fold2.pth`, ..., `resnet18_mel96_fold9.pth`
- Stesso pattern per `crnn_mel80_fold*.pth` e `conv1d_sep_ds48k_fold*.pth`
- In totale dovresti avere **27 file** (3 modelli × 9 fold)

### Verificare che il processo sia ancora in esecuzione:
```bash
ps aux | grep deep_cv
```

**Cosa mi aspetto:** Vedi una riga con `python -m model_classifier.deep_cv` se il training è ancora in corso.

### Verificare i risultati finali:
```bash
cd COLLEAGUE_BSc_Thesis
ls -lh model_classifier/results_*.txt
ls -lh model_classifier/result_*.txt
```

**Cosa mi aspetto:**
- File `results_YYYYMMDD_HHMMSS.txt` con il riepilogo di tutti i modelli
- File `result_<modello>_YYYYMMDD_HHMMSS.txt` per ogni modello specifico

---

## Troubleshooting

### Il training si interrompe con errori di memoria:
- Riduci il numero di worker: `CLASSIFIER_LOAD_WORKERS=2 python -m model_classifier.deep_cv`
- Oppure riduci il batch size modificando `deep_cv.py` (ma non è consigliato per ora)

### Errore "No (audio,label) pairs found":
- **Causa:** I file di dati non sono presenti nelle cartelle attese
- **Soluzione 1:** Verifica che i dati esistano (vedi Step 2.5)
- **Soluzione 2:** Se i dati sono in un'altra posizione, puoi usare variabili d'ambiente:
  ```bash
  # Esempio: se hai un solo file di test
  CLASSIFIER_AUDIO_FILE=/path/to/audio_event_test.csv \
  CLASSIFIER_LABEL_FILE=/path/to/labels_test.csv \
  python -m model_classifier.deep_cv
  ```
- **Soluzione 3:** Crea i link simbolici se i dati sono altrove:
  ```bash
  cd COLLEAGUE_BSc_Thesis
  mkdir -p Data/csv
  ln -s /path/to/real/audio_loopback_csv Data/csv/audio_loopback_csv
  ln -s /path/to/real/labels_csv Data/csv/labels_csv
  ```

### Non vedo i checkpoint nella cartella:
- Verifica che la cartella `checkpoints/` esista: `mkdir -p COLLEAGUE_BSc_Thesis/model_classifier/checkpoints`
- Controlla i log per eventuali errori: `cat COLLEAGUE_BSc_Thesis/logs_deep_cv.txt | grep -i error`

### Vuoi fermare il training:
```bash
# Trova il PID del processo
ps aux | grep deep_cv

# Ferma il processo (sostituisci <PID> con il numero che vedi)
kill <PID>
```

---

## Riepilogo comandi rapidi

```bash
# Setup completo (da eseguire una volta)
conda create -n ac_ml python=3.10 -y
conda activate ac_ml
cd COLLEAGUE_BSc_Thesis
pip install -r requirements.txt
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
pip install librosa soundfile scipy

# Verifica dati (IMPORTANTE prima del training)
cd COLLEAGUE_BSc_Thesis
ls Data/csv/audio_loopback_csv/audio_event_*.csv | wc -l
ls Data/csv/labels_csv/*.csv | wc -l

# Training (ogni volta che vuoi riallenare)
cd COLLEAGUE_BSc_Thesis
nohup python -m model_classifier.deep_cv > logs_deep_cv.txt 2>&1 &

# Verifica
tail -f logs_deep_cv.txt
ls -lh model_classifier/checkpoints/
```

