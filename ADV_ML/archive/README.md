# Archive — File Obsoleti e Temporanei

Questa cartella contiene file che sono stati spostati durante la riorganizzazione del progetto ADV_ML.

## 📁 Contenuto

### `output/`
- **Varianti audio generate**: File `.wav` prodotti durante i test coarse → fine
  - `coarse/`: Varianti con range ampi (per identificare regioni candidate)
  - `fine/`: Varianti con range ristretti (intorno alle soglie identificate)
  - `audible_variants/`: Varianti generate per test manuali
- **Motivo archivio**: File numerosi (>200), mantenuti per riferimento ma non essenziali per il funzionamento

### `coarse_results/`
- **Risultati intermedi**: File CSV con risultati parziali dei test coarse per singolo suono
- **Motivo archivio**: Aggregati in `tests/TEST_RESULTS_COARSE.csv`, mantenuti per dettaglio

### Script obsoleti
- `run_abx.py`: Script per test ABX (non più utilizzato)
- `human_test_cli.py`: CLI alternativa per test manuali (sostituito)
- `human_listen_and_label.py`: Script per labeling manuale (versione vecchia)
- `generate_audible_variants.py`: Generazione varianti per test manuali (funzionalità integrata)
- `snrdiff_auto.py`: Calcolo SNR per varianti (mantenuto per compatibilità con `run_all_tests.sh`)

### Documentazione obsoleta
- `SETUP_ADV_ML.md`: Setup iniziale (informazioni integrate in README principale)
- `STATUS_PROGETTO.md`: Status report temporaneo
- `DATASET_READY.md`: Nota temporanea
- `INSTALLAZIONE_COMPLETATA.md`: Nota temporanea
- `QUICK_START.md`: Sostituito da README principale

## 🔄 Compatibilità

I file in `archive/` sono ancora referenziati da:
- `tests/run_all_tests.sh`: Usa `archive/snrdiff_auto.py` per compatibilità
- `scripts/generate_variants.py`: Percorsi aggiornati per puntare a `archive/output/`

## 📝 Note

- **Non eliminare**: Questi file sono mantenuti per:
  - Tracciabilità dei risultati
  - Possibile necessità futura di ri-analisi
  - Compatibilità con script esistenti
  
- **Non distribuire**: Se il progetto viene pubblicato, considerare di:
  - Escludere `archive/output/` (file troppo numerosi)
  - Mantenere solo script e documentazione obsoleta per riferimento

