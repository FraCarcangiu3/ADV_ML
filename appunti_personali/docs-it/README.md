# 🎵 Sottosistema Audio di AssaultCube - Documentazione Tecnica Completa
#Lavoro a cura di Francesco Carcangiu

## Introduzione e Obiettivi

Questa documentazione analizza in dettaglio il **sottosistema audio** del gioco **AssaultCube**, un FPS open-source basato su Cube Engine. L'obiettivo è comprendere l'architettura esistente e proporre estensioni per supportare **tecniche di obfuscation e watermarking audio** per scopi anti-cheat.

**introduzione**: L'audio digitale è come un film: il computer deve "disegnare" migliaia di fotogrammi al secondo per creare suoni fluidi. Qui vedremo come funziona questo processo passo-passo, dai bit ai tuoi altoparlanti.

**Sviluppatore Esperto**: Analisi completa del sistema OpenAL-based con proposta di estensione per streaming audio autenticato e watermarking spread-spectrum.

## 📋 Sommario
- [Scansione del Codice](#scansione-del-codice)
- [Architettura Audio](#architettura-audio)
- [Flusso Server-Client](#flusso-server-client)
- [Proposta di Modifica](#proposta-di-modifica)
- [Tecniche di Obfuscation](#tecniche-di-obfuscation)
- [Sicurezza e Anti-Tamper](#sicurezza-e-anti-tamper)
- [Piano di Test](#piano-di-test)
- [Glossario](#glossario)
- [Riferimenti](#riferimenti)

---

## Scansione del Codice

### Comandi di Ricerca Eseguiti

```bash
#Utilizzo i comandi grep e find per cercare parole chiavi nel codice sorgente in modo da poter risparmiare tempo

# Scansione componenti audio principali
grep -r -n "sound\|audio\|playSound\|playsound" /AC/source/src/

# Ricerca formati audio supportati
grep -r -n "\.wav\|\.ogg" /AC/source/src/

# Identificazione librerie audio
grep -r -n "OpenAL\|SDL_mixer\|alSourcePlay" /AC/source/src/

# Protocollo di rete per suoni
grep -r -n "SV_SOUND\|SV_VOICECOM\|message\|netmsg" /AC/source/src/

# Asset audio effettivi
find /AC/packages/audio -name "*.ogg" -o -name "*.wav"

```
##Tutte queste ricerche dovrebbero permettermi di trovare:
	•	Dove i suoni vengono riprodotti (playsound);
	•	Dove vengono caricati (.wav / .ogg);
	•	Dove si trovano i messaggi di rete (server → client);
	•	Dove sono gli asset audio sul disco (/AC/packages/audio/).


### File Rilevanti Identificati

| File | Ruolo | Componenti Chiave |
|------|-------|------------------|
| `sound.h` | **Definizioni Core** | 103 suoni enum, categorie SC_*, struttura soundcfgitem |
| `audiomanager.cpp` | **Gestore Audio** | Classe principale, inizializzazione OpenAL, funzioni playsound() importante perchè gestisce tutto l'audio del gioco (inizializza, riproduce, aggiorna) |
| `server.h` | **Configurazione Server** | Array soundcfg[] con metadati suoni |
| `openal.cpp` | **Wrapper OpenAL** | Classi source/sbuffer, caricamento WAV/OGG, usa OpenAL per parlare con la scheda audio |
| `oggstream.cpp` | **Streaming Musica** | Classe oggstream per riproduzione musicale |
| `protocol.h` | **Messaggi Rete** | Enum SV_SOUND, SV_VOICECOM, SV_VOICECOMTEAM |
| `clients2c.cpp` | **Handler Client** | Ricezione messaggi audio da server, gestiscono i messaggi di rete legati al suono |
| `packages/audio/` | **Asset Audio** | ~400 file OGG/WAV organizzati per categoria |

---

## Architettura Audio

### Diagramma del Flusso End-to-End

```
Evento Gioco (sparo, passo, voicecom)
         ↓
    Server Trigger (SV_SOUND/SV_VOICECOM) 
         ↓
Messaggio Rete (ID suono + metadati)
         ↓
    Client Handler (clients2c.cpp:409)
         ↓
Audio Manager (audiomgr.playsound())
         ↓
  Buffer Loader (openal.cpp:sbuffer::load())
         ↓
OpenAL Source (source::play())
         ↓
  Mixer Audio (OpenAL context)
         ↓
   Dispositivo Audio (speakers/headphones)
```



**Spiegazione**: Il sistema utilizza un'architettura a eventi asincrona basata su OpenAL 1.1 con gestione prioritaria delle risorse audio. I suoni vengono caricati on-demand da filesystem locale in formato OGG Vorbis (streaming) o WAV (buffer statico).
Quindi in poche parole: il server decide quale suono deve partire mandando un messaggio al client con l'ID del suono, il client lo riconosce tramite l'ID e ricevendo il messaggio chiama playsound(). Successivamente il gestore audio carica il file .ogg o .wav locale e poi lo riproduce localmente con OpenAL creando una "fonte sonora 3D".


### Componenti Principali per File

#### 🎵 `sound.h` - Definisce tutti gli ID dei suoni e le categorie
esempio:
```cpp
// 103 suoni predefiniti del gioco (0-102)
enum {
    S_JUMP = 0, S_PISTOL = 8, S_FOOTSTEPS = 53,
    S_AFFIRMATIVE = 63, S_NULL = 102
};

// Categorie logiche per filtri
enum { SC_PAIN = 0, SC_WEAPON, SC_VOICECOM, SC_TEAM, SC_PUBLIC };

// Struttura configurazione sonora
struct soundcfgitem {
    const char *name, *desc;  // Nome file + descrizione
    uchar vol, loop, audibleradius;  // Volume, loop, raggio udibilità
    int flags;  // Categorie di appartenenza
};
```

#### 🎛️ `audiomanager.cpp` - Cuore del Sistema Audio
Contiene la classe audiomanager, che: 
	•	apre il dispositivo audio (OpenAL),
	•	gestisce la musica (oggstream),
	•	riproduce suoni (playsound()),
	•	aggiorna lo stato dell’audio.
```cpp
// Classe principale gestione audio
class audiomanager {
    bool nosound;           // Flag disabilitazione audio
    ALCdevice *device;      // Dispositivo OpenAL
    ALCcontext *context;    // Contesto audio OpenAL
    oggstream *gamemusic;   // Streaming musica di sottofondo

    // Funzioni principali
    void initsound();       // Inizializzazione OpenAL
    void playsound(int n);  // Riproduzione suono generico
    void music(char *name); // Gestione musica
    void updateaudio();     // Loop principale aggiornamento
};
```

#### 🔊 `openal.cpp` - Wrapper OpenAL Basso Livello
Gestisce la parte “bassa”: comunicazione diretta con la scheda audio.
```cpp
// Classe source: rappresenta una fonte sonora 3D
class source {
    ALuint id;              // ID OpenAL interno
    sourceowner *owner;     // Callback per eventi
    bool locked, valid;     // Stato risorsa
    int priority;           // Priorità (0-3)

    bool play();            // Avvia riproduzione
    bool buffer(ALuint buf); // Associa buffer audio
    bool position(vec &pos); // Posizione 3D
};

// Classe sbuffer: gestione buffer audio
class sbuffer {
    ALuint id;              // ID buffer OpenAL
    const char *name;       // Nome file

    bool load(bool trydl);  // Carica WAV/OGG da disco
    void unload();          // Libera risorse
};
```

#### 🎶 `oggstream.cpp` - Streaming Musicale
Serve solo per la musica di sottofondo, che viene riprodotta in streaming (non tutta caricata in RAM)
```cpp
// Classe per streaming OGG Vorbis
class oggstream : sourceowner {
    OggVorbis_File oggfile; // File OGG aperto
    vorbis_info *info;      // Info formato (sample rate, canali)
    ALuint bufferids[2];    // Buffer doppi per streaming

    bool open(const char *f);    // Apre file OGG
    bool playback(bool loop);    // Avvia riproduzione
    void fadein/fadeout();       // Effetti dissolvenza
};
```

---

## Flusso Server-Client

### Comunicazione Attuale (Solo Trigger/ID)

**Spiegazione Semplice**: Il server dice "suona il suono numero 5" e il client sa già quale file corrisponde a quel numero perché ha tutti i suoni salvati localmente.

**Situazione Attuale**:
1. **Server** → **Client**: Solo ID numerici + metadati minimi
2. **Client** deve avere tutti gli asset audio localmente
3. **Nessun** streaming di file audio dal server

#### Esempio Flusso Voicecom (Comunicazione Vocale)
```cpp
// Server: quando giocatore usa voicecom
void voicecom(char *sound, char *text) {
    // Trova ID del suono voicecom
    int s = audiomgr.findsound(soundpath, 0, gamesounds);

    // Invia a tutti i giocatori
    if(gamesound_ispublicvoicecom(s)) {
        addmsg(SV_VOICECOM, "ri", s);      // ID + ricevente
        toserver(text);                     // Testo chat
    } else {
        addmsg(SV_VOICECOMTEAM, "ri", s);   // Solo squadra
    }
}

// Client: riceve messaggio e riproduce
case SV_VOICECOM: {
    int t = getint(p);  // ID del suono voicecom
    audiomgr.playsound(t, SP_HIGH);  // Riproduci con priorità alta
}
```

#### Esempio Flusso Suono Normale
```cpp
// Server: evento gioco genera suono
void audiomanager::playsoundc(int n, physent *p, int priority) {
    if(p && p!=player1) playsound(n, p, priority);  // Suono posizionale
    else {
        addmsg(SV_SOUND, "i", n);  // Invia ID a tutti
        playsound(n, priority);   // Riproduci localmente
    }
}

// Client: riceve e processa
case SV_SOUND:
    audiomgr.playsound(getint(p), d);  // Riproduci suono ID ricevuto
```

### Limitazioni dell'Architettura Attuale

| Limitazione | Impatto | Soluzione Proposta |
|-------------|---------|-------------------|
| **Solo ID/trigger** | Client deve avere tutti i file | **Streaming dinamico** con chunking |
| **Nessuna autenticazione** | Facile manomissione client-side | **HMAC per chunk** di audio |
| **Asset statici** | Impossibile audio dinamico | **Cache runtime** per suoni server |
| **No watermarking** | Nessuna protezione anti-cheat | **Spread-spectrum watermarking** |

---

## Proposta di Modifica

### Estensione Protocollo per Streaming Audio

**Spiegazione Semplice**: Invece di dire "suona il suono 5", il server potrà inviare pezzetti del file ("chuck") audio stesso, come spedire un puzzle un pezzo alla volta, con una firma digitale per verificare che ogni pezzo sia autentico.

#### Nuovi Messaggi Protocollo

```cpp
// In protocol.h - aggiungere dopo SV_NUM
enum {
    SV_AUDIO_FILE_START = SV_NUM,   // Inizio trasmissione file
    SV_AUDIO_FILE_CHUNK,            // Chunk dati audio
    SV_AUDIO_FILE_END,              // Fine trasmissione
    SV_AUDIO_NEW_NUM                // Nuovo conteggio messaggi
};

// Struttura messaggio AUDIO_FILE_START
// file_id:4, seq:4, total_chunks:4, sample_rate:4, channels:1, format:1, checksum:32, signature:64
// Totale: 4+4+4+4+1+1+32+64 = 114 byte

// Struttura messaggio AUDIO_FILE_CHUNK
// file_id:4, chunk_seq:4, data_length:2, data:MAX_CHUNK_SIZE, hmac:32
// Massimo 4+4+2+4096+32 = 4138 byte
```

#### Modifiche al Server (`server.cpp`)
Nel codice server.cpp, vengono aggiunti niovi handler:
    •	Quando inizia a mandare un file, invia SV_AUDIO_FILE_START.
	•	Poi manda tanti SV_AUDIO_FILE_CHUNK.
	•	Alla fine, SV_AUDIO_FILE_END.
Il server controlla anche l'integrità (checksum e HMAC)
```cpp
// server.cpp - aggiungere handler per nuovi messaggi

case SV_AUDIO_FILE_START: {
    int file_id = getint(p);
    int seq = getint(p);
    int total_chunks = getint(p);
    int sample_rate = getint(p);
    int channels = getint(p);
    int format = getint(p);
    uchar checksum[32], signature[64];

    // Verifica firma HMAC del messaggio
    if(!verify_audio_signature(p.buf, p.length(), signature)) {
        // Firma non valida - ignora
        break;
    }

    // Inizializza struttura file audio
    audio_file_t *afile = new audio_file_t(file_id, total_chunks,
                                          sample_rate, channels, format);

    // Salva checksum per verifica finale
    memcpy(afile->expected_checksum, checksum, 32);
    audio_files[file_id] = afile;

    // Invia conferma al client
    sendf(sender, 1, "ri", SV_AUDIO_ACK, file_id);
    break;
}

case SV_AUDIO_FILE_CHUNK: {
    int file_id = getint(p);
    int chunk_seq = getint(p);
    int data_len = getint(p);

    // Trova file audio attivo
    audio_file_t *afile = find_audio_file(file_id);
    if(!afile || chunk_seq >= afile->total_chunks) break;

    // Verifica HMAC del chunk
    uchar chunk_hmac[32];
    memcpy(chunk_hmac, p.buf + p.length() - 32, 32);

    if(!verify_chunk_hmac(p.buf, p.length() - 32, chunk_hmac, server_key)) {
        // HMAC chunk non valido - richiedi ritrasmissione
        sendf(sender, 1, "rii", SV_AUDIO_RETRY, file_id, chunk_seq);
        break;
    }

    // Salva chunk nella cache
    memcpy(afile->chunks[chunk_seq], p.buf + 12, data_len);
    afile->received_chunks++;

    // Se completo, verifica checksum finale
    if(afile->received_chunks == afile->total_chunks) {
        uchar final_checksum[32];
        compute_file_checksum(afile, final_checksum);

        if(memcmp(final_checksum, afile->expected_checksum, 32) == 0) {
            // File valido - notifica client
            sendf(sender, 1, "ri", SV_AUDIO_COMPLETE, file_id);
        } else {
            // Checksum errato - richiedi ritrasmissione completa
            sendf(sender, 1, "ri", SV_AUDIO_INVALID, file_id);
        }
    }
    break;
}
```

#### Modifiche al Client (`clients2c.cpp`)
Il client riceve questi blocchi, li verifica, li ricompone e, se tutto è corretto:
	1.	Applica watermark/obfuscation (cioè “trucchetti” acustici);
	2.	Riproduce il suono.
Se qualcosa non va (es. firma errata), chiede di rispedire il pezzo.

```cpp
// clients2c.cpp - aggiungere handler per nuovi messaggi
case SV_AUDIO_FILE_START: {
    int file_id = getint(p);
    int seq = getint(p);
    int total_chunks = getint(p);
    int sample_rate = getint(p);
    int channels = getint(p);
    int format = getint(p);

    // Verifica firma messaggio con chiave pubblica server
    if(!verify_server_signature(p.buf, p.length())) {
        conoutf("Audio file signature verification failed");
        break;
    }

    // Crea struttura per ricevere file
    audio_file_t *afile = create_audio_file(file_id, total_chunks,
                                           sample_rate, channels, format);

    // Invia ACK al server
    addmsg(SV_AUDIO_ACK, "ri", file_id);
    break;
}

case SV_AUDIO_FILE_CHUNK: {
    int file_id = getint(p);
    int chunk_seq = getint(p);
    int data_len = getint(p);

    audio_file_t *afile = find_audio_file(file_id);
    if(!afile) break;

    // Verifica HMAC chunk
    uchar expected_hmac[32];
    compute_chunk_hmac(p.buf + 12, data_len, expected_hmac, client_key);

    uchar received_hmac[32];
    memcpy(received_hmac, p.buf + p.length() - 32, 32);

    if(memcmp(expected_hmac, received_hmac, 32) != 0) {
        // HMAC non valido - richiedi ritrasmissione
        addmsg(SV_AUDIO_RETRY, "rii", file_id, chunk_seq);
        break;
    }

    // Salva chunk e verifica completezza
    memcpy(afile->chunks[chunk_seq], p.buf + 12, data_len);
    afile->received_chunks++;

    if(afile->received_chunks == afile->total_chunks) {
        // File completo - applica watermarking e riproduci
        apply_audio_obfuscation(afile, client_id);
        play_audio_from_cache(afile);
    }
    break;
}
```

### Gestione Chiavi e Sicurezza
Ci sono due tipi di chiavi:
	•	HMAC (simmetrica): serve a verificare ogni blocco.
	•	Firma Ed25519 (asimmetrica): verifica che il messaggio venga davvero dal server.

#### Generazione Chiavi (`crypto.cpp`)
```cpp
// Genera chiave HMAC per sessione
void generate_session_keys() {
    // Chiave simmetrica per HMAC chunk
    RAND_bytes(server_hmac_key, 32);

    // Chiave asimmetrica per firme messaggi
    generate_ed25519_keypair(server_sign_key, server_verify_key);

    // Invia chiave pubblica al client durante handshake
    sendf(client, 1, "r32", SV_AUDIO_KEY_EXCHANGE, server_verify_key);
}
```

#### Verifica Integrità
```cpp
// Verifica firma messaggio server
bool verify_server_signature(uchar *data, int len) {
    ed25519_signature sig;
    memcpy(sig, data + len - 64, 64);

    uchar message[len - 64];
    memcpy(message, data, len - 64);

    return ed25519_sign_verify(sig, message, len - 64, server_verify_key);
}

// Calcola HMAC per chunk dati
void compute_chunk_hmac(uchar *chunk_data, int chunk_len,
                       uchar *hmac_out, uchar *key) {
    HMAC_CTX *ctx = HMAC_CTX_new();
    HMAC_Init_ex(ctx, key, 32, EVP_sha256(), NULL);
    HMAC_Update(ctx, chunk_data, chunk_len);
    HMAC_Final(ctx, hmac_out, NULL);
    HMAC_CTX_free(ctx);
}
```

### Fallback per Compatibilità

```cpp
// In server.cpp - verifica supporto client
bool client_supports_audio_streaming(int cn) {
    // Durante handshake, client invia capability bitmask
    clientinfo *ci = getclient(cn);
    return (ci->capabilities & CAP_AUDIO_STREAMING) != 0;
}

// Usa vecchio metodo se client non supporta
void send_sound_with_fallback(int sound_id, int cn) {
    if(client_supports_audio_streaming(cn)) {
        stream_audio_file(sound_id, cn);  // Nuovo metodo
    } else {
        sendf(cn, 1, "ri", SV_SOUND, sound_id);  // Vecchio metodo
    }
}
```

---

## Tecniche di Obfuscation
Abbiamo tre livelli di complessità

### 1. Pitch Shift Parametrico (Semplice)

**Spiegazione**: Cambia leggermente l'altezza del suono in base al tuo ID giocatore, vediamola come accordare uno strumento musicale in modo diverso per ogni musicista. 
Cambia leggermente l’altezza del suono per ogni giocatore.
→ Ogni client sente un suono identico ma con piccolissime variazioni impercettibili.
Serve per impedire che un cheat riconosca il suono perfettamente.

**Implementazione**:
```cpp
// In client - prima del playback
void apply_pitch_obfuscation(audio_file_t *afile, int client_id) {
    // Calcola shift basato su hash client_id
    float shift_factor = 1.0f + (hash_client_id(client_id) % 100) / 10000.0f;

    // Applica pitch shift a tutto il buffer
    for(int i = 0; i < afile->sample_count; i++) {
        afile->samples[i] *= shift_factor;
    }
}

// Hash deterministico da client_id
uint32_t hash_client_id(int client_id) {
    uint32_t hash = 2166136261u;
    hash ^= client_id;
    hash *= 16777619;
    return hash;
}
```

### 2. EQ/Filter Perturbation (Medio)

**Spiegazione**: Modifica le frequenze del suono come un equalizzatore audio, amplificando o attenuando bande specifiche basate sul tuo profilo giocatore.
Applica un filtro passa-basso o equalizzazione diversa per ogni client.
→ Cambia la risposta in frequenza (un po’ più ovattato o più brillante).

**Implementazione**:
```cpp
// Filtro passa-basso parametrico
void apply_eq_obfuscation(audio_file_t *afile, int client_id) {
    // Calcola cutoff frequency da client_id
    float cutoff_hz = 2000.0f + (client_id % 1000);

    // Coefficienti filtro IIR
    float a1 = exp(-2.0f * M_PI * cutoff_hz / afile->sample_rate);
    float b0 = 1.0f - a1;

    // Applica filtro a buffer
    float prev_input = 0.0f, prev_output = 0.0f;

    for(int i = 0; i < afile->sample_count; i++) {
        float output = b0 * afile->samples[i] + a1 * prev_output;
        prev_output = output;
        afile->samples[i] = output;
    }
}
```

### 3. Spread-Spectrum Watermarking (Avanzato)

**Spiegazione**: Nasconde informazioni segrete nel suono come un messaggio invisibile, spargendo dati su tutto lo spettro audio in modo che sia impossibile da rimuovere senza degradare la qualità.
Nasconde informazioni (es. ID del giocatore) dentro al suono, modulando micro-variazioni nello spettro.
→ Invisibile all’orecchio umano, ma rilevabile analizzando lo spettro FFT.


**Implementazione**:
```cpp
// Embedding watermark spread-spectrum
void embed_spread_spectrum_watermark(float *samples, int sample_count,
                                   int client_id, float sample_rate) {
    // Genera pseudorandom sequence da client_id
    srand(client_id);
    int watermark_bits = 32;  // 32 bit di identificazione

    // Per ogni bit del watermark
    for(int bit = 0; bit < watermark_bits; bit++) {
        int chip_seq = rand() % (sample_count / watermark_bits);
        float chip_value = (rand() % 2) ? 1.0f : -1.0f;

        // Modula sequenza con bit watermark
        float bit_value = (client_id & (1 << bit)) ? 1.0f : -1.0f;

        // Spread su finestra temporale
        int start_sample = bit * (sample_count / watermark_bits);
        int end_sample = (bit + 1) * (sample_count / watermark_bits);

        for(int i = start_sample; i < end_sample; i++) {
            samples[i] += 0.001f * chip_value * bit_value;  // Guadagno molto basso
        }
    }
}
```

### Posizione nel Pipeline Audio
Tutte queste modifiche si applicano dopo il decoding del suono ma prima della riproduzione (fase PCM)

```
File Audio → Decoding → Watermarking → Mixing → Playback
                              ↑
                   Qui applichiamo le trasformazioni
```

**Motivazione Tecnica**: L'obfuscation deve avvenire **dopo** il decoding ma **prima** del mixing per:
1. **Efficienza**: Lavoriamo su PCM raw invece che su dati compressi
2. **Universalità**: Funziona con qualsiasi formato (WAV/OGG)
3. **Controllo**: Possiamo applicare trasformazioni parametriche
4. **Sicurezza**: Più difficile da reverse-engineer rispetto al formato compresso

---

## Sicurezza e Anti-Tamper
Questa parte serve per evitare che i cheat manipolino il sistema audio.

### Gestione Chiavi HMAC - Rotazione chiavi
Le chiavi HMAC vengono rigenerate ogni ora per limitare il rischio di compromissione 

```cpp
// Chiavi per sessione (ruotate ogni ora)
struct audio_security_t {
    uchar server_hmac_key[32];      // Chiave simmetrica HMAC
    uchar client_verify_key[32];    // Chiave pubblica client
    time_t key_rotation_time;       // Timestamp rotazione
};

// Rotazione chiavi ogni ora
void rotate_audio_keys() {
    if(time(NULL) - audio_security.key_rotation_time > 3600) {
        RAND_bytes(audio_security.server_hmac_key, 32);

        // Invia nuova chiave pubblica ai client connessi
        sendf(-1, 1, "r32", SV_AUDIO_KEY_ROTATION, audio_security.client_verify_key);

        audio_security.key_rotation_time = time(NULL);
    }
}
```

### Controlli Anti-Hooking

#### 1. Verifica Integrità Processi Audio
Controllare se altri processi (come Audacity o OBS) leggono il dispositivo audio -> possibile registrazione
```cpp
// Controlla se processi sospetti accedono al loopback audio
void check_audio_integrity() {
    // Lista processi che accedono al dispositivo audio
    system("lsof /dev/audio /dev/snd/* 2>/dev/null | grep -v 'pulseaudio\|alsa' > /tmp/audio_processes");

    FILE *fp = fopen("/tmp/audio_processes", "r");
    if(fp) {
        char line[256];
        while(fgets(line, sizeof(line), fp)) {
            // Flagga processi sospetti (recording software, etc.)
            if(strstr(line, "audacity") || strstr(line, "recorder")) {
                log_suspicious_audio_activity("Recording software detected");
            }
        }
        fclose(fp);
    }
}
```

#### 2. Timing Attack Detection
Controllare se ci sono anomalie di tempo (latenze irregolari -> possibile interferenze)
```cpp
// Rileva se il client modifica i timing audio
void detect_timing_anomalies() {
    static uint64_t last_audio_update = 0;
    uint64_t current_time = get_microseconds();

    // Se il client salta aggiornamenti audio
    if(current_time - last_audio_update > 20000) {  // 20ms threshold
        log_timing_anomaly("Audio update skipped - possible hooking");
    }

    last_audio_update = current_time;
}
```

#### 3. Checksum Eseguibile
Controllare se l'eseguibile del client è stato modificato  (checksum differente)
```cpp
// Verifica integrità eseguibile client
void verify_client_integrity() {
    // Calcola hash dell'eseguibile in memoria
    uchar current_hash[32];
    compute_executable_hash(current_hash);

    // Confronta con hash noto (da autenticazione iniziale)
    if(memcmp(current_hash, known_client_hash, 32) != 0) {
        log_integrity_violation("Client executable modified");
        disconnect_client(reason_integrity_check_failed);
    }
}
```

### Logging e Telemetria
Tutti gli eventi sospsetti vengono loggati in un file audio_security.log e inviati al server.

```cpp
// Struttura per telemetria anti-cheat
struct audio_telemetry_t {
    uint32_t client_id;
    uint64_t timestamp;
    char event_type[32];    // "audio_hooked", "timing_anomaly", etc.
    char details[128];      // Dettagli evento
};

// Log eventi sospetti
void log_audio_security_event(const char *event_type, const char *details) {
    audio_telemetry_t telemetry = {
        .client_id = current_client_id,
        .timestamp = get_timestamp(),
        .event_type = event_type,
        .details = details
    };

    // Salva su file per analisi offline
    FILE *fp = fopen("audio_security.log", "a");
    fprintf(fp, "%u,%llu,%s,%s\n", telemetry.client_id, telemetry.timestamp,
            telemetry.event_type, telemetry.details);
    fclose(fp);

    // Invia al server per analisi real-time
    sendf(server, 1, "r32", SV_AUDIO_TELEMETRY, &telemetry);
}
```

---

## Piano di Test
Ora vediamo come verificare che tutto funzioni:

### Casi di Test Principali

#### 1. Test HMAC e Integrità
	•	File corrotti → il client deve rifiutarli.
	•	Chunk mancanti → deve chiedere la ritrasmissione.
```bash
# Test 1: HMAC difettoso
./test_audio_hmac_invalid.sh

# Test 2: Chunk mancante
./test_audio_missing_chunk.sh

# Test 3: Latenza simulata
./test_audio_latency_100ms.sh

# Test 4: Dispositivi diversi
./test_audio_device_usb_headphones.sh
./test_audio_device_bluetooth.sh
./test_audio_device_builtin_speakers.sh
```

#### 2. Test Obfuscation Effectiveness
    •	Misura se le modifiche audio sono percepibili.
	•	Controlla se il watermark si può rilevare in una registrazione.
```bash
# Misura impatto percettibile watermarking
./measure_obfuscation_perception.py --technique pitch_shift --client_id 12345

# Test riconoscimento watermark da registrazione esterna
./test_watermark_detection.py --audio_file recorded_gameplay.wav --expected_client_id 12345
```

#### 3. Test Sicurezza
    •	Simula hooking o timing attack.
	•	Vedi se il sistema li rileva correttamente.
```bash
# Simula attacco timing
./simulate_timing_attack.py --delay_ms 50 --duration_sec 10

# Test detection hooking audio
./test_audio_hooking_detection.py --hook_alsa --record_output
```

### Procedure di Test Dettagliate

#### Test Dispositivi Audio Diversi

**Setup Test**:
1. Collega cuffie USB al PC desktop
2. Collega cuffie Bluetooth al telefono
3. Avvia AssaultCube con audio streaming abilitato
4. Esegui scenario di gioco standard (deathmatch)

**Metriche da Rilevare**:
- Latenza audio percepita (ms)
- Qualità audio soggettiva (1-5 scale)
- Detection watermarking su registrazione esterna
- CPU usage incremento dovuto a obfuscation

**Dispositivi da Testare**:
- [ ] PC Desktop + altoparlanti integrati
- [ ] PC Desktop + cuffie USB
- [ ] PC Desktop + cuffie Bluetooth
- [ ] Laptop + altoparlanti integrati
- [ ] Smartphone + altoparlanti
- [ ] Smartphone + cuffie wired

#### Test VoIP Integration

**Scenario**: Gioca mentre Discord/Steam Voice è attivo

**Setup**:
1. Avvia Discord e unisciti a chiamata vocale
2. Avvia AssaultCube con audio obfuscato
3. Gioca partita normale mentre parli su Discord

**Metriche**:
- Comprensibilità voce su Discord durante gioco
- Interferenza tra audio gioco e voce VoIP
- Detection watermarking nella registrazione Discord

---

## Glossario

| Termine | Definizione Semplice | Definizione Tecnica |
|---------|---------------------|---------------------|
| **Sampling Rate** | Numero di "istantanee" audio al secondo | Frequenza di campionamento in Hz (es. 44100 Hz = 44100 campioni/sec) |
| **FFT** | Trasforma audio da tempo a frequenza | Fast Fourier Transform: algoritmo per analisi spettro |
| **HMAC** | Firma digitale per verificare autenticità | Hash-based Message Authentication Code usando SHA-256 |
| **Chunking** | Dividere file in pezzi più piccoli | Segmentazione dati per trasmissione affidabile |
| **Watermarking** | Nascondere informazioni segrete nell'audio | Tecnica steganografica per embedding dati invisibili |
| **Spread-Spectrum** | Distribuire segnale su larga banda | Tecnica di modulazione per watermarking robusto |
| **OpenAL** | Libreria per audio 3D | Open Audio Library per posizionamento spaziale suoni |
| **OGG Vorbis** | Formato audio compresso | Codec audio lossy con alta qualità e compressione |
| **Loopback** | Dispositivo audio virtuale | Interfaccia per catturare audio del sistema |
| **Anti-Tamper** | Protezione contro modifiche | Tecniche per rilevare manomissioni del software |

---

## Riferimenti

### Per Principianti (Audio Digitale)
- **"The Audio Programming Book"** di Boulanger e Lazzarini - Introduzione completa all'audio digitale
- **Khan Academy: Digital Audio** - Lezioni gratuite sui fondamenti del suono digitale
- **"Computer Music" di Dodge e Jerse** - Classico textbook su sintesi e processing audio

### Per Sviluppatori (OpenAL e Audio 3D)
- **OpenAL 1.1 Specification** - Documentazione ufficiale API
- **"OpenAL Programming Guide"** di Astro73 - Tutorial pratico OpenAL
- **Creative Labs OpenAL SDK** - Esempi e documentazione

### Anti-Cheat e Sicurezza
- **"Game Hacking" di Nick Cano** - Tecniche attacco/difesa nei giochi
- **"Reversing: Secrets of Reverse Engineering"** - Comprensione disassembly
- **OWASP Audio Security Guidelines** - Best practice sicurezza audio

### Watermarking e Steganografia
- **"Information Hiding Techniques" di Stefan Katzenbeisser** - Teoria watermarking
- **"Digital Watermarking" di Cox, Miller, Bloom** - Algoritmi pratici
- **IEEE Transactions on Information Forensics and Security** - Paper accademici watermarking

---

## 📝 Nota per la Tesi

Questo materiale è ideale per la  **sezione sperimentale** della mia tesi. Possiamo strutturarlo come:

1. **Setup Sperimentale** (Capitolo 4)
   - Descrizione implementazione modificata AssaultCube
   - Configurazione ambiente test (hardware/software)
   - Metriche di valutazione definite

2. **Risultati** (Capitolo 5)
   - Tabelle performance (latenza, CPU usage, qualità audio)
   - Grafici detection rate watermarking su diversi dispositivi
   - Analisi sicurezza (tentativi attacco rilevati)

3. **Discussione** (Capitolo 6)
   - Confronto tecniche obfuscation (efficacia vs impatto UX)
   - Limitazioni approccio e direzioni future
   - Implicazioni etiche (privacy giocatori)

**Metriche Quantitative da Riportare**:
- Latenza media audio (ms) per dispositivo
- CPU overhead dovuto a watermarking (%)
- Detection accuracy watermarking (%)
- False positive rate controlli sicurezza (%)

