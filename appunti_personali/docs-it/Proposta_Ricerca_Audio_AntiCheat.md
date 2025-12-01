# Proposta di Ricerca: Obfuscation Audio come Meccanismo Anti-Cheat in AssaultCube

## Abstract
Questa proposta di ricerca intende esplorare l’uso di watermarking e obfuscation audio come meccanismo anti-cheat in un motore di gioco reale (AssaultCube). Sulla base di un’analisi del sottosistema audio del client (OpenAL) e del protocollo di rete esistente (messaggi sonori lato server→client), proponiamo di valutare l’introduzione di un canale audio “autenticato” e personalizzato per utente, su cui applicare marcature impercettibili ma misurabili. L’obiettivo non è sostituire i meccanismi anti-cheat esistenti, bensì aggiungere una dimensione difensiva nuova, mirata a contrastare tecniche di riconoscimento/automazione basate su pattern sonori e a facilitare l’attribuzione forense. La ricerca si focalizza su fattibilità, impatto percettivo, robustezza alle manipolazioni e compatibilità con l’architettura di gioco.

## Introduzione e Contesto
AssaultCube è un FPS open-source che utilizza OpenAL per la riproduzione audio e una pipeline consolidata per la gestione di suoni e musica. L’architettura sonora attuale è basata su:
- un gestore audio nel client, responsabile di inizializzazione, mixing 3D e playback;
- messaggi di rete che trasmettono principalmente trigger/ID di suono dal server al client;
- asset audio locali in formati compressi (OGG) o non compressi (WAV), decodificati e riprodotti tramite OpenAL.

Obiettivo del progetto: investigare l’estensione di questo sottosistema affinché l’audio possa veicolare marcature impercettibili (watermark) e leggere trasformazioni di obfuscation per rendere meno affidabili i metodi di cheating basati su riconoscimento sonoro e, parallelamente, consentire verifica/attribuzione post-evento.

### Riferimenti tecnici nel codice (per mostrare comprensione)
- Gestore: classe di gestione audio del client (inizializzazione dispositivo OpenAL, streaming musica OGG, scheduling sorgenti).
- Definizioni suoni e categorie: file di definizioni che mappa ID→asset e categorie (weapon, movement, voicecom, ecc.).
- Wrappers OpenAL: gestione di sorgenti/buffer e caricamento OGG/WAV, con posizionamento 3D.
- Protocollo di rete: messaggi SV_SOUND / SV_VOICECOM gestiti nel client per scatenare il playback locale.
Questi riferimenti verranno usati solo per orientare la discussione; non si propone in questa sede alcun dettaglio implementativo né codice.

## Analisi del Sottosistema Audio
L’audio in AssaultCube segue uno schema evento→trigger→riproduzione locale:

```
Evento di gioco (es. sparo, passo, voicecom)
           ↓
   Server (logica di gioco)
           ↓
 Messaggio di rete (ID suono)
           ↓
 Client: handler network → risolve ID in asset
           ↓
 Decoding (OGG/WAV) → Buffer → OpenAL Source
           ↓
     Mixing 3D → Playback su dispositivo
```

- Il server invia al client un identificativo del suono; il client seleziona il file corrispondente dagli asset locali, lo decodifica e lo riproduce. 
- La musica di sottofondo è gestita in streaming (OGG) a parte, con priorità più alta e doppio buffering. 
- Le sorgenti sonore (colpi, passi, ambiente) sono soggette a priorità e distanza; l’engine assegna e riassegna canali per evitare saturazioni. 
- L’architettura è performante e stabile, ma il server oggi non invia contenuti audio: trasmette solo trigger/ID. 

Questa analisi suggerisce che introdurre marcature/obfuscation richiede un punto d’inserimento successivo al decoding (PCM) e precedente al mixing, e un meccanismo di distribuzione dei contenuti o dei parametri di trasformazione deciso dal server.

## Motivazione della Ricerca Anti-Cheat Audio
Diversi cheat moderni si basano su riconoscimento di pattern sonori (audio-based triggers) o sfruttano stream audio puliti per coordinare automatismi (es. allerta su headshot, latch su reload). Un canale audio indistinguibile e riproducibile consente a tool esterni di allenare classificatori robusti.

L’introduzione di watermarking/obfuscation mira a:
- impedire riconoscimento deterministico dei suoni (riducendo l’affidabilità di trigger automatizzati);
- consentire l’attribuzione forense (watermark per-client) in presenza di registrazioni;
- aumentare il costo di sviluppo dei cheat, spostando la barriera tecnica verso la rimozione/neutralizzazione di marcature.

La sfida è bilanciare robustezza e impercettibilità, evitando impatti negativi sull’esperienza utente e sulla compatibilità tra client.

## Idea di Estensione (concetto, non implementazione)
Si propone di esplorare due direttrici complementari, senza vincolarsi a una soluzione unica:

1) **Obfuscation parametrica lato client**
- Applicare micro-trasformazioni deterministiche ma personalizzate (es. lievi variazioni di pitch, equalizzazione o fase) al segnale PCM dopo il decoding e prima del mixing. 
- Parametri dipendenti da un identificatore del client o da un seed condiviso con il server. 
- Effetto atteso: suoni soggettivamente identici ma non perfettamente coincidenti tra client diversi, riducendo l’efficacia del riconoscimento automatico.

