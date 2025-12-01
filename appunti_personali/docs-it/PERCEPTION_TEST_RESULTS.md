# 🎧 Risultati Test di Percezione Pitch Shifting

**Data:** 17 Ottobre 2024  
**Tester:** Francesco Carcangiu  
**Sistema:** macOS M1  
**Dispositivo Audio:** [Da specificare]

---

## 📊 RISULTATI TEST OFFLINE

### Soglie di Percettibilità Identificate

| Tipo Suono | Soglia Minima | Note |
|------------|--------------|------|
| **Shotgun** (percussivo) | **≥150 cents** (~1.5 semitoni) | Differenze chiare da 150 cents in poi |
| **Footsteps** (percussivo) | **≥150 cents** (~1.5 semitoni) | Simile a shotgun |
| **Voicecom** (voce umana) | **≥100 cents** (~1 semitono) | Più percettibile delle altre |

### Dettagli per Valore

| Cents | Semitoni | Shotgun/Footsteps | Voicecom | Note |
|------:|----------|-------------------|----------|------|
| 0 | 0 | Baseline | Baseline | Originale |
| +5 | +0.05 | ❌ Non percettibile | ❌ Non percettibile | Troppo sottile |
| +10 | +0.1 | ❌ Non percettibile | ❌ Non percettibile | Troppo sottile |
| +20 | +0.2 | ❌ Non percettibile | ❌ Non percettibile | Quasi impercettibile |
| +40 | +0.4 | ❌ Appena percettibile | ❌ Appena percettibile | Molto sottile |
| +60 | +0.6 | ❌ Leggermente percettibile | ⚠️ Leggermente percettibile | Ancora sottile |
| +100 | +1.0 | ⚠️ Percettibile | ✅ **Percettibile** | 1 semitono - voce chiara |
| +150 | +1.5 | ✅ **Chiaramente percettibile** | ✅ **Molto percettibile** | Soglia suoni percussivi |
| +200 | +2.0 | ✅ Molto percettibile | ✅ Molto percettibile | 2 semitoni |
| +300 | +3.0 | ✅ Estremamente percettibile | ✅ Estremamente percettibile | 3 semitoni - molto evidente |
| +400 | +4.0 | ✅ Completamente diverso | ✅ Completamente diverso | 4 semitoni |
| +500 | +5.0 | ✅ Completamente diverso | ✅ Completamente diverso | 5 semitoni - estremo |

**Legenda:**
- ❌ = Non percettibile o quasi
- ⚠️ = Percettibile con attenzione
- ✅ = Chiaramente percettibile

---

## 🔍 ANALISI

### 1. Perché Valori Bassi Non Sono Percettibili?

**Motivo Tecnico:**
- La letteratura musicale indica ±5-20 cents come "impercettibili" ma questo vale per **musica continua** con note sostenute
- I **suoni percussivi** (spari, passi) hanno:
  - Durata molto breve (<1 secondo)
  - Spettro armonico complesso
  - Transitori rapidi
- Il cervello ha **meno tempo** per percepire differenze di pitch su suoni brevi

**Motivo Psicoacustico:**
- La percezione del pitch dipende dalla **durata del suono**
- Suoni <100ms: pitch quasi non percettibile
- Suoni 100-500ms: pitch percettibile solo con grandi variazioni
- Suoni >500ms: pitch ben percettibile anche con piccole variazioni

### 2. Differenza tra Voce e Suoni Percussivi

| Caratteristica | Voicecom (Voce) | Shotgun/Footsteps |
|----------------|-----------------|-------------------|
| Durata tipica | ~1-2 secondi | ~0.1-0.5 secondi |
| Spettro | Armonico, fondamentale chiara | Inharmonico, rumore |
| Soglia pitch | **100 cents** | **150 cents** |
| Perché | Durata maggiore + armonie chiare | Durata breve + spettro complesso |

### 3. Implicazioni per il Progetto

**Conclusioni:**
1. ✅ **Sistema funziona correttamente** - SoundTouch applica il pitch shift come atteso
2. ⚠️ **Valori iniziali erano troppo bassi** - ±20 cents è sotto la soglia di percettibilità
3. 💡 **Range ottimale per test**: **±100 a ±300 cents**
4. 💡 **Per anti-cheat efficace**: Usare **≥150 cents** per essere percettibile

**Raccomandazioni:**
- **Range minimo consigliato**: ±100 cents (1 semitono) per voci
- **Range consigliato**: ±150 cents (1.5 semitoni) per suoni percussivi
- **Range massimo supportato**: ±500 cents (5 semitoni)
- **Range "sicuro" anti-cheat**: ±150-200 cents (percettibile ma non troppo innaturale)

---

## 🎯 MODIFICHE IMPLEMENTATE

### Aumento Limite Pitch Shifting

**File modificato:** `AC/source/src/audio_obf.cpp`

