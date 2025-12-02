# Guida per aggiungere i CSV grandi dopo il push iniziale

## Situazione
Il repository principale è stato pubblicato senza i file CSV grandi (che sono troppo pesanti per GitHub normale). Questi file sono ancora sul tuo computer ma non sono tracciati da Git.

## Come aggiungere i CSV con Git LFS

### 1. Installa Git LFS (se non ce l'hai già)
```bash
brew install git-lfs
```

### 2. Inizializza Git LFS nel repository
```bash
cd "/Users/francesco03/Documents/GitHub/AssaultCube Server"
git lfs install
```

### 3. Traccia i file CSV con Git LFS
```bash
git lfs track "COLLEAGUE_BSc_Thesis/Data/csv/audio_loopback_csv/*.csv"
```

Questo creerà/modificherà il file `.gitattributes`.

### 4. Rimuovi i CSV dal .gitignore (temporaneamente)
```bash
# Modifica .gitignore e commenta o rimuovi questa riga:
# COLLEAGUE_BSc_Thesis/Data/csv/audio_loopback_csv/*.csv
```

Oppure usa questo comando:
```bash
sed -i '' '/COLLEAGUE_BSc_Thesis\/Data\/csv\/audio_loopback_csv\/\*\.csv/d' .gitignore
```

### 5. Aggiungi i CSV al repository
```bash
git add .gitattributes
git add .gitignore
git add COLLEAGUE_BSc_Thesis/Data/csv/audio_loopback_csv/*.csv
```

### 6. Commit
```bash
git commit -m "Add large CSV files via Git LFS"
```

### 7. Push
```bash
git push origin main
```

## Verifica

Dopo il push, verifica che i CSV siano stati caricati:
- Vai su https://github.com/FraCarcangiu3/ADV_ML
- Controlla che i file CSV siano presenti
- Dovrebbero avere un'icona speciale che indica che sono gestiti da Git LFS

## Note importanti

- **Git LFS ha limiti**: GitHub offre 1GB di storage LFS gratuito, poi costa. Se hai molti CSV grandi, potresti superare il limite gratuito.
- **I CSV rimangono sul tuo computer**: Git LFS scarica i file solo quando necessario.
- **Chi clona il repository**: Dovrà avere Git LFS installato per scaricare i CSV.

## Se vuoi aggiungere anche altri file grandi

Puoi tracciare anche:
- File WAV: `git lfs track "*.wav"`
- File FLAC: `git lfs track "*.flac"`
- File PNG grandi: `git lfs track "COLLEAGUE_BSc_Thesis/Data/screenshots/**/*.png"`

Poi aggiungi e committa come sopra.

