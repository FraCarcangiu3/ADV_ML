# Guida per pubblicare il progetto su GitHub

## Repository: https://github.com/FraCarcangiu3/ADV_ML.git

## Comandi da eseguire in ordine:

### 1. Vai nella directory del progetto
```bash
cd "/Users/francesco03/Documents/GitHub/AssaultCube Server"
```

### 2. Verifica che il remote sia configurato correttamente
```bash
git remote -v
```
Dovresti vedere:
```
origin	https://github.com/FraCarcangiu3/ADV_ML.git (fetch)
origin	https://github.com/FraCarcangiu3/ADV_ML.git (push)
```

### 3. Se il remote non è configurato, aggiungilo:
```bash
git remote add origin https://github.com/FraCarcangiu3/ADV_ML.git
```

### 4. Assicurati di essere sul branch main
```bash
git branch -M main
```

### 5. Configura il buffer HTTP per file grandi (opzionale ma consigliato)
```bash
git config http.postBuffer 524288000
```

### 6. Verifica lo stato del repository
```bash
git status
```

### 7. Esegui il push del contenuto
```bash
git push -u origin main
```

## ⚠️ PROBLEMA: Repository molto grande (3.6 GB) - Soluzioni

### SOLUZIONE 1: Verifica se il push è andato a buon fine
A volte GitHub dà errore ma il push è completato. Controlla su GitHub se i file ci sono:
- Vai su https://github.com/FraCarcangiu3/ADV_ML
- Se vedi i file, il push è riuscito nonostante l'errore!

### SOLUZIONE 2: Usa SSH invece di HTTPS (CONSIGLIATO per file grandi)
```bash
# Cambia il remote a SSH
git remote set-url origin git@github.com:FraCarcangiu3/ADV_ML.git

# Riprova il push
git push -u origin main
```

### SOLUZIONE 3: Aumenta timeout e buffer
```bash
# Aumenta il buffer HTTP
git config http.postBuffer 1048576000

# Aumenta il timeout
git config http.lowSpeedLimit 0
git config http.lowSpeedTime 999999

# Riprova
git push -u origin main
```

### SOLUZIONE 4: Push con compressione massima
```bash
# Configura compressione massima
git config core.compression 9
git config pack.compression 9

# Riprova
git push -u origin main
```

### SOLUZIONE 5: Push in batch più piccoli (se le altre non funzionano)
```bash
# Fai push di un commit alla volta (se hai più commit)
# Oppure usa depth limit
git push -u origin main --depth=1
```

### SOLUZIONE 6: Usa Git LFS per file molto grandi (se necessario)
Se hai file singoli > 100MB, installa Git LFS:
```bash
# Installa Git LFS (se non ce l'hai)
brew install git-lfs  # su macOS

# Inizializza LFS
git lfs install

# Traccia file grandi (esempio per file .pth, .dylib, ecc.)
git lfs track "*.pth"
git lfs track "*.dylib"
git lfs track "*.so"

# Aggiungi .gitattributes
git add .gitattributes
git commit -m "Add Git LFS tracking"

# Riprova push
git push -u origin main
```

## Verifica finale

Dopo il push, verifica che tutto sia stato caricato:
```bash
git log --oneline
```

E controlla su GitHub che tutti i file siano presenti nella repository.

## Note importanti:

- La cartella `AC/` è esclusa tramite `.gitignore` (come richiesto)
- I virtual environment (`venv/`) sono esclusi automaticamente
- **IMPORTANTE**: Il repository è molto grande (3.6 GB). GitHub può avere problemi con push così grandi.
- Se vedi "Everything up-to-date" alla fine dell'errore, **controlla su GitHub**: potrebbe essere andato a buon fine!
- Per repository così grandi, SSH è più affidabile di HTTPS
- Se il push si interrompe, puoi riprovare: Git è intelligente e continuerà da dove si è fermato

## Ordine consigliato di tentativi:

1. **PRIMA COSA**: Controlla su GitHub se i file ci sono già (https://github.com/FraCarcangiu3/ADV_ML)
2. Se non ci sono, prova **SOLUZIONE 2** (SSH) - è la più affidabile
3. Se SSH non funziona, prova **SOLUZIONE 3** (aumenta timeout)
4. Come ultima risorsa, usa **SOLUZIONE 6** (Git LFS)


