# 🎮 AssaultCube Server - Sistema Anti-Cheat Audio

Progetto di ricerca per proteggere AssaultCube da riconoscimento audio automatico tramite perturbazioni DSP (obfuscation).

---

## 📁 Struttura Progetto

```
AssaultCube Server/
├── 📖 README.md                    ← Questo file (indice principale)
│
├── 🎮 AC/                          ← Modifiche al client AssaultCube
│   └── source/src/audio_runtime_obf.cpp  ← Implementazione C++
│
├── 🐍 ADV_ML/                      ← Sistema Python per test offline
│   ├── README.md                   ← Indice ADV_ML
│   ├── offline_perturb.py         ← Script principale
│   ├── audio_effects.py           ← Effetti audio
│   └── docs/                       ← Documentazione organizzata
│
├── 📚 docs/                        ← Documentazione progetto
│   ├── guide/                      ← Guide pratiche
│   ├── modifiche/                  ← Modifiche al codice
│   └── proposte/                   ← Proposte future
│
├── 📝 discorso.md                  ← Discorso per relatore (aggiornato)
├── 📝 discorso_fase1_fase2.md      ← Discorso fase 1&2 (aggiornato)
│
├── 📄 TESI_ANTICHEAT.md            ← Documento tesi (italiano)
└── 📄 THESIS_ANTICHEAT.md          ← Documento tesi (inglese)
```

---

## 🎯 Cosa Fa Questo Progetto

### Obiettivo
Proteggere AssaultCube da riconoscimento audio automatico tramite perturbazioni audio che:
- ✅ Mantengono la qualità del suono accettabile per i giocatori
- ✅ Confondono i modelli ML di riconoscimento
- ✅ Sono applicate in tempo reale durante il gameplay

### Come Funziona

1. **Client C++** (`AC/`) - Applica perturbazioni in tempo reale:
   - Pitch shift (modifica frequenza)
   - White/Pink noise (rumore)
   - EQ tilt (equalizzazione)
   - Filtri HP/LP (filtri frequenza)

2. **Sistema Python** (`ADV_ML/`) - Test offline:
   - Replica gli stessi effetti del client
   - Applica ai dataset per testare efficacia ML
   - Genera CSV per valutazione modelli

---

## 🚀 Quick Start

### Per Testare il Sistema Python

```bash
# Vai nella cartella ADV_ML
cd ADV_ML

# Leggi la guida
cat README.md

# Genera CSV con perturbazioni
python offline_perturb.py --help
```

### Per Modificare il Client C++

Vedi `AC/source/src/audio_runtime_obf.cpp` per l'implementazione.

---

## 📚 Documentazione

### Guide Pratiche (`docs/guide/`)
- `GUIDA_OFFLINE_PERTURB_STEP_BY_STEP.md` - Guida step-by-step completa
- `FASE1_FASE2_RIEPILOGO.md` - Riepilogo fase 1 e 2
- `ML_PIPELINE_COLLEAGUE_OVERVIEW.md` - Overview pipeline ML

### Sistema ADV_ML (`ADV_ML/`)
- `ADV_ML/README.md` - Indice completo del sistema Python
- `ADV_ML/docs/` - Documentazione organizzata per argomento

### Modifiche (`docs/modifiche/`)
- `AC_MODIFICATIONS(beforeML).md` - Modifiche al codice prima del ML

---

## 🔧 Ultime Modifiche (Novembre 2024)

### ✅ Correzione: Rumore Solo sul Segnale
Il rumore viene ora applicato **solo durante lo sparo**, non sul silenzio.
- Migliora il realismo (simula comportamento reale)
- Mantiene i silenzi originali (~77% dell'audio)
- Vedi `ADV_ML/docs/corrections/` per dettagli

### ✅ Organizzazione Documentazione
Tutta la documentazione è stata organizzata:
- `ADV_ML/docs/` - Documentazione ADV_ML organizzata
- `docs/` - Documentazione progetto principale

---

## 📝 File Importanti

| File | Cosa Contiene |
|------|---------------|
| `discorso.md` | Discorso per relatore (aggiornato) |
| `discorso_fase1_fase2.md` | Discorso fase 1&2 (aggiornato) |
| `TESI_ANTICHEAT.md` | Documento tesi italiano |
| `THESIS_ANTICHEAT.md` | Documento tesi inglese |
| `ADV_ML/README.md` | Indice sistema Python |
| `docs/guide/GUIDA_OFFLINE_PERTURB_STEP_BY_STEP.md` | Guida completa |

---

## 🎓 Per i Professori

Esempi audio per dimostrazione:
**`ADV_ML/demo_audio_for_professors/`**

Vedi `ADV_ML/demo_audio_for_professors/GUIDA_ASCOLTO.md` per istruzioni.

---

## 📞 Dove Trovare Cosa

| Cosa Cerchi | Dove Guardare |
|-------------|---------------|
| Come usare sistema Python | `ADV_ML/README.md` |
| Guide pratiche | `docs/guide/` |
| Modifiche al codice | `docs/modifiche/` |
| Documentazione ADV_ML | `ADV_ML/docs/` |
| Esempi audio | `ADV_ML/demo_audio_for_professors/` |

---

**Ultimo aggiornamento:** 24 Novembre 2024



#test