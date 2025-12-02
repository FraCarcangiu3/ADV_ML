# Comandi per il push finale

## Situazione attuale
- Repository: 2.53 GiB (leggermente sopra il limite di 2GB)
- File .pth rimossi dalla storia ✅
- File CSV rimossi dal tracking ✅

## Prova il push

```bash
cd "/Users/francesco03/Documents/GitHub/AssaultCube Server"

# Push con SSH
git push -u origin main --force
```

**Nota**: Usiamo `--force` perché abbiamo riscritto la storia Git.

## Se il push fallisce ancora

Il repository è ancora troppo grande. Dobbiamo rimuovere altri file grandi:

### Opzione 1: Rimuovere file WAV e PNG grandi

```bash
# Rimuovi file WAV grandi (demo audio)
git rm --cached ADV_ML/demo_audio_for_professors/**/*.wav

# Rimuovi screenshot PNG grandi
git rm --cached COLLEAGUE_BSc_Thesis/Data/screenshots/**/*.png

# Aggiorna .gitignore
echo "ADV_ML/demo_audio_for_professors/**/*.wav" >> .gitignore
echo "COLLEAGUE_BSc_Thesis/Data/screenshots/**/*.png" >> .gitignore

# Commit
git add .gitignore
git commit -m "Remove large WAV and PNG files"

# Rimuovi dalla storia
FILTER_BRANCH_SQUELCH_WARNING=1 git filter-branch --force --index-filter 'git rm --cached --ignore-unmatch ADV_ML/demo_audio_for_professors/**/*.wav COLLEAGUE_BSc_Thesis/Data/screenshots/**/*.png' --prune-empty --tag-name-filter cat -- --all

# Pulisci
rm -rf .git/refs/original/ && git reflog expire --expire=now --all && git gc --prune=now --aggressive

# Push
git push -u origin main --force
```

### Opzione 2: Usa Git LFS per tutti i file grandi

```bash
# Installa Git LFS
brew install git-lfs

# Inizializza
git lfs install

# Traccia file grandi
git lfs track "*.wav"
git lfs track "*.png"
git lfs track "*.flac"
git lfs track "*.pth"
git lfs track "COLLEAGUE_BSc_Thesis/Data/csv/audio_loopback_csv/*.csv"

# Aggiungi .gitattributes
git add .gitattributes
git commit -m "Track large files with Git LFS"

# Migra file esistenti
git lfs migrate import --include="*.wav,*.png,*.flac,*.pth,COLLEAGUE_BSc_Thesis/Data/csv/audio_loopback_csv/*.csv" --everything

# Push
git push -u origin main --force
```

## Dopo il push riuscito

Una volta che il push è andato a buon fine, puoi aggiungere i CSV separatamente con Git LFS:

```bash
# Installa Git LFS se non ce l'hai
brew install git-lfs
git lfs install

# Traccia i CSV
git lfs track "COLLEAGUE_BSc_Thesis/Data/csv/audio_loopback_csv/*.csv"

# Aggiungi i CSV
git add .gitattributes
git add COLLEAGUE_BSc_Thesis/Data/csv/audio_loopback_csv/*.csv
git commit -m "Add large CSV files via Git LFS"

# Push
git push origin main
```