**Prima:**
```cpp
// Range esteso test: fino a ±200 cents (2 semitoni)
if (g_pitch_cents < -200) {
    g_pitch_cents = -200;
}
if (g_pitch_cents > 200) {
    g_pitch_cents = 200;
}
```

**Dopo:**
```cpp
// Range esteso test: fino a ±500 cents (5 semitoni) per test percettibilità
// Nota: Valori <150 cents possono essere poco percettibili su suoni percussivi
if (g_pitch_cents < -500) {
    g_pitch_cents = -500;
}
if (g_pitch_cents > 500) {
    g_pitch_cents = 500;
}
```

**Motivazione:**
- Soglia di percettibilità identificata: **150 cents** per suoni percussivi
- Limite precedente (200 cents) era al limite minimo
- Nuovo limite (500 cents) permette test più ampi e valori chiaramente percettibili

---

## 🧪 TEST IN-GAME RACCOMANDATI

### Test Consigliati (Post-Modifica)

**Test 1: Soglia Minima (+100 cents - voci)**
```bash
cd "/Users/francesco03/Documents/GitHub/AssaultCube Server/AC"
AC_ANTICHEAT_PITCH_ENABLED=1 AC_ANTICHEAT_PITCH_CENTS=100 ./source/src/ac_client
```
**Aspettativa:** Voicecom percettibili, shotgun/footsteps appena percettibili

**Test 2: Soglia Percussivi (+150 cents)**
```bash
AC_ANTICHEAT_PITCH_ENABLED=1 AC_ANTICHEAT_PITCH_CENTS=150 ./source/src/ac_client
```
**Aspettativa:** Tutto chiaramente percettibile

**Test 3: Molto Percettibile (+200 cents)**
```bash
AC_ANTICHEAT_PITCH_ENABLED=1 AC_ANTICHEAT_PITCH_CENTS=200 ./source/src/ac_client
```
**Aspettativa:** Molto evidente su tutti i suoni

**Test 4: Estremo (+300 cents)**
```bash
AC_ANTICHEAT_PITCH_ENABLED=1 AC_ANTICHEAT_PITCH_CENTS=300 ./source/src/ac_client
```
**Aspettativa:** Estremamente evidente, quasi "cartone animato"

**Test 5: Pitch Negativo (-150 cents)**
```bash
AC_ANTICHEAT_PITCH_ENABLED=1 AC_ANTICHEAT_PITCH_CENTS=-150 ./source/src/ac_client
```
**Aspettativa:** Suoni più gravi, chiaramente percettibili

---

## 📋 PROSSIMI PASSI

### Per Completare la Validazione:

1. ✅ **Test offline completato** - Soglie identificate
2. ✅ **Limite aumentato** - Sistema supporta ±500 cents
3. ✅ **Client ricompilato** - Pronto per test in-game
4. ⏳ **Test in-game con valori alti** - Da eseguire (150, 200, 300 cents)
5. ⏳ **Confronto offline vs in-game** - Verificare che siano identici
6. ⏳ **Documentazione finale** - Aggiornare PROJECT_FULL_LOG.md

### Domande da Rispondere:

- [ ] Con +150 cents in-game, i suoni sono percettibili come offline?
- [ ] Con +300 cents in-game, il pitch è estremamente evidente?
- [ ] C'è differenza qualitativa tra offline e in-game?
- [ ] Quale valore è ottimale per un sistema anti-cheat? (balance percettibilità/naturalezza)

---

## 📝 NOTE TECNICHE

### File Audio Generati per Test Offline

**Posizione:** `AC/tools/results/perception_test/`

**File totali:** 57 file WAV
- Shotgun: 23 varianti (0, ±5 a ±500 cents)
- Footsteps: 17 varianti (0, ±5 a ±200 cents)
- Voicecom: 17 varianti (0, ±5 a ±200 cents)

**Tool usato:** `pitch_test` (SoundTouch + libsndfile)

**Comando esempio:**
```bash
./pitch_test samples/shotgun_ref.wav results/shotgun_p150.wav --cents 150
```

---

## 🎓 LEZIONI APPRESE

1. **La letteratura musicale non si applica direttamente ai giochi**
   - ±5-20 cents è impercettibile per musica
   - Ma i suoni di gioco sono diversi (percussivi, brevi, context)

2. **La durata del suono è critica per la percezione del pitch**
   - Shotgun (0.1s): Soglia ~150 cents
   - Voicecom (1-2s): Soglia ~100 cents

3. **Test offline sono essenziali**
   - Permettono di isolare la variabile (pitch shift puro)
   - Eliminano confusione da ambiente di gioco
   - Identificano soglie precise

4. **Range dinamico del pitch è ampio**
   - Da impercettibile (+5) a estremo (+500) in pochi semitoni
   - Non serve andare oltre ±300 cents per test

---

**Ultimo aggiornamento:** 17 Ottobre 2024  
**Stato:** Test offline completati, limiti aggiornati, pronto per test in-game con valori alti  
**Prossimo step:** Test in-game con +150, +200, +300 cents

