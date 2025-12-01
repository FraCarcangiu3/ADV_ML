# Guida Test Manuali Audio — per Ubi (utente)

**Autore:** Francesco Carcangiu  
**Data:** 30 Ottobre 2025

Questa guida spiega come eseguire test di ascolto soggettivi per calibrare le soglie di audio obfuscation (`min_perc` e `max_ok`). **Tu** decidi ascoltando, non un algoritmo.

---

## 🎧 Preparazione

### Ambiente di ascolto
- **Cuffie chiuse** o **in-ear** di buona qualità (no speaker)
- Volume confortevole ma non troppo basso (70-80% del max)
- Ambiente **silenzioso** (no rumori di fondo, no distrazioni)
- Prendi pause ogni 15-20 minuti per evitare affaticamento uditivo

### Software necessario
- macOS: `afplay` (già incluso)
- Linux/Windows: `ffplay` (installare ffmpeg: `brew install ffmpeg` o equivalente)
- Python 3.8+ con `soundfile`, `librosa`, `numpy` (opz. `sounddevice`)

---

## 📦 Generazione varianti

Prima di tutto, genera le varianti audio da testare:

```bash
cd "ADV_ML/tests"
python3 generate_audible_variants.py
```

Questo crea in `output/audible_variants/<sound>/`:
- `*_ref.wav` (riferimento originale)
- `*_pitch_p10.wav`, `*_pitch_n25.wav`, `*_pitch_p200.wav` (pitch shift)
- `*_noise_snr30.wav` (white noise)
- `*_noise_pink_snr35.wav` (pink noise)
- `*_tone_9000hz.wav` (toni puri)
- `*_eq_tilt_p3dB.wav` (tilt EQ)
- `*_combo_*.wav` (combinazioni semplici)

Ogni file ha un sidecar `.txt` con i parametri applicati.

**Verifica:** ~75 file per suono (auto, footsteps, affirmative).

---

## 🧪 Test 1: Listening Test Guidato (nuova CLI)

Usa la nuova CLI unificata:

```bash
python3 ADV_ML/tests/human_listen_and_label.py ADV_ML/tests/output/audible_variants/auto \
  --subject Francesco --types pitch noise noise_pink tone eq_tilt combo --randomize
```

- Filtri disponibili: `--types pitch noise noise_pink tone eq_tilt combo all`
- Player: auto (afplay su macOS, ffplay altrove). Fallback `sounddevice`.
- Output risultati: `ADV_ML/tests/subjective_results.csv`

Esempi rapidi:

```bash
# Solo pitch
python3 ADV_ML/tests/human_listen_and_label.py ADV_ML/tests/output/audible_variants/auto --types pitch --subject Francesco --randomize

# Solo combinazioni
python3 ADV_ML/tests/human_listen_and_label.py ADV_ML/tests/output/audible_variants/footsteps --types combo --subject Francesco
```

Procedura:
1. Riproduce (se presente) il **riferimento**, poi la **variante**
2. Chiede: differenza (Y/N), severità (1–5 se Y), note
3. Salva riga CSV: `subject,file,value,type,perceived_change,severity,notes,timestamp`

---

## 🎯 Test 2: ABX (Discriminazione)

```bash
python3 ADV_ML/tests/run_abx.py ADV_ML/tests/output/audible_variants/auto --subject Francesco --trials 15
```

Interpretazione:
- **>70% correct** → discrimini chiaramente
- **60–70%** → discrimini spesso
- **50–60%** → borderline
- **<50%** → al caso

---

## 📊 Analisi Risultati

```bash
python3 -c "
import pandas as pd
p1='ADV_ML/tests/subjective_results.csv'
df=pd.read_csv(p1)
print('Detection rate per type:')
print(df.groupby('type')['perceived_change'].value_counts(normalize=True))
print('\nAverage severity (when detected):')
print(df[df['severity']>0].groupby('type')['severity'].mean())
"
```

Stima soglie:
- **min_perc**: primo valore (per tipo) dove `perceived_change=Y` oppure ~60% ABX
- **max_ok**: ultimo valore dove `severity ≤ 2`

Suggerimenti attesi (da letteratura):
- auto: min 10–15c, max 25–40c
- footsteps: min 3–7c, max 10–20c
- affirmative: min 5–10c, max 15–25c

---

## 🔧 Workflow Consigliato

1) Genera varianti  
2) Esegui `human_listen_and_label.py` per pitch → noise → tone → eq → combo  
3) (Opz.) ABX su range critici  
4) Estrai min_perc e max_ok e aggiorna `AC/audio_obf_config.csv`

---

## 📝 Template Decisione Finale

| Sound | min_perc (cents) | max_ok (cents) | Note |
|-------|------------------|----------------|------|
| weapon/auto.ogg | 10–15 | 25–40 | gunshot robusto |
| player/footsteps.ogg | 3–7 | 10–20 | sensibile |
| voicecom/affirmative.ogg | 5–10 | 15–25 | voce |

---

## ❓ Troubleshooting

- Nessun audio: installa ffmpeg o usa `--player afplay/ffplay`
- CSV vuoto: controlla path e permessi, riprova
- Differenze sempre percepite: abbassa volume e fai pause

---

## 🎓 Riferimenti
- ITU-R BS.1116, ABX testing, JND pitch/noise

**Buon testing!** 🎧

