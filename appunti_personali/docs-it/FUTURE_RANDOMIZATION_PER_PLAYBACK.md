# Randomizzazione per Ogni Riproduzione - Idea Implementazione Futura

**Data**: 2025  
**Status**: 🔄 Idea/Proposta  
**Priorità**: Media

---

## 📋 Contesto

Attualmente, il sistema di obfuscation audio randomizza i parametri (pitch, noise, EQ, filtri) **una sola volta** all'inizializzazione del client o al primo caricamento del suono. Durante la stessa sessione di gameplay, tutti gli spari dello stesso tipo di arma utilizzano gli **stessi parametri randomizzati**.

### Comportamento Attuale

- ✅ Randomizzazione avviene all'avvio del client
- ✅ Variabilità garantita tra sessioni diverse
- ❌ Nessuna variabilità all'interno della stessa sessione
- ❌ Tutti gli spari della stessa arma hanno parametri identici

### Problema

Un attaccante che raccoglie dati durante una singola sessione di gameplay potrebbe teoricamente identificare pattern comuni, anche se limitati. La randomizzazione per riproduzione aumenterebbe significativamente l'entropia e la difficoltà di addestramento per modelli ML.

---

## 🎯 Obiettivo

Implementare una randomizzazione dei parametri audio **ad ogni singola riproduzione** del suono, non solo all'inizializzazione. Questo garantirebbe:

1. **Massima variabilità**: Ogni sparo avrebbe parametri diversi
2. **Entropia aumentata**: Impossibile per l'attaccante predire i parametri
3. **Difesa più robusta**: Pattern ML molto più difficili da addestrare

---

## 🔧 Proposta di Implementazione

### Opzione 1: Processing On-The-Fly (Runtime)

**Idea**: Applicare le trasformazioni audio in tempo reale ad ogni riproduzione, senza cache del buffer processato.

**Vantaggi**:
- Massima variabilità (ogni riproduzione è unica)
- Nessun overhead di memoria per buffer multipli
- Implementazione più pulita concettualmente

**Svantaggi**:
- ⚠️ **Overhead CPU**: Processing audio ad ogni riproduzione (pitch shift, EQ, filtri, noise injection)
- ⚠️ **Latenza potenziale**: Potrebbe causare delay nella riproduzione
- ⚠️ **Performance**: Potrebbe essere problematico con molti suoni simultanei

**Fattibilità**: 
- ✅ Tecnicamente fattibile
- ⚠️ Richiede ottimizzazione attenta per evitare lag
- ⚠️ Potrebbe richiedere processing asincrono o thread dedicato

### Opzione 2: Cache Multipla con Varianti

**Idea**: Generare e cachare multiple varianti del suono (es. 10-20 varianti) all'inizializzazione, e selezionare casualmente una variante ad ogni riproduzione.

**Vantaggi**:
- ✅ Basso overhead runtime (solo selezione casuale)
- ✅ Nessuna latenza aggiuntiva
- ✅ Buon compromesso tra variabilità e performance

**Svantaggi**:
- ⚠️ **Overhead memoria**: N varianti × dimensione buffer (per ogni suono)
- ⚠️ **Variabilità limitata**: Solo N varianti possibili (non infinita)
- ⚠️ **Memoria crescente**: Con molti suoni, memoria potrebbe diventare significativa

**Fattibilità**:
- ✅ Molto fattibile
- ✅ Bilanciamento buono tra variabilità e risorse
- ✅ Implementazione relativamente semplice

### Opzione 3: Hybrid - Cache + On-The-Fly per Suoni Critici

**Idea**: Utilizzare cache multipla per suoni comuni (spari, passi) e processing on-the-fly per suoni rari o meno critici.

**Vantaggi**:
- ✅ Bilanciamento ottimale risorse/variabilità
- ✅ Flessibilità nella configurazione

**Svantaggi**:
- ⚠️ Complessità implementativa maggiore

---

## 📊 Analisi Performance

### Stima Overhead Opzione 1 (On-The-Fly)

**Processing per suono**:
- Pitch shift: ~2-5 ms (dipende da algoritmo)
- EQ tilt: ~1-2 ms
- HP/LP filters: ~1-3 ms
- Noise injection: ~0.5-1 ms
- **Totale stimato**: ~5-11 ms per suono

