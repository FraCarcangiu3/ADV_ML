# Manual Verification Steps

## Procedura Coarse → Fine Completata

Questa directory contiene i risultati della procedura automatizzata per trovare min_perc e max_ok sui 3 suoni selezionati.

### File Generati

- `TEST_RESULTS_COARSE.csv` - Risultati del coarse sweep
- `TEST_RESULTS_FINE.csv` - Risultati del fine sweep  
- `TEST_SUMMARY_FINE.md` - Report completo con analisi
- `plots/` - Grafici SNR vs Pitch per ogni suono
- `listening_set/` - File audio selezionati per test soggettivi

### Verifica Manuale

#### 1. Controlla i Risultati

```bash
# Visualizza prime 10 righe dei risultati fine
head -10 TEST_RESULTS_FINE.csv

# Conta varianti per suono
cut -d',' -f1 TEST_RESULTS_FINE.csv | sort | uniq -c
```

#### 2. Test Audio Manuale

```bash
# Converti OGG a WAV
ffmpeg -y -i ../AC/packages/audio/weapon/shotgun.ogg -ar 44100 -ac 1 shotgun_ref.wav

# Genera variante pitch (se pitch_test disponibile)
../AC/tools/pitch_test shotgun_ref.wav shotgun_pitch.wav --cents 20

# Calcola SNR
python3 snrdiff_auto.py shotgun_ref.wav shotgun_pitch.wav

# Ascolta i file
afplay shotgun_ref.wav      # macOS
ffplay shotgun_pitch.wav    # cross-platform
```

#### 3. Test Soggettivi

1. Vai nella directory `listening_set/`
2. Per ogni suono, ascolta i file selezionati
3. Compila `subjective_results_template.csv` con:
   - `detected(0/1)`: Hai notato differenze?
   - `rating(1-5)`: Qualità audio (1=molto distorta, 5=perfetta)
   - `comments`: Note aggiuntive

#### 4. Verifica Soglie

Basandoti sui risultati SNR e sui test soggettivi:

- **min_perc**: Primo pitch dove noti differenze
- **max_ok**: Ultimo pitch dove la qualità è ancora accettabile

### Configurazione Finale

I valori raccomandati per `audio_obf_config.csv`:

```csv
# Sound-specific pitch shift ranges (min_perc, max_ok, min_noise, max_noise)
shotgun,5,15,20,30
footsteps,2,8,12,20
affirmative,3,10,15,25
```

### Troubleshooting

- Se `pitch_test` non funziona, usa `librosa` (fallback automatico)
- Se i file audio non si aprono, verifica che `ffmpeg` sia installato
- Se i risultati SNR sembrano strani, controlla che i file di riferimento esistano
