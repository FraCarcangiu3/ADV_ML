# 🚀 Quick Start - ADV_ML AntiCheat

## ⚡ Comandi Essenziali

### 1. Attiva Virtual Environment
```bash
cd "/Users/francesco03/Documents/GitHub/AssaultCube Server/ADV_ML"
source venv/bin/activate
```

**⚠️ IMPORTANTE:** Sempre attivare il virtual environment prima di eseguire script Python!

### 2. Verifica Installazione
```bash
python3 -c "import librosa, sklearn, numpy, matplotlib, tqdm, secmlt, torch; print('✅ OK!')"
```

### 3. Estrai Feature MFCC
```bash
python3 scripts/extract_features.py
```

### 4. Carica e Verifica Dataset
```bash
python3 -c "
import numpy as np
X = np.load('features/X.npy')
y = np.load('features/y.npy')
print(f'Dataset: {X.shape[0]} samples, {X.shape[1]} features')
print(f'Classes: {len(np.unique(y))} classi')
"
```

## 📁 Struttura Progetto

```
ADV_ML/
├── venv/                    # Virtual environment (ATTIVARE SEMPRE!)
├── dataset/
│   ├── original/            # Audio originali (3 file)
│   └── obfuscated/          # Audio con pitch shift (3 file)
├── features/
│   ├── X.npy                # Feature MFCC (6×13)
│   └── y.npy                # Etichette (6)
├── scripts/
│   ├── audio_converter.py   # Conversione OGG→WAV + pitch shift
│   └── extract_features.py # Estrazione MFCC
└── requirements.txt         # Dipendenze Python
```

## 🔧 Troubleshooting

### Errore: "No module named 'librosa'"
**Soluzione:** Attiva il virtual environment
```bash
cd ADV_ML
source venv/bin/activate
```

### Errore: "Dataset not found"
**Soluzione:** Popola il dataset
```bash
python3 scripts/audio_converter.py
python3 scripts/extract_features.py
```

### Errore: "Permission denied"
**Soluzione:** Rendi eseguibili gli script
```bash
chmod +x scripts/*.py
```

## 📊 Dataset Attuale

- **File audio:** 6 (3 original + 3 obfuscated)
- **Feature:** 6 samples × 13 MFCC
- **Classi:** 2 (original=0, obfuscated=1)
- **Formato:** WAV mono 44.1kHz
- **Pitch shift:** +100 cents

## 🎯 Prossimi Step

1. ✅ **Setup Ambiente** → COMPLETATO
2. ✅ **Dataset Popolato** → COMPLETATO
3. ✅ **Feature Estratte** → COMPLETATO
4. ⏳ **Train Classificatore** → PROSSIMO
5. ⏳ **Test Adversarial** → FUTURO

## 💡 Tips

- **Sempre attivare venv:** `source venv/bin/activate`
- **Verifica prima di procedere:** Testa import delle librerie
- **Backup dataset:** I file audio sono preziosi!
- **Logs utili:** Controlla `.cursor-output/` per report

---

**Status:** ✅ READY FOR ML TRAINING  
**Ultima verifica:** 23 Ottobre 2025