**Scenario**: 10 suoni simultanei = ~50-110 ms overhead totale
- ⚠️ Potrebbe essere percepibile come lag

### Stima Overhead Opzione 2 (Cache Multipla)

**Memoria per suono** (es. `weapon/usp`, ~100KB PCM):
- 10 varianti: ~1 MB
- 20 varianti: ~2 MB
- 50 varianti: ~5 MB

**Totale progetto** (es. 50 suoni critici):
- 10 varianti: ~50 MB
- 20 varianti: ~100 MB
- 50 varianti: ~250 MB

**Runtime**: ~0.01 ms (solo selezione casuale)

---

## 🎯 Raccomandazione

**Opzione 2 (Cache Multipla)** sembra essere il miglior compromesso:

1. ✅ Performance runtime eccellente (nessun lag)
2. ✅ Variabilità molto buona (10-20 varianti per suono)
3. ✅ Memoria accettabile (50-100 MB per suoni critici)
4. ✅ Implementazione relativamente semplice

**Configurazione suggerita**:
- **Suoni critici** (spari armi principali): 20 varianti
- **Suoni comuni** (passi, ricarica): 10 varianti
- **Suoni rari**: 5 varianti o cache singola

---

## 🔨 Implementazione Tecnica (Opzione 2)

### Modifiche al Codice

1. **Estendere `audio_file_t` struttura**:
   ```cpp
   struct audio_file_t {
       // ... campi esistenti ...
       std::vector<PCMBuffer> variant_buffers;  // Cache varianti
       int num_variants;
   };
   ```

2. **Generazione varianti all'inizializzazione**:
   ```cpp
   void generate_audio_variants(audio_file_t *afile, int num_variants) {
       for (int i = 0; i < num_variants; i++) {
           // Randomizza parametri
           int pitch = randomize_pitch_uniform(...);
           float snr = randomize_snr_uniform(...);
           // ... altri parametri ...
           
           // Processa audio con parametri
           PCMBuffer variant = process_audio(afile->original_buffer, 
                                             pitch, snr, ...);
           afile->variant_buffers.push_back(variant);
       }
   }
   ```

3. **Selezione casuale ad ogni riproduzione**:
   ```cpp
   PCMBuffer* get_random_variant(audio_file_t *afile) {
       if (afile->variant_buffers.empty()) {
           return &afile->original_buffer;  // Fallback
       }
       int idx = random_int(0, afile->variant_buffers.size() - 1);
       return &afile->variant_buffers[idx];
   }
   ```

### Configurazione CSV

Aggiungere campo opzionale per numero di varianti:
```csv
file_name,min_pitch_cents,max_pitch_cents,...,num_variants
weapon/usp,-200,500,...,20
weapon/ak47,-200,500,...,20
footstep1,0,0,...,10
```

---

## ⚠️ Considerazioni

### Compatibilità

- ✅ Compatibile con sistema attuale (estensione, non sostituzione)
- ✅ Flag configurabile: `AC_AUDIO_OBF_VARIANTS=20` (numero varianti)

### Testing

- Test performance: misurare overhead memoria e CPU
- Test percettivo: verificare che variabilità non sia eccessiva
- Test entropia: validare che varianti siano effettivamente diverse

### Limitazioni

- Memoria: limitare numero varianti per suoni non critici
- Compatibilità: mantenere fallback a comportamento attuale se `num_variants=1`

---

## 📝 Note Finali

Questa implementazione rappresenterebbe un **miglioramento significativo** della sicurezza anti-cheat, aumentando l'entropia del sistema e rendendo molto più difficile l'addestramento di modelli ML da parte di attaccanti.

**Priorità di implementazione**: Media-Alta (dopo ottimizzazioni e validazioni del sistema attuale)

**Stima sforzo**: 2-3 giorni di sviluppo + testing

---

## 🔗 Riferimenti

- Implementazione attuale: `AC/source/src/audio_runtime_obf.cpp`
- Documentazione randomizzazione: `ADV_ML/docs/randomization_guide.md`
- Tesi: `TESI_ANTICHEAT.md` - Sezione 7.4

