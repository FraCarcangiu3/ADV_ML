# 🔫👣 Test Percezione: Mitragliatrice e Passi

**Data:** 17 Ottobre 2024  
**Problema:** Difficoltà a percepire differenze di pitch su mitragliatrice e passi

---

## 🎯 COSA È STATO FATTO

### 1. ✅ Verificato che TUTTI i file audio ricevono pitch shifting

**89+ file audio processati**, inclusi:
- `weapon/auto` - Mitragliatrice (Assault Rifle)
- `weapon/shotgun` - Shotgun
- `player/step` - Passi singoli
- `player/footsteps` - Sequenza passi
- Tutti gli altri suoni (voicecom, reload, ecc.)

**Conclusione:** Il sistema applica correttamente il pitch a TUTTI i suoni OGG.

### 2. ✅ Generati file offline per test specifici

**File generati:**

**Mitragliatrice (`auto`):**
- `auto_p0.wav` - Originale
- `auto_p100.wav` a `auto_p500.wav` - Pitch positivi (+100 a +500 cents)
- `auto_p-100.wav` a `auto_p-300.wav` - Pitch negativi

**Passi (`step`):**
- `step_p0.wav` - Originale
- `step_p100.wav` a `step_p500.wav` - Pitch positivi (+100 a +500 cents)
- `step_p-100.wav` a `step_p-300.wav` - Pitch negativi

**Posizione:** `AC/tools/results/perception_test/`

---

## 🧪 COME TESTARE

### Test Offline (File Audio Isolati)

**Opzione 1: Script Interattivo**
```bash
cd "/Users/francesco03/Documents/GitHub/AssaultCube Server/AC/tools/results/perception_test"
./test_auto_step.sh
```

**Opzione 2: Ascolto Manuale - Mitragliatrice**
```bash
cd "/Users/francesco03/Documents/GitHub/AssaultCube Server/AC/tools/results/perception_test"

# Originale
afplay auto_p0.wav

# +300 cents (dovrebbe essere MOLTO percettibile)
afplay auto_p300.wav

# +500 cents (MASSIMO - dovrebbe essere COMPLETAMENTE diverso)
afplay auto_p500.wav
```

**Opzione 3: Ascolto Manuale - Passi**
```bash
cd "/Users/francesco03/Documents/GitHub/AssaultCube Server/AC/tools/results/perception_test"

# Originale
afplay step_p0.wav

# +300 cents
afplay step_p300.wav

# +500 cents (MASSIMO)
afplay step_p500.wav
```

### Test In-Game

**Script Guidato:**
```bash
cd "/Users/francesco03/Documents/GitHub/AssaultCube Server"
./TEST_MITRAGLIATRICE.sh
```

Lo script ti guiderà attraverso test progressivi:
1. Baseline (0 cents)
2. +200 cents
3. +300 cents
4. +400 cents
5. +500 cents
6. -300 cents

**Test Manuali Rapidi:**

```bash
cd "/Users/francesco03/Documents/GitHub/AssaultCube Server/AC"

# Test +300 cents
AC_ANTICHEAT_PITCH_ENABLED=1 AC_ANTICHEAT_PITCH_CENTS=300 ./source/src/ac_client

# Test +500 cents (MASSIMO)
AC_ANTICHEAT_PITCH_ENABLED=1 AC_ANTICHEAT_PITCH_CENTS=500 ./source/src/ac_client
```

---

## 🔍 ANALISI PROBLEMA

### Perché è Difficile Percepire il Pitch su Questi Suoni?

**1. Mitragliatrice (27608 frames @ 44100 Hz = 0.63 secondi)**
- **Molto breve**: Solo 0.6 secondi
- **Suono percussivo**: Spettro complesso con molto rumore
- **Transiente rapido**: L'attacco del suono è quasi istantaneo
- **In-game**: Mascherato da altri suoni (ambiente, altri spari)

**2. Passi (11926 frames @ 44100 Hz = 0.27 secondi)**
- **ESTREMAMENTE breve**: Solo 0.27 secondi (270 millisecondi)
- **Suono percussivo secco**: Quasi nessun contenuto armonico chiaro
- **In-game**: Ripetuti rapidamente, difficile concentrarsi su uno

**Confronto con Voicecom:**
- **Durata**: 1-2 secondi (3-7x più lungo)
- **Contenuto armonico**: Voce umana con fondamentale chiara
- **Soglia percezione**: 100 cents vs 150-200 cents per percussivi

---

## 📊 ASPETTATIVE REALISTICHE

### Livelli di Percettibilità Attesi

