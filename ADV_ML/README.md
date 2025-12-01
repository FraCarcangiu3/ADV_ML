# 📚 ADV_ML - Sistema di Perturbazione Audio

Sistema completo per applicare perturbazioni audio offline ai FLAC del collega e generare dati di test per il modello ML.

---

## 🗂️ Struttura Cartelle

```
ADV_ML/
├── 📖 README.md                    ← Questo file (INDICE PRINCIPALE)
│
├── 🐍 Script Python Principali
│   ├── offline_perturb.py          ← Script principale per generare CSV perturbati
│   ├── audio_effects.py            ← Funzioni per applicare effetti audio
│   ├── test_audio_pipeline.py      ← Test completo del sistema
│   └── generate_demo_audio.py      ← Genera esempi audio per professori
│
├── 📁 docs/                        ← DOCUMENTAZIONE ORGANIZZATA
│   ├── perturbazioni/              ← Guide su come usare le perturbazioni
│   │   └── README_OFFLINE_PERTURB.md
│   ├── test/                       ← Report e risultati dei test
│   │   ├── RISPOSTA_ZERI_CSV.md
│   │   └── REPORT_TEST_PIPELINE.md
│   └── corrections/                ← Documentazione delle correzioni
│       ├── CORREZIONE_RUMORE_SOLO_SEGNALE.md
│       └── SUMMARY_CORREZIONE.md
│
├── 📁 output/                      ← CSV generati (dati per ML)
│   └── pistol_*.csv
│
├── 📁 demo_audio_for_professors/   ← Esempi audio per dimostrazione
│   ├── 00_ORIGINALI/
│   ├── 01_PITCH/
│   ├── 02_WHITE_NOISE/
│   └── ...
│
├── 📁 scripts/                     ← Script di utilità
│   └── ...
│
└── 📁 tests/                       ← Test e risultati
    └── ...
```

---

## 🚀 Quick Start

### 1. Generare CSV con Perturbazioni

```bash
# Esempio: Genera CSV con pitch shift
python ADV_ML/offline_perturb.py \
  --dataset-root COLLEAGUE_BSc_Thesis/Data/audio/audio_loopback_flac \
  --perturbation pitch \
  --mode random \
  --min-cents -150 \
  --max-cents 150 \
  --num-samples 50 \
  --output-csv ADV_ML/output/pistol_pitch_P2_medium.csv
```

### 2. Testare il Sistema

```bash
# Test completo del sistema
python ADV_ML/test_audio_pipeline.py
```

### 3. Generare Esempi Audio per Professori

```bash
# Genera 5 esempi audio con tutte le perturbazioni
python ADV_ML/generate_demo_audio.py --num-samples 5
```

---

## 📖 Documentazione per Argomento

### 🎵 Come Usare le Perturbazioni
**📁 `docs/perturbazioni/README_OFFLINE_PERTURB.md`**
- Guida completa all'uso delle perturbazioni
- Esempi di comandi
- Spiegazione di tutti gli effetti disponibili
- **LEGGI QUESTO** se vuoi generare CSV

### 🧪 Test e Validazione
**📁 `docs/test/`**
- `RISPOSTA_ZERI_CSV.md` - Perché ci sono tanti zeri nei CSV?
- `REPORT_TEST_PIPELINE.md` - Report completo dei test eseguiti

### 🔧 Correzioni Applicate
**📁 `docs/corrections/`**
- `CORREZIONE_RUMORE_SOLO_SEGNALE.md` - Correzione: rumore solo sul segnale
- `SUMMARY_CORREZIONE.md` - Riassunto delle correzioni

---

## 🎯 Cosa Fa Ogni File

### Script Principali

| File | Cosa Fa |
|------|---------|
| `offline_perturb.py` | ⭐ **Script principale** - Genera CSV con perturbazioni |
| `audio_effects.py` | Funzioni per applicare effetti (pitch, noise, EQ, filtri) |
| `test_audio_pipeline.py` | Test completo del sistema |
| `generate_demo_audio.py` | Genera esempi audio per professori |

### Documentazione

| File | Quando Leggerlo |
|------|----------------|
| `docs/perturbazioni/README_OFFLINE_PERTURB.md` | ⭐ **Prima di tutto** - Come usare il sistema |
| `docs/test/RISPOSTA_ZERI_CSV.md` | Se ti chiedi perché ci sono tanti zeri |
| `docs/corrections/SUMMARY_CORREZIONE.md` | Se devi rigenerare CSV con rumore |

---

## 📋 Workflow Tipico

### 1. Generare CSV per Test ML

```bash
# Genera tutti i livelli di perturbazione
# (vedi GUIDA_OFFLINE_PERTURB_STEP_BY_STEP.md nella root)
```

### 2. Testare che Funzioni

```bash
python ADV_ML/test_audio_pipeline.py
```

### 3. Preparare Demo per Professori

```bash
python ADV_ML/generate_demo_audio.py --num-samples 5
# Poi apri ADV_ML/demo_audio_for_professors/
```

---

## ⚠️ Note Importanti

### Rumore Solo sul Segnale
✅ **IMPORTANTE:** Il rumore viene applicato **SOLO durante lo sparo**, non sul silenzio.

Questo è stato corretto in `audio_effects.py` con il parametro `only_on_signal=True`.

### CSV da Rigenerare
Se hai CSV vecchi con rumore, devi rigenerarli:
- ❌ Vecchi: `pistol_noiseW_*.csv` con 0% zeri
- ✅ Nuovi: `pistol_noiseW_*.csv` con ~77% zeri

Vedi `docs/corrections/SUMMARY_CORREZIONE.md` per i comandi.

---

## 🆘 Problemi Comuni

### "librosa non trovato"
```bash
pip install librosa
```

### "Nessun file FLAC trovato"
Verifica il path:
```bash
ls COLLEAGUE_BSc_Thesis/Data/audio/audio_loopback_flac/*.flac | head -5
```

### "CSV ha troppi zeri"
✅ **È normale!** Gli audio originali hanno ~77% zeri.
Vedi `docs/test/RISPOSTA_ZERI_CSV.md` per spiegazione completa.

---

## 📞 Dove Trovare Cosa

| Cosa Cerchi | Dove Guardare |
|-------------|---------------|
| Come generare CSV | `docs/perturbazioni/README_OFFLINE_PERTURB.md` |
| Perché tanti zeri | `docs/test/RISPOSTA_ZERI_CSV.md` |
| Come rigenerare CSV | `docs/corrections/SUMMARY_CORREZIONE.md` |
| Esempi audio | `demo_audio_for_professors/` |
| CSV generati | `output/` |
| Script di utilità | `scripts/` |

---

## 🎓 Per i Professori

Gli esempi audio sono in:
**`demo_audio_for_professors/`**

Vedi `demo_audio_for_professors/GUIDA_ASCOLTO.md` per istruzioni complete.

---

**Ultimo aggiornamento:** 24 Novembre 2024
