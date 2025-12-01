# 🎮 Comandi Rapidi per Test Pitch Shifting - AssaultCube

**Data:** 17 Ottobre 2024 (Aggiornato con valori percettibili)  
**Stato:** ✅ Sistema completamente funzionante - Limiti aumentati a ±500 cents

**⚠️ IMPORTANTE:** Dai test offline, le soglie di percettibilità sono:
- **Voci**: ≥100 cents
- **Suoni percussivi** (spari, passi): ≥150 cents

---

## 🚀 COMANDI RAPIDI

### ✅ Test Base (Audio Normale - Senza Pitch)
```bash
cd "/Users/francesco03/Documents/GitHub/AssaultCube Server/AC"
./source/src/ac_client
```

---

### 🎵 Test Pitch Shifting (VALORI PERCETTIBILI)

**⚠️ Valori sotto 100 cents sono difficili da percepire in-game!**

**Test +100 cents (soglia voci - 1 semitono)**
```bash
cd "/Users/francesco03/Documents/GitHub/AssaultCube Server/AC"
AC_ANTICHEAT_PITCH_ENABLED=1 AC_ANTICHEAT_PITCH_CENTS=100 ./source/src/ac_client
```
✅ **Raccomandato:** Primo test - voci percettibili

**Test +150 cents (soglia suoni percussivi - 1.5 semitoni)**
```bash
cd "/Users/francesco03/Documents/GitHub/AssaultCube Server/AC"
AC_ANTICHEAT_PITCH_ENABLED=1 AC_ANTICHEAT_PITCH_CENTS=150 ./source/src/ac_client
```
✅ **Raccomandato:** Tutti i suoni percettibili

**Test +200 cents (molto percettibile - 2 semitoni)**
```bash
cd "/Users/francesco03/Documents/GitHub/AssaultCube Server/AC"
AC_ANTICHEAT_PITCH_ENABLED=1 AC_ANTICHEAT_PITCH_CENTS=200 ./source/src/ac_client
```
✅ **Raccomandato:** Chiaramente evidente

**Test +300 cents (estremamente percettibile - 3 semitoni)**
```bash
cd "/Users/francesco03/Documents/GitHub/AssaultCube Server/AC"
AC_ANTICHEAT_PITCH_ENABLED=1 AC_ANTICHEAT_PITCH_CENTS=300 ./source/src/ac_client
```
💡 **Estremo ma utile per test**

**Test +500 cents (massimo - 5 semitoni)**
```bash
cd "/Users/francesco03/Documents/GitHub/AssaultCube Server/AC"
AC_ANTICHEAT_PITCH_ENABLED=1 AC_ANTICHEAT_PITCH_CENTS=500 ./source/src/ac_client
```
💡 **Test limite sistema**

**Test -150 cents (pitch più grave - 1.5 semitoni)**
```bash
cd "/Users/francesco03/Documents/GitHub/AssaultCube Server/AC"
AC_ANTICHEAT_PITCH_ENABLED=1 AC_ANTICHEAT_PITCH_CENTS=-150 ./source/src/ac_client
```
✅ **Raccomandato:** Suoni più gravi e profondi

**Test -300 cents (molto più grave - 3 semitoni)**
```bash
cd "/Users/francesco03/Documents/GitHub/AssaultCube Server/AC"
AC_ANTICHEAT_PITCH_ENABLED=1 AC_ANTICHEAT_PITCH_CENTS=-300 ./source/src/ac_client
```
💡 **Estremamente grave**

---

### 🚫 Test NON Raccomandati (Sotto Soglia Percezione)

**Test +5, +10, +20, +40, +60 cents**
- ❌ **Troppo bassi** - Risultati test offline: non percettibili su suoni percussivi
- 💡 Usa invece ≥100 cents per voci o ≥150 cents per suoni percussivi

---

## 🔧 Comandi di Verifica

**Verifica OpenAL-soft è attivo:**
```bash
cd "/Users/francesco03/Documents/GitHub/AssaultCube Server/AC"
./source/src/ac_client 2>&1 | grep "Sound:"
# Output atteso: Sound: OpenAL Soft / OpenAL Soft (OpenAL Community)
```

**Verifica pitch shifting è abilitato:**
```bash
cd "/Users/francesco03/Documents/GitHub/AssaultCube Server/AC"
AC_ANTICHEAT_PITCH_ENABLED=1 AC_ANTICHEAT_PITCH_CENTS=20 ./source/src/ac_client 2>&1 | grep "audio_obf"
# Output atteso: [audio_obf] Pitch shift ENABLED: +20 cents
```

---

## 🛠️ Ricompilazione (se necessario)

```bash
cd "/Users/francesco03/Documents/GitHub/AssaultCube Server/AC/source/src"
make clean
make client -j8
```

---

## 📊 Checklist Test (Valori Percettibili)

- [x] Test offline completato - Soglie identificate
- [x] Limiti aumentati a ±500 cents
- [x] Client ricompilato
- [ ] Test baseline (senza pitch) - Audio funziona
- [ ] Test +100 cents - Soglia voci
- [ ] Test +150 cents - Soglia suoni percussivi ✅ RACCOMANDATO
- [ ] Test +200 cents - Molto percettibile
- [ ] Test +300 cents - Estremamente percettibile
- [ ] Test -150 cents - Pitch più grave
- [ ] Test -300 cents - Molto più grave
- [ ] Confronto offline vs in-game - Verificare identità
- [ ] Annota osservazioni soggettive
- [ ] Determina valore ottimale per anti-cheat
- [ ] Aggiorna PROJECT_FULL_LOG.md con risultati

---

**Per dettagli completi, consulta:** `INGAME_PITCH_TEST_PROCEDURE.md`

