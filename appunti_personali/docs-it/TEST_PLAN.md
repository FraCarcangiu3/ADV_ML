# 🎵 Piano di Test - Sistema Audio Obfuscato AssaultCube

#STRUTTURA GENERALE
	1.	Introduzione → spiega gli obiettivi generali.
	2.	Sommario Test → tabella che elenca i gruppi di test.
	3.	Casi di Test Dettagliati → descrive ogni test: scenario, passi, criteri di successo, metriche.
	4.	Strumenti di Test → spiega gli script e i tool usati.
	5.	Metriche di Valutazione → elenca i valori numerici che devi misurare.
	6.	Struttura Report Test → formato con cui presentare i risultati.
	7.	Nota per la Tesi → spiega come usare i risultati nel tuo elaborato.

## Introduzione

Questo piano di test valuta l'implementazione di **streaming audio autenticato con watermarking** in AssaultCube. L'obiettivo è verificare che:

1. **Funzionalità core**: Audio streaming funzioni correttamente, i suoni arrivano e si sentano bene 
2. **Sicurezza**: HMAC e firme proteggano da manomissioni
3. **Obfuscation**: Tecniche watermarking siano applicate correttamente
4. **Performance**: Sistema non degradi l'esperienza di gioco
5. **Compatibilità**: Fallback funzioni per client legacy


---

## 📋 Sommario Test

| Categoria | Test Case | Obiettivo | Status |
|-----------|-----------|-----------|---------|
| **Core Functionality** | Test 1-3 | Verifica trasmissione e playback audio | 🔄 Pending |
| **Security & Integrity** | Test 4-6 | Valida protezione HMAC e firme | 🔄 Pending |
| **Obfuscation** | Test 7-9 | Testa tecniche watermarking | 🔄 Pending |
| **Performance** | Test 10-12 | Misura impatto prestazionale | 🔄 Pending |
| **Compatibility** | Test 13-14 | Verifica fallback legacy | 🔄 Pending |
| **Integration** | Test 15-16 | Test con sistemi esterni (VoIP) | 🔄 Pending |

Tutti i test gli ho messi in pending in quanto sono tutti da eseguire ancora. 
---

## 🧪 Casi di Test Dettagliati
Ogni test è scritto con lo stesso formato:
	•	Scenario → cosa voglio verificare;
	•	Setup → come preparo l’ambiente;
	•	Passi → azioni da fare;
	•	Criteri di successo → cosa significa che “funziona”;
	•	Metriche → numeri da misurare.

Vediamoli per gruppi 👇

### Test 1: Trasmissione Audio Base
È il test più importante, perché verifica se tutto il sistema funziona.

**Scenario**: Server invia file audio completo, client riceve e riproduce correttamente.

**Setup**:
```bash
# 1. Avvia server AssaultCube modificato
./ac_server --audio-streaming-enabled

# 2. Avvia client con supporto audio streaming
./ac_client --enable-audio-obfuscation

# 3. Unisciti al server come giocatore normale
```

**Passi**:
1. Server carica file audio `weapon/pistol.ogg` (ID: 8)
2. Giocatore spara con pistola (evento gioco)
3. Server invia `SV_AUDIO_FILE_START` con metadati file
4. Client riceve e alloca struttura `audio_file_t`
5. Server invia chunk sequenziali con `SV_AUDIO_FILE_CHUNK`
6. Client riceve tutti chunk e verifica HMAC
7. Client applica watermarking basato su `client_id`
8. Client riproduce audio dalla cache locale

**Criteri Successo**:
- ✅ Client riceve tutti i chunk senza errori
- ✅ Verifica HMAC passa per tutti i chunk
- ✅ Audio viene riprodotto correttamente
- ✅ Latenza totale < 100ms (misurata da evento a playback)

**Metriche**:
- Tempo trasmissione totale (ms)
- Numero chunk ricevuti vs attesi
- Latenza da evento gioco a playback (ms)
- Utilizzo CPU durante ricezione (%)

---

### Test 2: Gestione Errori - Chunk Mancante
Simula una rete con pacchetti persi per verificare il sistema di “retry”.
Strumento: usa iptables per far perdere casualmente il 10 % dei pacchetti UDP.
Obiettivo: controllare che il client chieda al server di rimandare i pezzi mancanti.
Deve terminare con file integro (checksum corretto)

