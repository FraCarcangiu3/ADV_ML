# 📚 Indice Documentazione ADV_ML

Questa cartella contiene tutta la documentazione organizzata per argomento.

---

## 🎵 Perturbazioni Audio

**📁 `perturbazioni/`**

### `README_OFFLINE_PERTURB.md` ⭐
**Guida completa all'uso delle perturbazioni**

- Come generare CSV con perturbazioni
- Tutti gli effetti disponibili (pitch, noise, EQ, filtri)
- Esempi di comandi pronti all'uso
- Corrispondenza con client C++
- **LEGGI QUESTO PRIMA** se vuoi usare il sistema

---

## 🧪 Test e Validazione

**📁 `test/`**

### `RISPOSTA_ZERI_CSV.md`
**Perché ci sono tanti zeri nei CSV?**

- Spiegazione semplice del problema
- Perché gli audio hanno ~77% zeri
- Confronto tra diversi tipi di perturbazione
- **Leggi questo** se ti chiedi perché i CSV hanno molti zeri

### `REPORT_TEST_PIPELINE.md`
**Report completo dei test eseguiti**

- Risultati dei test su 3 file FLAC
- Statistiche dettagliate
- Validazione del sistema
- **Leggi questo** per vedere i risultati dei test

---

## 🔧 Correzioni Applicate

**📁 `corrections/`**

### `CORREZIONE_RUMORE_SOLO_SEGNALE.md`
**Correzione: rumore applicato solo sul segnale**

- Problema originale
- Soluzione implementata
- Modifiche al codice
- Risultati prima/dopo
- **Leggi questo** per capire la correzione tecnica

### `SUMMARY_CORREZIONE.md` ⭐
**Riassunto delle correzioni**

- Cosa è stato modificato
- Come rigenerare i CSV
- Checklist completa
- FAQ
- **Leggi questo** se devi rigenerare CSV con rumore

---

## 📋 Ordine di Lettura Consigliato

### Per iniziare:
1. ⭐ `perturbazioni/README_OFFLINE_PERTURB.md` - Come usare il sistema
2. `test/RISPOSTA_ZERI_CSV.md` - Capire i CSV

### Se hai problemi:
1. `corrections/SUMMARY_CORREZIONE.md` - Correzioni applicate
2. `test/REPORT_TEST_PIPELINE.md` - Verifica risultati test

### Per approfondire:
1. `corrections/CORREZIONE_RUMORE_SOLO_SEGNALE.md` - Dettagli tecnici

---

**Torna all'indice principale:** `../README.md`

