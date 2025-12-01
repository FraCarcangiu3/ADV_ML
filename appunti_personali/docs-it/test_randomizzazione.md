## 9. Guida Rapida per Test e Validazione del Sistema

### 9.1 Test di Compilazione

**Verifica che il codice compili senza errori**:

```bash
cd AC/source/src
make client -j

# Output atteso:
# clang++ ... -o ac_client ...
# (Nessun errore)

# Verifica eseguibile
cd ../..
ls -lh ac_client
# -rwxr-xr-x ... ac_client
```

### 9.2 Test Obfuscation (Parametri Fissi)

**Verifica che le trasformazioni audio siano applicate correttamente**:

```bash
cd AC

# 1. Configura CSV con parametri fissi (deterministic)
cat > audio_obf_config.csv << 'EOF'
file_name,min_pitch_cents,max_pitch_cents,noise_type,noise_snr_db,min_freq,max_freq,eq_tilt_db,hp_hz,lp_hz
weapon/usp,150,150,white,40,,,3,175,9500
EOF

# 2. Avvia client CON obfuscation ma SENZA randomizzazione
export AC_AUDIO_OBF=1
export AC_AUDIO_OBF_RANDOMIZE=0  # Disabilita random
./ac_client

# 3. In-game: sparare con pistola, controllare log
# Output atteso:
# [AUDIO_OBF] weapon/usp → pitch:+150c; ... noise:white@40.0dB
# (Parametri FISSI, sempre gli stessi)
```

**Verifica uditiva**: Il suono della pistola deve essere leggermente più acuto (pitch +150c), con un leggero fruscio bianco di fondo.

### 9.3 Test Randomizzazione (Parametri Variabili)

**Verifica che i parametri cambino per ogni colpo**:

```bash
cd AC

# 1. Configura CSV con range (per randomizzazione)
cat > audio_obf_config.csv << 'EOF'
file_name,min_pitch_cents,max_pitch_cents,noise_type,noise_snr_db,min_freq,max_freq,eq_tilt_db,hp_hz,lp_hz
weapon/usp,-200,200,white,35,,,2,150,10000
EOF

# 2. Avvia client CON obfuscation E randomizzazione
export AC_AUDIO_OBF=1
export AC_AUDIO_OBF_RANDOMIZE=1  # Abilita random
./ac_client

# 3. In-game: sparare 5-10 colpi, controllare log
# Output atteso:
# [AUDIO_OBF_RAND] weapon/usp → pitch:+156c, noise:white@42.1dB, eq:+2.8dB, ...
# [AUDIO_OBF_RAND] weapon/usp → pitch:-127c, noise:white@37.8dB, eq:+4.2dB, ...
# [AUDIO_OBF_RAND] weapon/usp → pitch:+89c, noise:white@39.5dB, eq:+3.1dB, ...
# (Parametri DIVERSI per ogni colpo)
```

**Verifica numerica** (pitch deve variare in `[-200,-75] ∪ [75,200]`):

```bash
# Estrai valori pitch dal log
grep "AUDIO_OBF_RAND.*weapon/usp" ~/Library/Logs/assaultcube.log | \
  sed -n 's/.*pitch:\([+-]*[0-9]*\)c.*/\1/p' | sort -n

# Output atteso (esempio):
# -189
# -156
# -98
# -87
# 89
# 127
# 156
# 189
# NOTA: NESSUN valore in [-75, 75] (dead zone)
```

### 9.4 Test Generazione Varianti Offline

**Verifica che lo script `run_random_variants.sh` funzioni**:

```bash
cd ADV_ML/scripts

# 1. Genera 10 varianti di test
./run_random_variants.sh weapon/usp 10

# Output atteso:
# === Audio Random Variants Generator ===
# Sound: weapon/usp
# Num variants: 10
# ...
# Generated variant 1: pitch=161c, SNR=35.3dB, EQ=3.1dB, HP=223Hz, LP=9435Hz
# Generated variant 2: pitch=-80c, SNR=43.7dB, EQ=5.7dB, HP=232Hz, LP=8675Hz
# ...

# 2. Verifica CSV generato
cat ../output/random_variants/random_params.csv

# Output atteso:
# variant_id,pitch_cents,noise_snr_db,eq_tilt_db,hp_hz,lp_hz
# 1,161,35.3,3.1,223,9435
# 2,-80,43.7,5.7,232,8675
# ...

# 3. Verifica distribuzione uniforme (pitch)
cat ../output/random_variants/random_params.csv | \
  awk -F',' 'NR>1 {print $2}' | sort -n

# Output atteso: valori distribuiti uniformemente in [-200..-75] ∪ [75..200]
```

### 9.5 Test Impercezione (Soggettivo)

**Verifica che le trasformazioni siano accettabili per gameplay competitivo**:

```bash
cd AC
export AC_AUDIO_OBF=1
export AC_AUDIO_OBF_RANDOMIZE=1
./ac_client

# In-game: giocare 3-5 partite complete in modalità competitiva
# Annotare:
# - Suoni distinguibili? (armi diverse riconoscibili?)
# - Direzione spaziale preservata? (posso capire da dove sparano?)
# - Distanza percepita? (suono lontano vs vicino?)
# - Affaticamento uditivo? (dopo 30 min, è fastidioso?)

# Criteri di accettabilità:
# ✓ Severity ≤ 2 (accettabile)
# ✓ Nessuna perdita di informazione tattica critica
# ✓ Nessun affaticamento dopo gameplay esteso
```

### 9.6 Test di Regressione (Compatibilità)

**Verifica che il sistema non rompa funzionalità esistenti**:

```bash
cd AC

# 1. Test senza obfuscation (modalità vanilla)
unset AC_AUDIO_OBF
unset AC_AUDIO_OBF_RANDOMIZE
./ac_client

# Verifica:
# - Audio funziona normalmente?
# - Nessun crash/freeze?
# - Nessun log di errore?

# 2. Test con obfuscation disabilitato via CSV
cat > audio_obf_config.csv << 'EOF'
file_name,min_pitch_cents,max_pitch_cents,noise_type,noise_snr_db,min_freq,max_freq,eq_tilt_db,hp_hz,lp_hz
EOF
# (CSV vuoto → nessun suono configurato)

export AC_AUDIO_OBF=1
./ac_client

# Verifica:
# - Audio vanilla (nessuna trasformazione)?
# - Log mostra "Profile not found" (silenzioso, corretto)?
```

### 9.7 Checklist Completa di Test

```
[ ] Compilazione riuscita (make client -j)
[ ] Obfuscation deterministico funziona (AC_AUDIO_OBF=1, RANDOMIZE=0)
[ ] Randomizzazione funziona (AC_AUDIO_OBF=1, RANDOMIZE=1)
[ ] Parametri variano per ogni colpo (verificato da log)
[ ] Pitch rispetta dead zone (nessun valore in [-75, 75])
[ ] SNR in range [35, 45] dB
[ ] EQ, HP, LP randomizzati correttamente
[ ] Script run_random_variants.sh genera CSV corretto
[ ] Test soggettivo: impercezione OK (severity ≤ 2)
[ ] Test soggettivo: informazione tattica preservata
[ ] Test regressione: modalità vanilla funziona
[ ] Test regressione: CSV vuoto → nessun crash
```

**Se tutti i test passano** ✅: Il sistema è pronto per validazione ML!

---