**Scenario**: Simula perdita di rete per testare meccanismo retry.

**Setup**:
```bash
# Simula perdita chunk con tool di rete
sudo iptables -A INPUT -p udp --dport 28763 -m statistic --mode random --probability 0.1 -j DROP
```

**Passi**:
1. Esegui Test 1 normalmente
2. Durante trasmissione, sistema perde casualmente 10% pacchetti
3. Client rileva chunk mancante tramite sequenza non consecutiva
4. Client invia `SV_AUDIO_RETRY` con `chunk_seq` mancante
5. Server ritrasmette chunk richiesto
6. Processo continua fino completamento

**Criteri Successo**:
- ✅ Client rileva correttamente chunk mancanti
- ✅ Server riceve e processa richieste retry
- ✅ Ritrasmissione funziona correttamente
- ✅ File finale è integro (checksum corretto)

**Metriche**:
- Tempo aggiuntivo dovuto a retry (ms)
- Numero retry richiesti
- Percentuale successo ritrasmissione (%)

---

### Test 3: Latenza Simulata
Simula connessioni lente o variabili (50–200 ms) con tc qdisc.
Obiettivo: verificare che il sistema gestisca bene i ritardi, mantenga i suoni nell’ordine giusto e senza scatti.
Successo se la latenza massima rimane sotto i 300 ms e non ci sono interruzioni.

**Scenario**: Test comportamento con condizioni di rete reali.

**Setup**:
```bash
# Simula latenza variabile 50-200ms
sudo tc qdisc add dev lo root netem delay 100ms 50ms distribution normal
```

**Passi**:
1. Esegui scenario gioco con 4 giocatori
2. Misura latenza end-to-end per eventi audio
3. Test con burst di eventi simultanei (tutti sparano insieme)
4. Verifica ordinamento corretto eventi audio

**Criteri Successo**:
- ✅ Eventi audio mantenuti in ordine temporale corretto
- ✅ Latenza massima < 300ms anche con burst
- ✅ No stuttering o interruzioni audio percepibili

---

### Test 4: Verifica HMAC Difettoso
Verifica che il sistema rilevi un file modificato in transito.
Simulazione: uno script Python intercetta e altera i pacchetti UDP, creando un HMAC errato.
Risultato atteso: il client rifiuta il chunk, chiede un retry, e alla fine ottiene un file valido.
Serve per provare la robustezza della sicurezza.

**Scenario**: Attacco man-in-the-middle modifica chunk audio.

**Setup**:
```python
# Script per modificare chunk in transito
import socket

def tamper_audio_chunk():
    # Intercetta pacchetti UDP su porta 28763
    # Modifica payload chunk aggiungendo rumore
    # Calcola nuovo HMAC errato
    pass
```

**Passi**:
1. Avvia mitmproxy per intercettare traffico
2. Modifica intenzionalmente HMAC di un chunk
3. Verifica che client rifiuti chunk corrotto
4. Server riceve `SV_AUDIO_RETRY` e ritrasmette

**Criteri Successo**:
- ✅ Client rileva e rifiuta chunk con HMAC errato
- ✅ Server gestisce richiesta retry correttamente
- ✅ File finale integro nonostante attacco

---

### Test 5: Attacco Timing
Controlla la protezione anti-hooking.
Un cheat potrebbe manipolare la funzione di aggiornamento audio per saltare controlli.
Il test simula questo scenario e verifica che venga loggato come sospetto e segnalato al server.
Successo: il sistema rileva l’anomalia (>20 ms di gap), logga e invia telemetria.

**Scenario**: Client cerca di bypassare controlli timing.

**Setup**:
```bash
# Script per manipolare timing chiamate audio
void hook_audio_update() {
    // Forza skip aggiornamenti audio periodici
    if (attack_mode) {
        skip_audio_updates(50);  // Salta 50 aggiornamenti
    }
}
```

**Passi**:
1. Implementa hook che salta aggiornamenti `updateaudio()` periodici
2. Sistema dovrebbe rilevare anomalia nei timing
3. Verifica logging evento sospetto
4. Test se giocatore viene disconnesso dopo threshold

