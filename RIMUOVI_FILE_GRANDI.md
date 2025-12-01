# Guida per rimuovere file grandi dal repository Git

## Problema
Il repository contiene file molto grandi (modelli .pth da 43MB, CSV da 16MB) che rendono difficile il push su GitHub.

## Soluzione: Rimuovere file grandi dal repository

### IMPORTANTE: Leggi prima di procedere
- Questi comandi rimuoveranno i file grandi dalla **storia Git**
- I file rimarranno sul tuo computer (non vengono cancellati)
- Dovrai fare un nuovo commit dopo

### Opzione 1: Rimuovere solo i file .pth (modelli ML)

```bash
cd "/Users/francesco03/Documents/GitHub/AssaultCube Server"

# Rimuovi i file .pth dal repository (ma non dal filesystem)
git rm --cached COLLEAGUE_BSc_Thesis/model_classifier/checkpoints/*.pth

# Aggiungi il commit
git commit -m "Remove large model files (.pth) from repository"
```

### Opzione 2: Rimuovere anche i CSV grandi (dati audio)

```bash
cd "/Users/francesco03/Documents/GitHub/AssaultCube Server"

# Rimuovi i CSV grandi (attenzione: sono molti!)
git rm --cached COLLEAGUE_BSc_Thesis/Data/csv/audio_loopback_csv/*.csv

# Aggiungi il commit
git commit -m "Remove large CSV files from repository"
```

### Opzione 3: Rimuovere tutto in una volta (modelli + CSV)

```bash
cd "/Users/francesco03/Documents/GitHub/AssaultCube Server"

# Rimuovi modelli
git rm --cached COLLEAGUE_BSc_Thesis/model_classifier/checkpoints/*.pth

# Rimuovi CSV grandi
git rm --cached COLLEAGUE_BSc_Thesis/Data/csv/audio_loopback_csv/*.csv

# Commit tutto insieme
git commit -m "Remove large files (.pth and CSV) from repository"
```

## Dopo aver rimosso i file

1. **Verifica che il .gitignore sia aggiornato** (dovrebbe già esserlo):
```bash
cat .gitignore | grep -E "(\.pth|\.csv)"
```

2. **Fai il push**:
```bash
git push -u origin main
```

## Nota importante

- I file `.pth` e `.csv` rimarranno sul tuo computer, ma non saranno più tracciati da Git
- Se qualcuno clona il repository, dovrà generare/ottenere questi file separatamente
- Per condividere questi file, considera:
  - Usare Git LFS (Git Large File Storage)
  - Caricarli su un servizio di storage separato (Google Drive, Dropbox, ecc.)
  - Includerli in un archivio separato

## Se vuoi usare Git LFS invece (per file grandi)

```bash
# Installa Git LFS
brew install git-lfs

# Inizializza
git lfs install

# Traccia file .pth
git lfs track "*.pth"
git lfs track "COLLEAGUE_BSc_Thesis/Data/csv/audio_loopback_csv/*.csv"

# Aggiungi .gitattributes
git add .gitattributes
git commit -m "Add Git LFS tracking for large files"

# Aggiungi i file
git add COLLEAGUE_BSc_Thesis/model_classifier/checkpoints/*.pth
git add COLLEAGUE_BSc_Thesis/Data/csv/audio_loopback_csv/*.csv
git commit -m "Add large files via Git LFS"

# Push
git push -u origin main
```

## Verifica dimensione repository dopo la rimozione

```bash
# Verifica dimensione
du -sh .git/objects

# Dovrebbe essere molto più piccolo (da 3.6GB a molto meno)
```