| Cents | Mitragliatrice | Passi | Voicecom | Note |
|------:|----------------|-------|----------|------|
| +100 | ❌ Difficile | ❌ Difficile | ✅ Percettibile | Suoni troppo brevi |
| +150 | ⚠️ Forse | ⚠️ Forse | ✅ Chiaro | Al limite |
| +200 | ⚠️ Leggermente | ⚠️ Leggermente | ✅ Molto chiaro | Sottile su percussivi |
| +300 | ✅ Percettibile | ⚠️ Percettibile | ✅ Evidentissimo | Dovrebbe sentirsi |
| +400 | ✅ Molto percettibile | ✅ Percettibile | ✅ Estremo | Chiaro |
| +500 | ✅ Estremamente diverso | ✅ Molto diverso | ✅ Completamente diverso | MASSIMO |

**Legenda:**
- ❌ = Quasi impercettibile
- ⚠️ = Percettibile con attenzione
- ✅ = Chiaramente percettibile

---

## 💡 SUGGERIMENTI PER MIGLIORARE LA PERCEZIONE

### Durante Test Offline:
1. **Usa cuffie di buona qualità** (non speaker)
2. **Alza il volume** al 70-80%
3. **Ascolta in ambiente silenzioso**
4. **Confronta direttamente**: Originale → Modificato → Originale
5. **Concentrati su**:
   - Mitragliatrice: Il "tono" generale del burst
   - Passi: Il "thud" di impatto

### Durante Test In-Game:
1. **Inizia partita vs bot** (meno caos)
2. **Scegli mappa piccola** (es. ac_douze)
3. **Spara in ambiente silenzioso** (non durante scontri)
4. **Per mitragliatrice**: Spara LUNGHE raffiche continue
5. **Per passi**: Cammina lentamente, ascolta ogni passo

### Se ancora non senti differenze:
- ⚠️ **Possibile**: I suoni sono TROPPO brevi per il cervello di percepire pitch
- 💡 **Alternativa**: Concentrati su **voci** (più lunghe e armoniche)
- 💡 **Tecnico**: Considera che per anti-cheat efficace servono suoni > 0.5s

---

## 🎯 RACCOMANDAZIONI FINALI

### Per il Progetto Anti-Cheat:

**1. Se anche +500 cents è difficile da percepire:**
- ✅ Il sistema funziona correttamente
- ⚠️ Suoni percussivi brevi hanno **limitazioni intrinseche**
- 💡 **Focus su voci e suoni lunghi** (>1 secondo)

**2. Valori Ottimali per Anti-Cheat:**
- **Voci/Voicecom**: ±150-200 cents (percettibili ma naturali)
- **Suoni lunghi** (reload, ambiente): ±200-300 cents
- **Suoni brevi** (spari, passi): ±300-500 cents (se serve percettibilità)

**3. Considerazioni Tecniche:**
- La percezione del pitch **richiede tempo**
- Suoni <300ms: pitch difficile da percepire anche con grandi shift
- Per anti-cheat efficace: Applicare pitch a **suoni lunghi** (>500ms)
- Suoni brevi: Considerare altre tecniche (filtering, distorsione)

---

## 📝 PROSSIMI PASSI

**Da fare:**
1. [ ] Ascolta `auto_p500.wav` e `auto_p0.wav` offline - Confronto diretto
2. [ ] Ascolta `step_p500.wav` e `step_p0.wav` offline - Confronto diretto
3. [ ] Se senti differenze offline ma NON in-game → Bug integrazione
4. [ ] Se NON senti differenze nemmeno offline → Limitazione fisiologica
5. [ ] Testa con altre persone per conferma

**Compila:**
```
□ Offline auto_p500: Differenza percettibile? SÌ/NO
□ Offline step_p500: Differenza percettibile? SÌ/NO
□ In-game +500 mitragliatrice: Differenza percettibile? SÌ/NO
□ In-game +500 passi: Differenza percettibile? SÌ/NO

Conclusione:
_________________________________________________
_________________________________________________
```

---

## 🎓 SPIEGAZIONE SCIENTIFICA

### Perché Suoni Brevi Hanno Pitch Meno Percettibile?

**Neuroscienza:**
- Il cervello impiega **~50-100ms** per iniziare a percepire pitch
- Per pitch **accurato**, servono **200-300ms**
- Suoni <300ms: pitch percepito come "qualità timbrica" non come "altezza"

**Psicoacustica:**
- **Principio dell'incertezza temporale-frequenziale**
- Per percepire frequenza precisa serve tempo: Δt × Δf ≥ 1
- Suoni brevi → Δt piccolo → Δf grande (incertezza frequenza alta)

**Pratico:**
- Mitragliatrice (630ms): Al limite minimo per pitch percepibile
- Passo singolo (270ms): Sotto la soglia ottimale
- Voicecom (1-2s): Tempo sufficiente per pitch chiaro

---

**File:** `TEST_MITRAGLIATRICE_E_PASSI.md`  
**Ultimo aggiornamento:** 17 Ottobre 2024  
**Stato:** Pronti per test offline e in-game con valori estremi