**Criteri Successo**:
- ✅ Sistema rileva timing anomalo (>20ms tra aggiornamenti)
- ✅ Evento viene loggato in `audio_security.log`
- ✅ Telemetria inviata al server

---

### Test 6: Verifica Firma Messaggi
Prova la verifica di firme digitali.
Il test intercetta il messaggio SV_AUDIO_FILE_START, cambia il sample_rate e lo rimanda colla vecchia firma.
→ La firma risulta non valida → il client deve rifiutare il messaggio.

**Scenario**: Attacco modifica metadati file audio.

**Setup**:
```bash
# Modifica lunghezza file o sample rate
def tamper_message_signature():
    # Intercetta SV_AUDIO_FILE_START
    # Modifica sample_rate da 44100 a 22050
    # Sistema dovrebbe rifiutare per firma non valida
```

**Passi**:
1. Intercetta messaggio `SV_AUDIO_FILE_START`
2. Modifica campo `sample_rate` nel payload
3. Firma messaggio rimane invariata (attacco)
4. Client dovrebbe rifiutare per firma non valida

**Criteri Successo**:
- ✅ Client rifiuta messaggio con firma non valida
- ✅ Evento sicurezza viene loggato
- ✅ Connessione continua con normale funzionamento

---

### Test 7: Watermarking Pitch Shift

**Scenario**: Test tecnica obfuscation più semplice. Suoni leggermente diversi per ogni client

**Setup**:
```bash
# Test con client_id diversi
for client_id in [12345, 67890, 11111]:
    ./test_obfuscation.py --technique pitch_shift --client_id $client_id
```

**Passi**:
1. Carica stesso file audio per 3 client diversi
2. Applica pitch shift basato su `client_id`
3. Registra output audio di ciascun client
4. Analizza differenze spettroscopiche

**Criteri Successo**:
- ✅ Ogni client produce output audio diverso
- ✅ Differenze sono impercettibili all'ascolto umano
- ✅ Watermark può essere estratto da registrazione

**Metriche**:
- Differenza media spettro tra client diversi (dB)
- Accuratezza estrazione watermark (%)

---

### Test 8: Watermarking EQ Filter. Variazione spettro per watermark

**Scenario**: Test tecnica medio livello.

**Setup**:
```bash
# Applica filtri passa-basso diversi per client_id
./test_eq_watermarking.py --cutoff_freq 2000 --client_id 12345
./test_eq_watermarking.py --cutoff_freq 3000 --client_id 67890
```

**Passi**:
1. Applica filtro passa-basso con cutoff diverso per client
2. Registra output e analizza spettro frequenza
3. Verifica che filtri siano applicati correttamente
4. Test estrazione parametri filtro da registrazione

**Criteri Successo**:
- ✅ Filtri vengono applicati correttamente
- ✅ Parametri filtro possono essere estratti da registrazione
- ✅ Qualità audio rimane buona nonostante filtri

---

### Test 9: Spread-Spectrum Watermarking

**Scenario**: Test tecnica avanzata più robusta.

**Setup**:
```bash
# Embedding watermark 32-bit in file audio
./test_spread_spectrum.py --embed --client_id 12345 --audio_file pistol.ogg
./test_spread_spectrum.py --extract --audio_file pistol_watermarked.wav
```

**Passi**:
1. Embedda 32-bit `client_id` usando spread-spectrum
2. Registra audio watermarked durante gameplay
3. Estrai watermark dalla registrazione
4. Verifica accuratezza estrazione

**Criteri Successo**:
- ✅ Watermark estratto correttamente dalla registrazione
- ✅ Robustezza contro compressione/ricampionamento
- ✅ Impercettibile all'ascolto umano

---

### Test 10: Performance - CPU Usage

**Scenario**: Misura impatto prestazionale obfuscation.
monitor CPU durante gameplay (overhead < 5 %).

**Setup**:
```bash
# Monitor CPU durante gioco intenso
./monitor_cpu_usage.sh --duration 300 --log_file cpu_audio_test.log
```

**Passi**:
1. Gioca sessione deathmatch 5 minuti
2. Monitora utilizzo CPU con/senza obfuscation
3. Confronta con baseline (senza modifiche)

**Criteri Successo**:
- ✅ CPU overhead < 5% rispetto baseline
- ✅ Frame rate rimane stabile (>60 FPS)
- ✅ Memoria utilizzata rimane entro limiti ragionevoli

