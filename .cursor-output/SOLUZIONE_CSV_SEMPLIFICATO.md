# ✅ SOLUZIONE: CSV Semplificato + Range dal CSV (non hardcoded)

**Data**: 2025-11-03  
**Problema risolto**: CSV troppo lungo + range hardcoded nel codice C++

---

## 🎯 Problemi risolti

### Problema 1: CSV illeggibile
**Prima**: 132 righe con 130+ righe di commenti → impossibile capire la configurazione

**Dopo**: 42 righe totali (15 commenti + 1 header + 1 configurazione + esempi)

### Problema 2: Range hardcoded nel codice
**Prima**: 
- White noise: 35-45 dB **hardcoded** in C++
- Pink noise: 16-24 dB **hardcoded** in C++
- EQ boost: 2-6 dB **hardcoded** in C++
- EQ cut: -9--3 dB **hardcoded** in C++
- HP: 150-250 Hz **hardcoded** in C++
- LP: 8000-10000 Hz **hardcoded** in C++

**Conseguenza**: Se volevi aggiungere `weapon/auto` con range diversi, **dovevi modificare il codice C++** → NON espandibile!

**Dopo**: 
- TUTTI i range sono nel CSV
- Ogni suono può avere i suoi range personalizzati
- Il codice C++ legge i range dal CSV → **sistema completamente espandibile**

---

## 📝 Nuovo formato CSV

### Header
```csv
file_name,min_pitch_cents,max_pitch_cents,noise_type,white_snr_min,white_snr_max,pink_snr_min,pink_snr_max,eq_mode,eq_boost_min,eq_boost_max,eq_cut_min,eq_cut_max,hp_min_hz,hp_max_hz,lp_min_hz,lp_max_hz
```

### Configurazione weapon/usp (esempio)
```csv
weapon/usp,-200,200,random,35,45,16,24,random,2,6,-9,-3,150,250,8000,10000
```

**Spiegazione colonna per colonna**:
1. `weapon/usp` → nome suono
2. `-200,200` → pitch range (min, max)
3. `random` → tipo noise (random = 50% white, 50% pink)
4. `35,45` → white noise SNR range (min, max) in dB
5. `16,24` → pink noise SNR range (min, max) in dB
6. `random` → modalità EQ (random = 50% boost, 50% cut)
7. `2,6` → EQ boost range (min, max) in dB
8. `-9,-3` → EQ cut range (min, max) in dB
9. `150,250` → HP filter range (min, max) in Hz
10. `8000,10000` → LP filter range (min, max) in Hz

---

## 🔧 Modifiche al codice

### 1. Struct AudioProfile aggiornata (`audio_runtime_obf.h`)

**Prima** (campi singoli):
```cpp
struct AudioProfile {
    std::string noise_type;
    float noise_snr_db;  // Un solo valore
    float eq_tilt_db;     // Un solo valore
    int hp_hz;            // Un solo valore
    int lp_hz;            // Un solo valore
};
```

**Dopo** (range completi):
```cpp
struct AudioProfile {
    std::string noise_type;
    float white_snr_min, white_snr_max;  // Range white
    float pink_snr_min, pink_snr_max;    // Range pink
    std::string eq_mode;
    float eq_boost_min, eq_boost_max;    // Range boost
    float eq_cut_min, eq_cut_max;        // Range cut
    int hp_min_hz, hp_max_hz;            // Range HP
    int lp_min_hz, lp_max_hz;            // Range LP
};
```

### 2. Parsing CSV aggiornato (`audio_runtime_obf.cpp`)

Ora il codice legge **17 colonne** dal CSV invece di 10:
```cpp
profile.white_snr_min = fields[4];
profile.white_snr_max = fields[5];
profile.pink_snr_min = fields[6];
profile.pink_snr_max = fields[7];
// ... ecc per tutti i campi
```

### 3. Randomizzazione usa valori dal CSV

**Prima** (hardcoded):
```cpp
if (audio_prof.noise_type == "white") {
    noise_snr_db = randomize_snr_uniform(35.0f, 45.0f);  // HARDCODED!
}
```

**Dopo** (da CSV):
```cpp
if (audio_prof.noise_type == "white") {
    noise_snr_db = randomize_snr_uniform(
        audio_prof.white_snr_min,  // DAL CSV
        audio_prof.white_snr_max   // DAL CSV
    );
}
```

---

## 🚀 Come aggiungere un nuovo suono (es. weapon/auto)

### Passo 1: Calibra i range con test soggettivi
Segui la procedura in `RANGE.md` per trovare i tuoi range per `weapon/auto`.

### Passo 2: Aggiungi riga nel CSV
```csv
weapon/auto,-250,300,random,30,40,12,20,random,1.5,5,-10,-2,100,300,7000,11000
```

**Tutto qui!** Non serve modificare il codice C++.

### Differenze rispetto a weapon/usp
- Pitch più estremo: -250/+300 vs -200/+200
- White noise più forte: 30-40 vs 35-45
- Pink noise più forte: 12-20 vs 16-24
- EQ boost più soft: 1.5-5 vs 2-6
- EQ cut più aggressivo: -10--2 vs -9--3
- HP più aggressivo: 100-300 vs 150-250
- LP più esteso: 7000-11000 vs 8000-10000

