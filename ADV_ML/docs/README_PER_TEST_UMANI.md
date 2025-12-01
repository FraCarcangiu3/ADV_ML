# Guida Semplice x Test manuali (coarse → fine)

Questa guida ti aiuta, passo per passo, a fare i test di ascolto per capire quando il pitch-shift è percepibile (min_perc) e fino a quanto la qualità è ancora accettabile (max_ok). Non servono competenze avanzate.

## 1) Cosa sono i test coarse → fine e perché
- "Coarse": proviamo pochi valori ma molto distanti (es. 0, ±10, ±25, ±50, ±100 cents) per capire grossolanamente dove iniziamo a sentire differenze.
- "Fine": dopo il coarse, zoomiamo in una finestra più piccola (±20 cents) con passo fine (2 cents) per trovare meglio le soglie.
- Perché: ci serve un metodo rapido e oggettivo per scegliere i range da usare in gioco, bilanciando efficacia anti-cheat e qualità percepita.

## 2) Cartelle e file importanti
- `listening_set/`
  - contiene, per ogni suono, i file da ascoltare (controllo vicino a 0, candidati vicino a min_perc, esempi più distorti).
- `plots/`
  - immagini `snr_vs_pitch_<sound>.png` con grafico SNR (dB) in funzione del pitch.
- `TEST_RESULTS_FINE.csv`
  - risultati numerici completi (riga per variante) con la colonna chiave `snr_db`.
- `TEST_SUMMARY_FINE.md`
  - riassunto test e istruzioni rapide.

## 3) Come ascoltare i suoni e annotare min_perc / max_ok
Puoi usare un qualsiasi player audio. Su macOS:
```bash
cd ADV_ML/tests/listening_set/auto
afplay auto_ref.wav
afplay auto__fine__type-p__val-2.0__trial-1.wav
afplay auto__fine__type-n__val-4.0__trial-2.wav
```
Suggerimenti pratici:
- Confronta sempre con il file `*_ref.wav` (riferimento).
- Parti dai valori più vicini a 0 (±2, ±4, ±6 cents) e poi sali.
- "min_perc": il PRIMO valore (in assoluto) a cui noti una differenza rispetto al riferimento.
- "max_ok": l’ULTIMO valore (sempre in assoluto) che ancora ti sembra accettabile (rating ≥ 4/5). Oltre, la qualità degrada troppo.
- Se vuoi annotare feedback, usa il template: `listening_set/subjective_results_template.csv`.

Esempio di ascolto su Windows/Linux (o alternative):
- Windows: doppio click sul file o usare VLC
- Linux: `ffplay file.wav` (da `ffmpeg`), o qualsiasi player grafico

## 4) Come leggere i risultati numerici (snr_db)
Apri `TEST_RESULTS_FINE.csv` con un editor o Excel. Le colonne chiave sono:
- `applied_pitch_cents`: entità dello shift (cents)
- `snr_db`: rapporto segnale/rumore calcolato rispetto al riferimento

Regole guida (proxy):
- `min_perc` ≈ primo pitch (in valore assoluto) dove `snr_db < 35 dB`
- `max_ok` ≈ ultimo pitch (in valore assoluto) dove `snr_db > 25–30 dB`

Nota: SNR è un proxy oggettivo. La decisione finale considera anche l’ascolto soggettivo (punto 5).

## 5) Come combinare ascolto + SNR per scegliere i range
Procedura consigliata:
1. Dai numeri (CSV): individua un candidato `min_perc` (prima soglia < 35 dB) e un candidato `max_ok` (ultima soglia > 25–30 dB).
2. Dagli ascolti: verifica che quei punti corrispondano a ciò che percepisci davvero (confronta con il riferimento).
3. Se l’ascolto dice che un valore è già fastidioso, riduci `max_ok`. Se non senti differenze a una soglia proposta, aumenta leggermente `min_perc`.
4. Scrivi il range finale in `AC/audio_obf_config.csv`.

Esempio di riga:
```csv
weapon/auto.ogg,-15,30,white,35,,
```
Qui: min_pitch=-15, max_pitch=30 (cents), con rumore bianco a 35 dB (opzionale), senza toni.

## 6) Cosa leggere dopo (ordine consigliato)
1. `TEST_SUMMARY_FINE.md` (overview e parametri)
2. `plots/snr_vs_pitch_<sound>.png` (capisci dove cadono le soglie)
3. `TEST_RESULTS_FINE.csv` (dettaglio numerico)
4. `listening_set/<sound>/` (ascolto soggettivo finale)
5. `AC/audio_obf_config.csv` (aggiorna i range conclusivi)

## 7) Prossimi passi
Step 3 sarà la **randomizzazione** in produzione: una volta scelti i range per ogni suono, il client potrà applicare piccoli shift casuali (dentro i limiti accettabili) a ogni avvio o sessione, rendendo più difficile l’addestramento dei bot di cheating.

---

## Mini-tabella (compila i valori scelti)

| Suono | min_perc (cents) | max_ok (cents) | Note |
|---|---:|---:|---|
| weapon/auto.ogg |  |  |  |
| player/footsteps.ogg |  |  |  |
| voicecom/affirmative.ogg |  |  |  |

Suggerimento: mantieni anche un piccolo log personale di come hai deciso i valori (file ascoltati, commenti, cosa ti ha fatto propendere per quel range).