**Metriche**:
- CPU usage medio (%)
- Memoria utilizzata per cache audio (MB)
- Frame rate medio/minimo durante test

---

### Test 11: Performance - Latenza

**Scenario**: Misura latenza aggiuntiva introdotta.
misurare tempo evento→suono (aggiunta < 50 ms)

**Setup**:
```bash
# Misura latenza evento→audio
./measure_audio_latency.py --test_duration 60 --output latency_results.csv
```

**Passi**:
1. Genera eventi audio controllati (ogni 100ms)
2. Misura tempo da evento a playback effettivo
3. Confronta latenza con/senza streaming

**Criteri Successo**:
- ✅ Latenza aggiuntiva < 50ms rispetto sistema originale
- ✅ Latenza consistente tra eventi diversi
- ✅ No degradazione qualità audio percepibile

---

### Test 12: Scalabilità - Multiplayer

**Scenario**: Test con molti giocatori simultanei.
16 giocatori, tanti eventi simultanei, nessuna perdita d’ordine

**Setup**:
```bash
# Simula 16 giocatori con bot
./multiplayer_test.py --num_players 16 --duration 120
```

**Passi**:
1. Crea partita con 16 giocatori (8 umani + 8 bot)
2. Tutti sparano simultaneamente ogni 2 secondi
3. Monitora performance sistema audio
4. Verifica ordinamento eventi corretto

**Criteri Successo**:
- ✅ Sistema gestisce burst eventi simultanei
- ✅ Ordinamento temporale mantenuto
- ✅ Latenza rimane consistente sotto carico

---

### Test 13: Fallback Client Legacy

**Scenario**: Client vecchio senza supporto streaming.
se un client non supporta lo streaming, il server torna al metodo vecchio (solo ID)

**Setup**:
```bash
# Usa client originale AssaultCube senza modifiche
./ac_client_original --connect server_with_audio_streaming
```

**Passi**:
1. Server ha audio streaming abilitato
2. Client legacy si connette (senza capability bit)
3. Server rileva mancanza supporto
4. Usa metodo originale (solo ID trigger)

**Criteri Successo**:
- ✅ Server rileva correttamente mancanza supporto
- ✅ Fallback funziona perfettamente
- ✅ Client legacy riceve audio normale
- ✅ Nessun impatto su client modificati

---

### Test 14: Versioni Miste

**Scenario**: Mix client nuovi/vecchi sullo stesso server.
test misto, metà client nuovi metà vecchi, tutti funzionano insieme

**Setup**:
```bash
# 50% client nuovi, 50% legacy
./mixed_client_test.py --legacy_ratio 0.5 --num_clients 8
```

**Passi**:
1. 4 client con supporto streaming
2. 4 client legacy senza supporto
3. Eventi audio misti durante gameplay
4. Verifica comportamento corretto entrambi tipi

**Criteri Successo**:
- ✅ Client nuovi ricevono audio streaming
- ✅ Client legacy ricevono trigger tradizionali
- ✅ Nessuna interferenza reciproca
- ✅ Performance rimane buona

---

### Test 15: Integrazione VoIP - Discord
Verifica che il nuovo sistema audio non interferisca con il VoIP.

**Scenario**: Test con Discord/Steam Voice attivo.

**Setup**:
```bash
# 1. Avvia Discord in chiamata vocale
# 2. Avvia AssaultCube con audio obfuscato
# 3. Gioca mentre parli su Discord
```

**Passi**:
1. Unisciti chiamata Discord con altri giocatori
2. Avvia partita AssaultCube con audio streaming
3. Comunica su Discord mentre giochi
4. Registra sessione per analisi

**Criteri Successo**:
- ✅ Voce Discord rimane comprensibile
- ✅ Audio gioco non interferisce con VoIP
- ✅ Watermarking rilevabile anche su registrazione Discord
- ✅ Latenza VoIP rimane buona (<150ms)

**Metriche**:
- Qualità voce soggettiva (1-5 scale)
- Comprensibilità discorso durante eventi audio intensi
- Detection watermarking su registrazione Discord (%)

---

### Test 16: Integrazione VoIP - TeamSpeak

**Scenario**: Test con TeamSpeak durante sessione gaming.