---

## 📊 Esempi di configurazioni

### Massima variabilità (consigliato anti-ML)
```csv
weapon/usp,-200,200,random,35,45,16,24,random,2,6,-9,-3,150,250,8000,10000
```
→ Noise random (white/pink), EQ random (boost/cut)

### White fisso, EQ random
```csv
weapon/usp,-200,200,white,35,45,0,0,random,2,6,-9,-3,150,250,8000,10000
```
→ Solo white noise, ma EQ cambia tra boost/cut

### Pink fisso, boost fisso
```csv
weapon/usp,-200,200,pink,0,0,16,24,boost,2,6,0,0,150,250,8000,10000
```
→ Solo pink noise, solo boost EQ

### Solo pitch (no noise, no EQ)
```csv
weapon/usp,-200,200,none,0,0,0,0,none,0,0,0,0,150,250,8000,10000
```
→ Solo pitch shift + HP/LP filters

---

## ✅ Vantaggi del nuovo sistema

### 1. Espandibilità totale
- Aggiungi `weapon/auto`, `player/footsteps`, `voicecom/affirmative` con range personalizzati
- Non serve mai modificare il codice C++

### 2. CSV leggibile
- 42 righe vs 132 righe (70% più corto)
- Header chiaro con nomi colonne espliciti
- Commenti essenziali (no muri di testo)

### 3. Flessibilità per test
**Esempio**: Test A/B per `weapon/usp`
```csv
# Configurazione aggressiva
weapon/usp,-200,200,random,30,40,12,20,random,1,8,-12,-1,100,300,6000,12000

# Configurazione conservativa  
weapon/usp,-200,200,random,40,45,20,24,random,2,4,-6,-3,180,220,9000,10000
```
→ Cambi una riga e riavvii il client, nessuna ricompilazione

### 4. Documentazione nel CSV stesso
- Ogni colonna ha un nome autoesplicativo
- Esempi commentati nel file
- Facile da capire anche senza leggere la tesi

---

## 🧪 Come testare

```bash
cd "/Users/francesco03/Documents/GitHub/AssaultCube Server/AC"

# 1. Verifica configurazione CSV
cat audio_obf_config.csv | grep weapon/usp

# Output atteso:
# weapon/usp,-200,200,random,35,45,16,24,random,2,6,-9,-3,150,250,8000,10000

# 2. Avvia client
export AC_AUDIO_OBF=1
export AC_AUDIO_OBF_RANDOMIZE=1
./ac_client

# 3. In-game: sparare 5-10 colpi

# 4. Verificare log (mix white/pink, mix boost/cut)
# Output atteso:
# [AUDIO_OBF_RAND] weapon/usp → pitch:+156c; eq:+4.2dB; noise:white@42dB ...
# [AUDIO_OBF_RAND] weapon/usp → pitch:-134c; eq:-6.1dB; noise:pink@19dB ...
```

---

## 📁 File modificati

1. **`AC/audio_obf_config.csv`**
   - Ridotto da 132 a 42 righe
   - Aggiornato header con 17 colonne
   - Commenti semplificati

2. **`AC/source/src/audio_runtime_obf.h`**
   - Struct AudioProfile estesa con range completi
   - Campi vecchi rimossi (noise_snr_db, eq_tilt_db, hp_hz, lp_hz)
   - Campi nuovi aggiunti (white_snr_min/max, pink_snr_min/max, eq_mode, eq_boost_min/max, eq_cut_min/max, hp_min/max_hz, lp_min/max_hz)

3. **`AC/source/src/audio_runtime_obf.cpp`**
   - Parsing CSV aggiornato per leggere 17 colonne
   - Randomizzazione usa valori dal CSV (no hardcoded)
   - Sezione deterministica usa midpoint dei range dal CSV

---

## 🎓 Confronto: Prima vs Dopo

| Aspetto | Prima | Dopo |
|---------|-------|------|
| **CSV righe** | 132 | 42 (-70%) |
| **Range hardcoded** | SÌ (6 parametri) | NO (tutto dal CSV) |
| **Espandibile** | NO (modifica C++) | SÌ (solo CSV) |
| **Leggibilità** | Bassa (troppi commenti) | Alta (essenziale) |
| **Flessibilità** | Bassa (magic values) | Alta (range espliciti) |
| **Test A/B** | Richiede ricompilazione | Solo modifica CSV |

---

## ✅ Checklist finale

- [x] CSV semplificato (42 righe)
- [x] Header con 17 colonne esplicite
- [x] Struct AudioProfile aggiornata
- [x] Parsing CSV per 17 colonne
- [x] Randomizzazione usa valori dal CSV
- [x] Nessun range hardcoded nel codice
- [x] Compilazione con successo
- [x] Sistema espandibile per nuovi suoni

---

**Status**: ✅ **COMPLETO E PRONTO PER TEST**

Il sistema ora è:
- **Leggibile**: CSV corto e chiaro
- **Espandibile**: Aggiungi suoni senza modificare codice
- **Flessibile**: Ogni suono ha i suoi range personalizzati
- **Testabile**: Modifica CSV e riavvia, no ricompilazione