2) **Watermarking per-client**
premessa: Potrebbe essere compleassa in quanto richiede un po’ di conoscenze su segnali digitali e FFT, ma forse da quello che ho letto si può farne una versione semplice con pseudorandom noise anche se non saprei come procedere. Nei forum online ho trovato questo:

- Inserire una marcatura a bassa ampiezza, distribuita nello spettro (approccio a larga banda) o su bande selettive, per codificare un identificativo per-client o per-sessione.
- La marcatura dovrebbe essere robusta a ricampionamento, compressione, downmix e a moderate perturbazioni di rete/driver.
- Effetto atteso: possibilità di attribuzione in registrazioni esterne e supporto a verifiche post-evento.

Opzionalmente, si potrebbe valutare una terza direttrice:
- **Distribuzione controllata di contenuti audio**: in alcuni casi, inviare dal server al client asset o varianti parametrizzate (via meccanismi di autodownload già esistenti), mantenendo compatibilità e conservando cache locali. L’obiettivo non è il trasferimento massivo, ma abilitare contenuti sonori “firmati” o con parametri di marcatura aggiornabili.

## Possibile Piano di Validazione (qualitativo)
La validazione dovrà misurare con metodi riproducibili tre dimensioni: percezione, robustezza e impatto prestazionale.

### Categorie di verifica
- **Percezione/UX**: test di ascolto controllati (ABX) su campioni con e senza marcatura/obfuscation; scala MOS (Mean Opinion Score) su qualità percepita; soglia di accettabilità predefinita. 
- **Robustezza/Anti‑manipolazione**: resistenza a ricampionamento, ricompressione, equalizzazione, downmix mono, registrazione via loopback o microfono esterno; valutazione percentuale di recupero della marcatura. 
- **Impatto prestazionale**: misure di latenza end‑to‑end evento→playback; utilizzo CPU nel thread audio; stabilità sotto carico (eventi sonori simultanei, molte sorgenti concorrenti). 
- **Compatibilità**: test incrociati tra client “modificati” e client legacy, garantendo che i sistemi convivano (i client legacy continuano a riprodurre suoni regolarmente).

### Metriche principali (indicative)
- Latenza aggiuntiva media e massima (ms) introdotta dalla pipeline di marcatura.
- MOS minimo accettabile (>4/5) in condizioni tipiche di gioco.
- Tasso di riconoscimento watermark su registrazioni reali (>90% su campioni non degradati; >80% con degradazioni moderate).
- Overhead CPU (<5% rispetto al baseline su hardware di riferimento).

### Tipologia di esperimenti
- Sessioni di gioco standard con diversi dispositivi audio (altoparlanti integrati, cuffie USB, Bluetooth) e piattaforme. 
- Registrazioni parallele (cattura interna/esterna) per testare robustezza watermark. 
- Scenari di rete con jitter, perdita e latenza simulati; stress test con burst di eventi sonori. 
- Confronto tra più tecniche (pitch, EQ, spread-spectrum) per trade‑off qualità/robustezza.

## Sfide e Domande Aperte
- **Modellazione psicoacustica**: quali mascheramenti sfruttare per mantenere impercettibilità e massimizzare robustezza? 
- **Parametrizzazione per‑client**: quali spazi di parametri minimizzano collisioni e massimizzano distinguibilità in presenza di rumore e dispositivi eterogenei? 
- **Sicurezza del canale parametri**: come distribuire seed/parametri in modo autenticato e resiliente a MITM, senza introdurre trust eccessivo nel client? 
- **Interazione con mixing 3D**: come garantire che doppler, attenuazione e riassegnazione di sorgenti non degradino eccessivamente il watermark? 
- **Valutazione forense**: disegno di protocolli di attribuzione che rispettino privacy, minimizzino falsi positivi e forniscano valore probatorio. 
- **Compatibilità e standard**: in che misura queste tecniche si estendono ad altri motori basati su OpenAL o librerie simili?


## Conclusioni e Prossimi Passi
La proposta suggerisce un percorso incrementale per introdurre watermarking e obfuscation audio in un contesto reale, con attenzione a compatibilità, qualità percepita e robustezza. La fase successiva prevede la selezione di una o due tecniche prioritarie, la definizione di un protocollo leggero di distribuzione parametri e l’impostazione della campagna di test qualitativa e quantitativa.

L’obiettivo di questo documento è stimolare un confronto con i relatori su: priorità metodologiche, criteri di accettazione (qualità/overhead), e impostazione della validazione sperimentale. Il feedback guiderà la scelta finale delle tecniche e la pianificazione dell’implementazione prototipale.



##COSE IMPORTANTI DA RIUNIONE 

fare delle modifche di piccoli pitch 
sviluppatore usa secml per avversarial machine leraning

identificare dove c'è la chiamata openal per identificare dove fanno il playdell'audio per vedere come posso modificare l'audio per sentire un pitch altissimo ricompilando assault cube ecc andando a modificare il client

## Tecniche di Obfuscation
Abbiamo tre livelli di complessità
### 1. Pitch Shift Parametrico (Semplice)

avversario machine leraning per fottere il sistema di classificazione 