**Setup**:
```bash
# Simile a Test 15 ma con TeamSpeak
./teamspeak_integration_test.py --ts_server 192.168.1.100 --channel "AssaultCube Testing"
```

**Passi**:
1. Configura TeamSpeak per qualità alta
2. Unisciti canale con altri tester
3. Gioca sessione AssaultCube normale
4. Valuta impatto reciproco audio systems

**Criteri Successo**:
- ✅ TeamSpeak qualità rimane buona durante gioco
- ✅ Audio gioco non causa stuttering VoIP
- ✅ Possibile rilevare watermarking su registrazione TS

---

## 🛠️ Strumenti di Test

### Script di Automazione
Una cartella test_framework/ contiene gli script per eseguire i test automaticamente.
Ogni file testa una categoria (funzionalità, sicurezza, obfuscation, ecc.).


```bash
# Test automation framework
./test_framework/
├── run_all_tests.py           # Esegue tutti i test
├── test_audio_functionality.py # Test 1-3
├── test_security.py           # Test 4-6
├── test_obfuscation.py        # Test 7-9
├── test_performance.py        # Test 10-12
└── test_integration.py        # Test 15-16
```

### Tool di Monitoraggio
Script e programmi per misurare CPU, latenza e spettro audio (analisi FFT).

```bash
# Monitoraggio real-time durante test
./monitoring_tools/
├── cpu_monitor.sh             # Monitoraggio CPU
├── latency_monitor.py         # Misurazione latenza
├── audio_analyzer.py          # Analisi spettro audio
└── network_monitor.sh         # Monitoraggio rete
```

### Generazione Report
Uno script finale generate_test_report.py crea un report PDF con risultati, log e grafici.

```bash
# Script generazione report finali
./generate_test_report.py --test_results results/ --output report.pdf
```

---

## 📊 Metriche di Valutazione

### Metriche Primarie (Obbligatorie)

| Metrica | Unità | Target | Metodo Misurazione |
|---------|-------|---------|-------------------|
| **Latenza Audio** | ms | <100ms | Timestamp evento → playback |
| **CPU Overhead** | % | <5% | Monitoraggio durante gameplay |
| **Detection Accuracy** | % | >90% | Test estrazione watermark |
| **False Positive** | % | <1% | Test controlli sicurezza |

### Metriche Secondarie (Opzionali)

| Metrica | Unità | Target | Note |
|---------|-------|---------|------|
| **Qualità Audio Soggettiva** | 1-5 scale | >4.0 | Valutazione umana |
| **Robustezza Watermarking** | % | >85% | Dopo compressione/ricampionamento |
| **Compatibilità Legacy** | % | 100% | Test con client non modificati |

---

## 🗂️ Struttura Report Test

Ogni test deve produrre report con:

```markdown
# Test Report: [Nome Test]

## Setup
- **Ambiente**: [Hardware/Software]
- **Configurazione**: [Parametri specifici]
- **Durata**: [Tempo esecuzione]

## Risultati
- **Criteri Successo**: ✅/❌ per ciascun criterio
- **Metriche**: Tabella valori misurati
- **Osservazioni**: Note qualitative

## Log Eventi
```
[Log tecnici rilevanti]
```

## Conclusioni
- **Passato**: Sì/No con motivazione
- **Problemi Identificati**: Lista issue
- **Raccomandazioni**: Miglioramenti suggeriti
```

---

## 📝 Nota per la Tesi

Questo piano di test è strutturato per fornire **validazione sperimentale rigorosa** della tua proposta. Ogni test case include:

1. **Scenario realistico** che simula uso pratico
2. **Setup riproducibile** con comandi/script specifici
3. **Criteri successo chiari** con metriche quantitative
4. **Strumenti misurazione** definiti

**Per la Sezione Risultati**:
- Usa le tabelle metriche per creare grafici comparativi
- Includi screenshot strumenti di monitoring
- Reporta distribuzione normale delle latenze (non solo medie)

**Per la Sezione Discussione**:
- Analizza trade-off performance vs sicurezza
- Discuti limitazioni tecniche identificate
- Suggerisci ottimizzazioni future basate su risultati

Questo approccio garantisce **validità scientifica** e **riproducibilità** della tua ricerca sperimentale.
