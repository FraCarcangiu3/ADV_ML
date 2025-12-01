# THESIS_ANTICHEAT

**Development and Analysis of an Audio Obfuscation System in AssaultCube to Counter Machine Learning-Based Cheating Algorithms**

---

**Author:** Francesco Carcangiu  
**Degree Program:** Computer Engineering  
**University of Cagliari**
Project carried out at the Cyber Security Laboratory of the Polytechnic University of Madrid (UPM)  
**Academic Year:** 2025-2026

---

## Abstract

I developed and validated an experimental audio obfuscation system for the open-source video game AssaultCube, with the goal of countering cheating algorithms based on automated audio recognition through machine learning. The project fits into the context of security in multiplayer video games, where sophisticated cheats exploit ML to identify relevant audio events (enemy footsteps, weapon reloading, shot direction) and provide illicit competitive advantages.

The system implements deterministic audio transformations (pitch shift, EQ tilt, HP/LP filters, noise injection) applied at runtime through minimally invasive hooks in AssaultCube's OpenAL architecture. I manually calibrated the obfuscation parameters through in-game subjective tests, identifying perceptibility thresholds for different types of sounds (weapon/usp: pitch ±200-500 cents, white noise 35-45 dB SNR, EQ ±2-6 dB).

The main contribution is the demonstration of the **R₀+A vs R₁+A** model: an attacker who trains an ML model on audio with transformations R₀ (time t₀) suffers accuracy degradation when the game uses different transformations R₁ (time t₁), provided the transformations are imperceptible to the human user. I organized the entire workflow (variant generation, MFCC feature extraction, subjective tests) in the `ADV_ML/` folder, ready for final ML validation post-randomization.

---

## 1. Introduction

### 1.1 Context and Motivation

When I started this project, I was interested in exploring unconventional cybersecurity techniques applied to video games. AssaultCube, an open-source first-person shooter based on the Cube Engine, offered me the opportunity to work on a real and complex system, studying its C++ source code and understanding how audio management works in a 3D positional game.

I discovered that AssaultCube's audio architecture follows a pattern common to many games: the server sends numeric identifiers (IDs) of sounds to play to clients, while the actual audio files (.ogg, .wav) are stored locally on the client in `AC/packages/audio/`. This separation between server trigger and client resolution of audio assets creates a vulnerability: since all players have the same identical audio files, it is relatively simple for a cheat to train machine learning models to recognize specific audio events.

The problem of "audio cheats" is not purely theoretical. During my preliminary research, I found discussions on modding and hacking forums describing systems capable of automatically identifying enemy footsteps, weapon reloading, or other tactically relevant actions, providing the dishonest player with an "audio radar" or "audio wallhack". This type of cheat is particularly insidious because:

1. It does not require client modifications (it can run as an external process)
2. It is difficult to detect through traditional anti-cheat controls
3. It exploits legitimate information (the audio everyone hears)
4. It can be automated with pattern matching or ML algorithms

I therefore thought: what if each client received slightly different versions of the same sounds? What if the audio were "obfuscated" in a way imperceptible to the human ear but sufficient to confuse recognition algorithms trained on "standard" assets? This question became the foundation of my thesis work.

### 1.2 Project Objectives

The objectives I set at the beginning of the project were:

1. **Deeply understand how audio works in a real video game**: I wanted to go beyond book theory and see with my own eyes how OpenAL, Vorbis codec, and mixing pipelines integrate into a complex project.

2. **Implement a runtime obfuscation system**: Create a C++ framework that applies parametric audio transformations (pitch, noise, EQ, filters) transparently to gameplay.

3. **Calibrate perceptibility thresholds**: Empirically determine transformation ranges that are imperceptible or barely perceptible to the human user, but sufficient to degrade ML algorithms.

4. **Validate the R₀+A vs R₁+A attack model**: Demonstrate that a model trained on audio with transformations R₀ loses accuracy when tested on audio with different transformations R₁.

5. **Learn to do technical research rigorously**: This project was an opportunity for me to develop skills in systematic analysis, quantitative measurement, and scientific documentation.

---

## 2. Threat Model: R₀+A vs R₁+A

### 2.1 Attack Scenario

The threat model I studied is based on this scenario:

**Time t₀ (Cheat Training Phase)**:
1. The game produces clean audio **A** (e.g., pistol shot)
2. We add a controlled transformation **R₀** (e.g., pitch shift +100 cents, white noise 40 dB)
3. The dishonest player **records** audio from the game → their examples are of type **R₀ + A**
4. The attacker **trains** an ML model (e.g., CNN on spectrograms, or SVM on MFCC) to recognize tactically useful information:
   - Type of weapon fired (pistol vs shotgun vs sniper)
   - Approximate shot direction (left/right/center)
   - Estimated distance (near/far)
   - Specific events (reload, footsteps, voice command)

**Time t₁ (Cheat Usage Phase)**:
5. We **change** the transformation → the game now produces **R₁ + A** (e.g., pitch shift +300 cents, pink noise 35 dB, EQ tilt +3 dB)
6. The cheat's model, trained on R₀+A, receives R₁+A as input
7. **Hypothesis**: If R₁ is sufficiently different from R₀, the model's accuracy degrades significantly

### 2. Fundamental Constraint: Imperceptibility

The entire system only works if **R is imperceptible or barely perceptible** to the human user. If audio transformations are too evident, they degrade the gaming experience and are not acceptable.

**Perceptibility criterion**:
- **min_perc**: First transformation where I start to perceive during subjective tests
- **max_ok**: Last transformation I consider acceptable for competitive gameplay

The range **[min_perc, max_ok]** defines the usable transformation space. For example, for `weapon/usp`:
- Pitch shift: min_perc = 100 cents (UP), max_ok = 500 cents → range [100, 500]
- White noise: min_perc = 45 dB, max_ok = 35 dB → range [35, 45] dB SNR

### 2.3 System Objective

The obfuscation system must:

1. **At game startup** (or per session/map), choose random **R₁** parameters within calibrated ranges
2. **During gameplay**, apply R₁ to all audio assets transparently
3. **Periodically** (e.g., every week, every patch), change R₁ parameters to invalidate ML models trained on R₀

**Success metric**: ML accuracy degradation ≥20-30% when testing model trained on R₀ with R₁ audio.

### 2.4 Why This Works

The reason this technique is effective against ML lies in spectral features:

**Commonly used features** (MFCC, mel-spectrograms, ZCR, spectral centroid):
- **Depend on frequency distribution** → pitch shift directly alters them
- **Depend on signal-to-noise ratio** → noise injection degrades them
- **Depend on spectral balance** → EQ tilt distorts them
- **Depend on bandwidth** → HP/LP filters limit them

**Data augmentation** (attacker's defense):
- The attacker could train on "augmented" datasets with random pitch shift
- **Countermeasure**: We use **multiple combinations** (pitch + EQ + noise + filters), making the augmentation space too vast

**Non-uniform distribution** (as a final step I thought of an advanced defense by randomizing noises):
- Instead of `uniform(min, max)`, use Beta/Normal distributions concentrated near "sweet spot" values
- Make the choice of R₁ unpredictable

---

## 3. Technical Background

### 3.1 Digital Audio: Fundamentals

Before analyzing AssaultCube, I consolidated my basic knowledge of digital audio:

**PCM (Pulse-Code Modulation)** is the standard representation of digital audio: a sound wave is sampled at regular intervals (sample rate, e.g., 44100 Hz = 44100 samples per second), and each sample is quantized into a digital value (e.g., 16-bit signed integer, range -32768..32767). The PCM format is "lossless" (without loss), but takes up a lot of space, which is why games use compressed codecs like OGG Vorbis.

**Pitch shift** is the alteration of the fundamental frequency of a sound without changing its duration. This is different from simple "speed up" or "slow down": if I speed up a sound by 10%, it becomes higher-pitched and shorter. A true pitch shift maintains the original duration. To do this, sophisticated algorithms like WSOLA (Waveform Similarity Overlap-Add) are needed, implemented by the SoundTouch library I used.

**Psychoacoustic perception**: Not all acoustic differences are perceptible to the human ear. The pitch discrimination threshold depends on:
- **Sound duration**: sounds <100ms have almost imperceptible pitch; sounds >1s allow fine discrimination
- **Spectral complexity**: pure tones (sinusoids) are more sensitive to shift; noises/percussive effects less
- **Context**: in a noisy environment (like a video game), the perceptibility threshold increases

This psychoacoustic notion was fundamental for interpreting my results: I discovered that musical literature (which indicates ±5-20 cents as imperceptible) **does not apply directly to game sounds**, which are often short, percussive, and listened to in a competitive context.

### 3.2 OpenAL and 3D Audio in Games

AssaultCube uses **OpenAL** (Open Audio Library), a cross-platform API for positional 3D audio. OpenAL organizes audio into:

- **Listener**: the "position" of the listener (typically the player's camera)
- **Sources**: audio sources positioned in 3D space (e.g., an enemy firing)
- **Buffers**: PCM audio data loaded into memory (the audio assets)

The flow is: load audio file → decode to PCM → populate OpenAL buffer (`alBufferData`) → associate buffer with source → play (`alSourcePlay`). OpenAL automatically handles distance attenuation, Doppler effect, stereo/surround panning based on relative position.

A difficulty I encountered on macOS: Apple's OpenAL framework has been **deprecated** since 2019 and no longer works on Apple Silicon (M1/M2). I had to replace it with OpenAL-soft, an open-source alternative implementation — this became one of the most challenging technical problems I solved during the project.

### 3.3 SoundTouch: High-Quality Pitch Shifting

I chose **SoundTouch** (https://www.surina.net/soundtouch/) as the library for pitch shifting. SoundTouch is open-source (LGPL), mature (developed since 2001), and used in professional projects (Audacity, VLC). It offers simple APIs:

```cpp
SoundTouch st;
st.setSampleRate(44100);
st.setChannels(2); // stereo
st.setPitchSemiTones(0.5); // +0.5 semitones = +50 cents
st.putSamples(input_buffer, num_frames);
st.receiveSamples(output_buffer, buffer_size);
```

SoundTouch uses WSOLA algorithms that analyze the waveform, find similar segments, and "stretch" or "compress" them in the time domain to change pitch while maintaining duration. Quality is very high for moderate shifts (±1-2 semitones), with minimal artifacts.

---

## 4. Analysis of AssaultCube's Audio Architecture

### 4.1 Methodological Approach

I approached the analysis of AssaultCube's source code systematically:

1. **Recursive pattern search**: Used `grep` to search for key terms (`sound`, `audio`, `playsound`, `alBufferData`, `.ogg`, `.wav`) throughout the `AC/source/src/` codebase.
2. **Key file identification**: From grep results, I identified ~10 main files involved in audio management.
3. **Code reading and annotation**: I manually read each key file, annotating role, main functions, data structures.
4. **Mental diagram construction**: I drew the end-to-end flow from server trigger to audio playback.

### 4.2 Key Files Identified

#### `AC/source/src/openal.cpp`
**Role**: Low-level wrapper for OpenAL; manages `source` objects (audio channels) and `sbuffer` (data buffers).

**Key functions**:
- `sbuffer::load(char *name)`: Loads audio file (tries .ogg, .wav extensions), decodes, populates OpenAL buffer. **This is the critical point I chose for the hook**.
- `source::play()`: Starts playback on an OpenAL source.

**Relevant code** (extract lines 280-320):
```cpp
bool sbuffer::load(char *name)
{
    // Try to load .ogg
    OggVorbis_File oggfile;
    if(ov_open(f->stream(), &oggfile, NULL, 0) == 0)
    {
        vorbis_info *info = ov_info(&oggfile, -1);
        vector<char> buf;
        
        // Decode entire OGG file to PCM
        int bitstream;
        size_t bytes;
        do {
            char buffer[BUFSIZE];
            bytes = ov_read(&oggfile, buffer, BUFSIZE, ...);
            loopi(bytes) buf.add(buffer[i]);
        } while(bytes > 0);

        // >>> HOOK POINT: here buf contains PCM int16, before alBufferData <<<
        
        // Load PCM into OpenAL buffer
        alBufferData(id, 
                     info->channels == 2 ? AL_FORMAT_STEREO16 : AL_FORMAT_MONO16,
                     buf.getbuf(), 
                     buf.length(), 
                     info->rate);
        ov_clear(&oggfile);
    }
}
```

**Fundamental insight**: After `ov_read` and before `alBufferData`, audio data is available in raw PCM format. This is the perfect moment to apply transformations: I have complete metadata (sample rate, channels), direct access to samples, and no interference with global data structures.

### 4.3 Audio Flow Diagram

```
[SERVER]                                           [CLIENT]
   |                                                  |
   | SV_SOUND(id=S_PISTOL, pos=(x,y,z))              |
   +------------------------------------------------->|
                                                      | audiomanager::playsound(S_PISTOL, pos)
                                                      |   ↓
                                                      | Resolve: soundcfg[S_PISTOL] → "weapon/pistol"
                                                      |   ↓
                                                      | sbuffer::load("weapon/pistol")
                                                      |   ↓
                                                      | Load AC/packages/audio/weapon/pistol.ogg
                                                      |   ↓
                                                      | Decode OGG → PCM (int16, 22050 Hz, mono)
                                                      |   ↓
                                                      | [>>> OBFUSCATION HOOK HERE <<<]
                                                      |   ↓
                                                      | alBufferData(id, AL_FORMAT_MONO16, pcm, len, rate)
                                                      |   ↓
                                                      | alSourcePlay(source_id)
                                                      |   ↓
                                                   [SPEAKER]
```

---

## 5. Detailed Implementation of the Runtime Obfuscation System

In this chapter, we will see in detail the complete implementation of the C++ framework I developed to apply audio transformations in real-time to the AssaultCube client. 
The documentation includes **all relevant code** with in-depth explanations of the implemented DSP algorithms.

### 5.1 General Framework Architecture

I designed a modular system called `audio_runtime_obf` (Audio Runtime Obfuscation) consisting of four main elements:

1. **Header file** (`audio_runtime_obf.h`): Defines data structures, public API, and interface documentation
2. **Implementation file** (`audio_runtime_obf.cpp`): Contains the implementation of all DSP algorithms, CSV parser, and processing logic
3. **Hook points**: Hook points in `openal.cpp` and `main.cpp` to integrate the framework into the existing audio flow
4. **Configuration file**: CSV file (`audio_obf_config.csv`) with parameters specific to each sound

#### 5.1.1 Main Data Structures

I defined two fundamental data structures in `audio_runtime_obf.h`:

**Struct `AudioProfile` — Audio Profile for Single Sound**:

```cpp
struct AudioProfile {
    std::string file_name;        // File name (e.g. "weapon/usp")
    
    // Pitch shift range (Step 2: midpoint; Step 3: random in [min,max])
    int min_pitch_cents = 0;      // Minimum pitch shift in cents
    int max_pitch_cents = 0;      // Maximum pitch shift in cents
    
    // Noise injection
    std::string noise_type;       // "none", "white", "pink", "tone"
    float noise_snr_db = 0.f;     // Target SNR in dB
    
    // Tone frequency (if noise_type = "tone")
    int min_freq = 0;             // Minimum frequency in Hz
    int max_freq = 0;             // Maximum frequency in Hz
    
    // Multi-perturbation (Step 2 extended)
    float eq_tilt_db = 0.f;       // EQ tilt shelving in dB
    int hp_hz = 0;                // High-pass filter frequency (0 = off)
    int lp_hz = 0;                // Low-pass filter frequency (0 = off)
};
```

This structure contains all transformation parameters for a single audio file. Fields are organized into logical groups:

- **Identification**: `file_name` corresponds to the logical name of the sound (e.g., "weapon/usp", without .ogg extension)
- **Pitch shift**: Range defined by `min_pitch_cents` and `max_pitch_cents`. 
                   In Step 2 I use deterministic midpoint; in Step 3 it will be randomized.
- **Noise/Tone**: `noise_type` selects the type of additive perturbation, with SNR and frequency parameters
- **EQ and filters**: `eq_tilt_db`, `hp_hz`, `lp_hz` control equalization and spectral filtering

**Struct `ARO_Profile` — Global Configuration** (deprecated in Step 2, maintained for compatibility):

```cpp
struct ARO_Profile {
    bool enabled = false;         // global obfuscation ON/OFF
    bool use_pitch = false;       // enable pitch shifting
    int  pitch_cents = 0;         // +/- cents
    bool use_noise = false;       // enable noise addition
    float noise_snr_db = 0.f;     // target SNR in decibel
    bool use_tone = false;        // enable tone addition
    float tone_freq_hz = 0.f;     // tone frequency in Hz
    float tone_level_db = 0.f;    // tone level in dB
};
```

In Step 2, this structure is used mainly for the global `enabled` flag. Sound-specific configurations are managed by the `g_audio_profiles` map (see §5.2.3).

### 5.2 CSV Configuration File and Parser

#### 5.2.1 Extended CSV Schema

The file `AC/audio_obf_config.csv` defines transformation parameters for each sound. Complete schema:

```csv
file_name,min_pitch_cents,max_pitch_cents,noise_type,noise_snr_db,min_freq,max_freq,eq_tilt_db,hp_hz,lp_hz
# Comments start with #
# weapon/usp - USP Pistol (manually calibrated in Step 2)
weapon/usp,-200,500,white,35,,,2,150,10000
```

**Column Description**:

1. **`file_name`** (required): Logical name of the audio file **without extension** .ogg/.wav. Must exactly match the name passed to `sbuffer::load()` in `openal.cpp`. Example: `weapon/usp` (NOT `weapon/usp.ogg`)

2. **`min_pitch_cents`**, **`max_pitch_cents`**: Pitch shift range in cents (100 cents = 1 semitone = 6% freq variation). Negative values = lower pitch, positive = higher. Example: `-200,500` means "from 2 semitones below to 5 semitones above"

3. **`noise_type`**: Type of additive perturbation. Valid values:
   - `none`: No noise
   - `white`: White noise (uniform Gaussian noise, flat spectrum)
   - `pink`: Pink noise (1/f spectrum, more energy at low frequencies)
   - `tone`: Pure sinusoidal tone at specific frequency

4. **`noise_snr_db`**: Target Signal-to-Noise Ratio in decibels. Controls the intensity of noise/tone relative to the original signal. Higher values = weaker noise (less perceptible). Example: `35` dB = barely perceptible noise

5. **`min_freq`**, **`max_freq`**: Frequency range (in Hz) for tone injection (used only if `noise_type=tone`). Example: `9000,11000` = tone between 9 and 11 kHz (borderline ultrasonic range)

6. **`eq_tilt_db`**: EQ tilt (shelving) in dB. Positive = boost high frequencies ("brighten"), negative = boost low frequencies ("darken"). Example: `+2` dB = slightly brighter sound

7. **`hp_hz`**: High-pass filter cutoff frequency in Hz. Attenuates frequencies **below** this value. `0` = filter disabled. Example: `150` Hz = cuts low "rumble"

8. **`lp_hz`**: Low-pass filter cutoff frequency in Hz. Attenuates frequencies **above** this value. `0` = filter disabled. Example: `10000` Hz = cuts high "hiss"

**Empty Field Handling**: Empty fields are interpreted as `0` (effect disabled). Example: `weapon/usp,-200,500,none,,,,0,0,0` disables all effects except pitch

**Step 2 Notes** (Determinism): In this phase, ranges are resolved with **deterministic midpoint**:
- Pitch: `(min + max) / 2` → Example: `(-200+500)/2 = +150` cents
- Tone freq: `(min_freq + max_freq) / 2` → Example: `(9000+11000)/2 = 10000` Hz
- Single values (`noise_snr_db`, `eq_tilt_db`, `hp_hz`, `lp_hz`): used directly

**Step 3** (Randomization — Future): Ranges will be sampled with `std::uniform_int_distribution<>(min, max)` for each loaded sound.

#### 5.2.2 CSV Parser Implementation

I implemented a robust CSV parser in `audio_runtime_obf.cpp` that handles:
- Comments (lines starting with `#`)
- Empty fields (interpreted as `0`)
- Automatic whitespace trimming
- Quote handling (if needed in the future)

**Complete parser code** (`audio_runtime_obf.cpp`, lines 445-534):

```cpp
/**
 * Trim whitespace from string.
 */
static std::string trim(const std::string& str)
{
    size_t first = str.find_first_not_of(" \t\r\n");
    if (first == std::string::npos) return "";
    size_t last = str.find_last_not_of(" \t\r\n");
    return str.substr(first, last - first + 1);
}

/**
 * Split CSV line respecting empty fields.
 * Supports quotes for fields with internal commas (not used for now).
 */
static std::vector<std::string> split_csv_line(const std::string& line)
{
    std::vector<std::string> fields;
    std::string field;
    bool in_quotes = false;
    
    for (char c : line) {
        if (c == '"') {
            in_quotes = !in_quotes;  // Toggle quote state
        } else if (c == ',' && !in_quotes) {
            fields.push_back(trim(field));  // End of field
            field.clear();
        } else {
            field += c;  // Accumulate character
        }
    }
    fields.push_back(trim(field));  // Last field
    return fields;
}

/**
 * Load audio profiles from CSV file.
 * Populates the global g_audio_profiles map.
 * 
 * @param path Path to CSV file (relative to AC/ root)
 * @return true if loading successful, false if file not found
 */
bool aro_load_profiles_from_csv(const std::string& path)
{
    std::ifstream file(path);
    if (!file.is_open()) {
        std::printf("[AUDIO_OBF] config file %s not found — continuing with empty profiles\n", 
                    path.c_str());
        return false;
    }
    
    g_audio_profiles.clear();  // Reset existing profiles
    std::string line;
    int line_num = 0;
    int profiles_loaded = 0;
    
    while (std::getline(file, line)) {
        line_num++;
        line = trim(line);
        
        // Skip comments and empty lines
        if (line.empty() || line[0] == '#') continue;
        
        // Skip header line (contains "file_name")
        if (line_num == 1 || line.find("file_name") != std::string::npos) continue;
        
        // Parse CSV fields
        std::vector<std::string> fields = split_csv_line(line);
        if (fields.size() < 7) {
            std::fprintf(stderr, "[AUDIO_OBF] WARNING: Line %d has insufficient fields, skipping\n", 
                         line_num);
            continue;
        }
        
        // Build profile
        AudioProfile profile;
        profile.file_name = fields[0];
        
        // Parse numeric fields (empty = 0)
        profile.min_pitch_cents = fields[1].empty() ? 0 : std::atoi(fields[1].c_str());
        profile.max_pitch_cents = fields[2].empty() ? 0 : std::atoi(fields[2].c_str());
        profile.noise_type = fields[3].empty() ? "none" : fields[3];
        profile.noise_snr_db = fields[4].empty() ? 0.0f : std::atof(fields[4].c_str());
        profile.min_freq = fields[5].empty() ? 0 : std::atoi(fields[5].c_str());
        profile.max_freq = fields[6].empty() ? 0 : std::atoi(fields[6].c_str());
        
        // Parse new fields (Step 2 extended) - optional columns 8,9,10
        if (fields.size() > 7) 
            profile.eq_tilt_db = fields[7].empty() ? 0.0f : std::atof(fields[7].c_str());
        if (fields.size() > 8) 
            profile.hp_hz = fields[8].empty() ? 0 : std::atoi(fields[8].c_str());
        if (fields.size() > 9) 
            profile.lp_hz = fields[9].empty() ? 0 : std::atoi(fields[9].c_str());
        
        // Store in map (key = file_name)
        g_audio_profiles[profile.file_name] = profile;
        profiles_loaded++;
    }
    
    file.close();
    
    std::printf("[AUDIO_OBF] Loaded %d profiles from config (%s)\n", 
                profiles_loaded, path.c_str());
    return true;
}
```

**Parser implementation choices**:

1. **`trim()`**: Removes whitespace (spaces, tabs, newlines) from the beginning and end of string. Necessary because text editors can insert accidental spaces

2. **`split_csv_line()`**: Splits the line on commas, respecting quotes. I use an `in_quotes` flag to correctly handle fields like `"field, with comma"` (not used in our case, but present for future robustness)

3. **Empty field handling**: `fields[i].empty() ? 0 : std::atoi(...)` assigns `0` if the field is empty, otherwise converts the string to a number. This allows CSV like: `weapon/usp,-200,500,none,,,,0,0,0` where fields 4-7 are empty

4. **Optional columns**: `if (fields.size() > 7)` checks if columns 8-10 exist (added in Step 2 extended). Ensures backward-compatibility with old CSV files that only have 7 columns

5. **Global map**: `g_audio_profiles` is a `std::unordered_map<std::string, AudioProfile>` with key = `file_name`. O(1) lookup during audio processing

#### 5.2.3 Global State and Initialization

**Internal global variables** (`audio_runtime_obf.cpp`, lines 28-41):

```cpp
// Default profile used for all transformations (Step 1)
static ARO_Profile g_profile;

// Map of sound-specific audio profiles loaded from CSV (Step 2)
// Key = file_name (e.g. "weapon/usp"), Value = AudioProfile with all parameters
static std::unordered_map<std::string, AudioProfile> g_audio_profiles;

// Configuration source (for logging): "DEFAULT", "ENV", "CLI"
static const char* g_config_source = "DEFAULT";

// Initialization flag (prevent double-init)
static bool g_initialized = false;
```

**Initialization function** (`audio_runtime_obf.cpp`, lines 540-597):

```cpp
void aro_init_from_env_and_cli(int argc, char** argv)
{
    if (g_initialized) {
        return; // Already initialized, skip
    }
    
    // Reset state
    g_profile = ARO_Profile();
    g_config_source = "DEFAULT";
    
    // STEP 1: Read environment variables
    const char* env_enabled = std::getenv("AC_AUDIO_OBF");
    
    if (env_enabled != nullptr) {
        int val = std::atoi(env_enabled);
        if (val == 1) {
            g_profile.enabled = true;
            g_config_source = "ENV";
        }
    }
    
    // STEP 2: Parse CLI arguments (overrides ENV)
    // Look for pattern: --audio-obf on|off
    for (int i = 1; i < argc; ++i) {
        if (std::strcmp(argv[i], "--audio-obf") == 0) {
            // Check if there's a next argument
            if (i + 1 < argc) {
                const char* arg = argv[i + 1];
                if (std::strcmp(arg, "on") == 0) {
                    g_profile.enabled = true;
                    g_config_source = "CLI";
                    break;
                } else if (std::strcmp(arg, "off") == 0) {
                    g_profile.enabled = false;
                    g_config_source = "CLI";
                    break;
                }
            }
        }
    }
    
    // STEP 3: Initialize default parameters for transformations
    // (For Step 1-2, all disabled here - managed by CSV)
    g_profile.use_pitch = false;
    g_profile.pitch_cents = 0;
    g_profile.use_noise = false;
    g_profile.noise_snr_db = 0.0f;
    g_profile.use_tone = false;
    g_profile.tone_freq_hz = 0.0f;
    g_profile.tone_level_db = 0.0f;
    
    // STEP 4: Load audio profiles from CSV (only if enabled=true)
    if (g_profile.enabled) {
        aro_load_profiles_from_csv("audio_obf_config.csv");
    }
    
    g_initialized = true;
}
```

**Configuration precedence**: `CLI > ENV > default (OFF)`

**Initial state logging** (called from `main.cpp`):

```cpp
void aro_log_loaded()
{
    std::printf("[AUDIO_OBF] enabled=%d", g_profile.enabled ? 1 : 0);
    
    if (g_profile.enabled) {
        std::printf(" from=%s", g_config_source);
    }
    
    std::printf(" use_pitch=%d", g_profile.use_pitch ? 1 : 0);
    std::printf(" use_noise=%d", g_profile.use_noise ? 1 : 0);
    std::printf(" use_tone=%d\n", g_profile.use_tone ? 1 : 0);
    std::fflush(stdout);
}
```

**Example output**:
```
[AUDIO_OBF] Loaded 1 profiles from config (audio_obf_config.csv)
[AUDIO_OBF] enabled=1 from=ENV use_pitch=0 use_noise=0 use_tone=0
```

### 5.3 Implemented DSP Algorithms — Complete Documentation

This section documents in detail **all DSP algorithms** implemented in the `audio_runtime_obf` framework. For each effect I present:
- **Technical and perceptual objective**
- **Complete mathematical algorithm**
- **C++ code with comments**
- **Parameters used and motivations**
- **Bibliographic references**

#### 5.3.1 Pitch Shift (SoundTouch WSOLA)

**Objective**: Change the fundamental frequency of the sound **without altering duration** (inverse time-stretching disabled).

**Library**: [SoundTouch](https://www.surina.net/soundtouch/) v2.x (LGPL) — implements **WSOLA (Waveform Similarity Overlap-Add)** algorithm.

**WSOLA Algorithm** (simplified):
1. Divides the signal into overlapping frames (window ~20-50 ms)
2. For each frame, finds the next frame with **maximum cross-correlation** (similarity)
3. Applies overlap-add with fade in/out to avoid clicks
4. Pitch shift = re-sampling of frame matching rate

**C++ Implementation** (`audio_runtime_obf.cpp`, `apply_pitch_shift()`, lines 100-153):

```cpp
static bool apply_pitch_shift(float* samples, int frames, int channels, int samplerate, int cents)
{
#ifdef HAVE_SOUNDTOUCH
    if (cents == 0) return false;  // Skip if no shift
    
    try {
        SoundTouch st;
        st.setSampleRate(samplerate);
        st.setChannels(channels);
        st.setPitchSemiTones(cents / 100.0f);  // cents → semitones (100 cents = 1 semitone)
        
        // Feed samples to SoundTouch
        st.putSamples(samples, frames);
        st.flush();  // Force processing of all samples
        
        // Receive processed samples (output length may vary slightly)
        std::vector<float> output;
        output.reserve(frames * channels * 2);  // Allocate extra space for safety
        
        const int RECV_BUFF_SIZE = 4096;
        float temp_buff[RECV_BUFF_SIZE];
        int nSamples;
        
        do {
            nSamples = st.receiveSamples(temp_buff, RECV_BUFF_SIZE / channels);
            if (nSamples > 0) {
                for (int i = 0; i < nSamples * channels; ++i) {
                    output.push_back(temp_buff[i]);
                }
            }
        } while (nSamples != 0);
        
        // Copy back to original buffer (truncate or zero-pad if necessary)
        int output_frames = output.size() / channels;
        int copy_frames = std::min(output_frames, frames);
        
        for (int i = 0; i < copy_frames * channels; ++i) {
            samples[i] = output[i];
        }
        
        // Zero-pad if output shorter (can happen with very high pitch)
        for (int i = copy_frames * channels; i < frames * channels; ++i) {
            samples[i] = 0.0f;
        }
        
        return true;
    } catch (...) {
        std::fprintf(stderr, "[audio_runtime_obf] ERROR: SoundTouch exception\n");
        return false;
    }
#else
    return false;  // SoundTouch not available
#endif
}
```

**Step 2 midpoint calculation**:
```cpp
int pitch_cents = (audio_prof.min_pitch_cents + audio_prof.max_pitch_cents) / 2;
```

Example for `weapon/usp` (`-200, 500`):
\[ \text{pitch\_cents} = \frac{-200 + 500}{2} = +150 \text{ cents} \approx +1.5 \text{ semitones} \]

**Key parameters**:
- **Input**: float buffer [-1, 1], pitch in cents
- **Algorithm**: WSOLA (preserves time, changes only freq)
- **Output**: pitch-shifted buffer (length may vary ±1-2%)
- **Latency**: ~20-50 ms (depends on window size)

**Applicability**: All types of sounds (weapon, footsteps, voice). For weapon sounds, pitch shift is the **least perceptible** effect if kept below ±200 cents.

**References**:
- [SoundTouch Library Documentation](https://www.surina.net/soundtouch/)
- Werner Verhelst, Marc Roelands (1993). "An Overlap-Add Technique Based on Waveform Similarity (WSOLA) For High Quality Time-Scale Modification of Speech"

---

#### 5.3.2 White Noise Injection

**Objective**: Add uniform Gaussian noise (flat spectrum) to degrade the target signal-to-noise ratio (SNR).

**Mathematical Algorithm**:

White noise is a random signal with **constant spectral power** across all frequencies. The formula to calculate noise amplitude given a target SNR is:

\[ \text{SNR}_{\text{dB}} = 20 \log_{10}\left(\frac{\text{RMS}_{\text{signal}}}{\text{RMS}_{\text{noise}}}\right) \]

Invert to obtain noise RMS:

\[ \text{RMS}_{\text{noise}} = \frac{\text{RMS}_{\text{signal}}}{10^{\text{SNR}/20}} \]

**Correction for Uniform Distribution**:

A uniform random signal in \([-1,1]\) has theoretical RMS:

\[ \text{RMS}_{\text{uniform}} = \frac{1}{\sqrt{3}} \approx 0.577 \]

Therefore we must scale the generated noise amplitude:

\[ A_{\text{noise}} = \frac{\text{RMS}_{\text{noise}}}{\text{RMS}_{\text{uniform}}} = \frac{\text{RMS}_{\text{signal}}}{10^{\text{SNR}/20}} \cdot \sqrt{3} \]

**C++ Implementation** (`audio_runtime_obf.cpp`, `add_white_noise()`, lines 174-206):

```cpp
static void add_white_noise(float* samples, int count, float snr_db)
{
    // 1) Calculate signal RMS
    float rms_signal = calculate_rms(samples, count);
    if (rms_signal < 1e-6f) return;  // Signal too weak, skip
    
    // 2) Calculate target noise amplitude
    // Note: uniform noise [-1,1] has theoretical RMS ≈ 1/√3 ≈ 0.577
    float rms_uniform_noise = 1.0f / std::sqrt(3.0f);  // ≈ 0.577
    float target_rms_noise = rms_signal / std::pow(10.0f, snr_db / 20.0f);
    float noise_amplitude = target_rms_noise / rms_uniform_noise;
    
    // 3) Temporary DEBUG (for real SNR verification)
    static int debug_count = 0;
    if (debug_count++ < 3) {
        std::fprintf(stderr, "[NOISE_DEBUG] rms_signal=%.6f, snr_db=%.1f, target_rms_noise=%.6f, noise_amplitude=%.6f\n",
                     rms_signal, snr_db, target_rms_noise, noise_amplitude);
    }
    
    // 4) Generate uniform white noise [-1, 1]
    static std::mt19937 rng(12345);  // Fixed seed for Step 2 reproducibility
    std::uniform_real_distribution<float> dist(-1.0f, 1.0f);
    
    // 5) Add noise to signal
    for (int i = 0; i < count; ++i) {
        float noise = dist(rng) * noise_amplitude;
        samples[i] += noise;
        
        // Hard clipping to prevent overflow
        if (samples[i] > 1.0f) samples[i] = 1.0f;
        if (samples[i] < -1.0f) samples[i] = -1.0f;
    }
}

/**
 * Support function: calculates RMS (Root Mean Square) of signal.
 * RMS = √(Σ x²/N)
 */
static float calculate_rms(const float* samples, int count)
{
    float sum = 0.0f;
    for (int i = 0; i < count; ++i) {
        sum += samples[i] * samples[i];
    }
    return std::sqrt(sum / count);
}
```

**Example Parameters Used**:
- `weapon/usp`: SNR = `35` dB → barely perceptible noise (JND threshold ~40 dB)
- Voice: SNR = `40-45` dB → very light noise

**Random Generator**: `std::mt19937` (Mersenne Twister) with fixed seed `12345` for **Step 2 determinism**. In Step 3, seed will be randomized.

**Perceptibility**: White noise is more "harsh" than pink noise because it has a lot of energy at high frequencies (where the human ear is more sensitive).

---

#### 5.3.3 Pink Noise Injection (1/f Filter)

**Objective**: Noise with more energy at low frequencies (1/f spectrum), more "natural" than white noise.

**Mathematical Algorithm**:

Pink noise has power spectral density inversely proportional to frequency:

\[ S(f) \propto \frac{1}{f} \]

To generate it, I use a white noise filter with a **single-pole lowpass IIR**:

\[ y[n] = \alpha \cdot y[n-1] + (1-\alpha) \cdot x[n] \]

With \(\alpha = 0.99\), I obtain an approximation of the \(1/f\) spectrum.

**C++ Implementation** (`audio_runtime_obf.cpp`, `add_pink_noise()`, lines 253-300):

```cpp
static void add_pink_noise(float* samples, int count, float snr_db)
{
    // 1) Calculate signal RMS
    float rms_signal = calculate_rms(samples, count);
    if (rms_signal < 1e-6f) return;
    
    // 2) Calculate target noise amplitude
    float target_rms_noise = rms_signal / std::pow(10.0f, snr_db / 20.0f);
    
    // 3) Generate white noise
    std::vector<float> white_noise(count);
    static std::mt19937 rng(12346);  // Different seed from white
    std::uniform_real_distribution<float> dist(-1.0f, 1.0f);
    
    for (int i = 0; i < count; ++i) {
        white_noise[i] = dist(rng);
    }
    
    // 4) Filter with approximated 1/f IIR (single-pole lowpass)
    std::vector<float> pink_noise(count);
    float y_prev = 0.0f;
    const float alpha = 0.99f;  // IIR coefficient (higher = more filtering)
    
    for (int i = 0; i < count; ++i) {
        y_prev = alpha * y_prev + (1.0f - alpha) * white_noise[i];
        pink_noise[i] = y_prev;
    }
    
    // 5) Normalize RMS for target SNR
    float rms_pink = calculate_rms(pink_noise.data(), count);
    if (rms_pink > 1e-6f) {
        float scale = target_rms_noise / rms_pink;
        for (int i = 0; i < count; ++i) {
            pink_noise[i] *= scale;
        }
    }
    
    // 6) Add to signal
    for (int i = 0; i < count; ++i) {
        samples[i] += pink_noise[i];
        
        // Clipping
        if (samples[i] > 1.0f) samples[i] = 1.0f;
        if (samples[i] < -1.0f) samples[i] = -1.0f;
    }
}
```

**Difference from White Noise**:

| Characteristic | White Noise | Pink Noise |
|----------------|-------------|------------|
| Spectrum | Flat | 1/f (more energy at low freq) |
| Perception | Harsh, "hissing" | Warm, "natural" |
| Ideal use | Short weapon sounds | Voice, footsteps |
| Equivalent SNR | ~35 dB | ~16-24 dB (more perceptible) |

**weapon/usp parameters**:
- Pink SNR range calibrated: `16-24` dB (much lower than white because more perceptible)

**References**:
- [Pink noise generation techniques](https://www.dsprelated.com/freebooks/sasp/Example_Synthesis_1_F_Noise.html)
- [Voss-McCartney algorithm](https://www.firstpr.com.au/dsp/pink-noise/)

---

#### 5.3.4 Tone Injection (Pure Sinusoid)

**Objective**: Add sinusoidal tone at specific frequency (9-11 kHz) to disturb MFCC-based feature extraction.

**Mathematical Algorithm**:

Sinusoid generation:

\[ x(t) = A \sin(2\pi f t) \]

Where:
- \(A\) = amplitude calculated from target SNR
- \(f\) = freq_hz (e.g., 10000 Hz)
- \(t\) = time in seconds = `frame / samplerate`

**C++ Implementation** (`audio_runtime_obf.cpp`, `add_tone()`, lines 218-243):

```cpp
static void add_tone(float* samples, int frames, int channels, int samplerate, int freq_hz, float snr_db)
{
    // 1) Calculate signal RMS
    int count = frames * channels;
    float rms_signal = calculate_rms(samples, count);
    if (rms_signal < 1e-6f) return;
    
    // 2) Calculate tone amplitude (same calculation as noise)
    float tone_amplitude = rms_signal / std::pow(10.0f, snr_db / 20.0f);
    
    // 3) Generate sinusoid and add to all channels
    for (int frame = 0; frame < frames; ++frame) {
        float t = static_cast<float>(frame) / samplerate;  // Time in seconds
        float tone_sample = tone_amplitude * std::sin(2.0f * M_PI * freq_hz * t);
        
        // Add to all channels (stereo = same tone in L and R)
        for (int ch = 0; ch < channels; ++ch) {
            int idx = frame * channels + ch;
            samples[idx] += tone_sample;
            
            // Clipping
            if (samples[idx] > 1.0f) samples[idx] = 1.0f;
            if (samples[idx] < -1.0f) samples[idx] = -1.0f;
        }
    }
}
```

**Frequencies Used**: `9000-11000` Hz (borderline ultrasonic)

**High frequency motivation**:
1. Less perceptible (near auditory threshold ~15-16 kHz for adults)
2. Disturbs MFCC in high Mel bands (where weapon sounds have less natural energy)
3. Does not interfere with weapon fundamental frequencies (~300-800 Hz)

**Perceptibility**: Tone is more "surgical" than noise — creates a subtle but constant whistle. Very effective against ML models but more perceptually risky.

**Usage**: In Step 2, tone injection is rarely used (only for specific tests). I prefer white/pink noise for weapon sounds.

---

#### 5.3.5 EQ Tilt (High-Shelf Biquad @ 2 kHz)

**Objective**: Change the "timbre color" of the sound by shifting spectral energy toward high or low frequencies, without altering the temporal waveform.

**Algorithm**: Implemented as **high-shelf biquad filter** @ 2 kHz with variable gain.

**Biquad High-Shelf Parameters** (from Audio EQ Cookbook):

Given:
- `fc` = shelf frequency (2000 Hz)
- `gain_db` = shelf gain in dB
- `Q` = quality factor (0.707 for Butterworth)

Coefficient calculation:

\[
\begin{aligned}
A &= 10^{\text{gain\_db}/40} \\
\omega_0 &= \frac{2\pi f_c}{f_s} \\
\cos(\omega_0) &= \cos(\omega_0) \\
\sin(\omega_0) &= \sin(\omega_0) \\
\alpha &= \frac{\sin(\omega_0)}{2Q}
\end{aligned}
\]

High-shelf coefficients:

\[
\begin{aligned}
a_0 &= (A+1) - (A-1)\cos(\omega_0) + 2\sqrt{A}\alpha \\
b_0 &= \frac{A \cdot [(A+1) + (A-1)\cos(\omega_0) + 2\sqrt{A}\alpha]}{a_0} \\
b_1 &= \frac{-2A \cdot [(A-1) + (A+1)\cos(\omega_0)]}{a_0} \\
b_2 &= \frac{A \cdot [(A+1) + (A-1)\cos(\omega_0) - 2\sqrt{A}\alpha]}{a_0} \\
a_1 &= \frac{2 \cdot [(A-1) - (A+1)\cos(\omega_0)]}{a_0} \\
a_2 &= \frac{(A+1) - (A-1)\cos(\omega_0) - 2\sqrt{A}\alpha}{a_0}
\end{aligned}
\]

**C++ Implementation** (`audio_runtime_obf.cpp`, `apply_eq_tilt()`, lines 411-439):

```cpp
static void apply_eq_tilt(float* samples, int frames, int channels, int sr, float tilt_db)
{
    if (std::abs(tilt_db) < 0.1f) return;  // Skip if almost zero
    
    // Shelf filter parameters
    float shelf_freq = 2000.0f;  // Shelf frequency @ 2 kHz
    float A = std::pow(10.0f, tilt_db / 40.0f);  // Gain factor (dB → linear)
    float omega = 2.0f * M_PI * shelf_freq / sr;
    float cos_w = std::cos(omega);
    float sin_w = std::sin(omega);
    float alpha = sin_w / (2.0f * 0.707f);  // Q = 0.707 (Butterworth)
    
    // High-shelf coefficients (from Audio EQ Cookbook)
    float a0 = (A+1.0f) - (A-1.0f)*cos_w + 2.0f*std::sqrt(A)*alpha;
    float b0 = A * ((A+1.0f) + (A-1.0f)*cos_w + 2.0f*std::sqrt(A)*alpha);
    float b1 = -2.0f * A * ((A-1.0f) + (A+1.0f)*cos_w);
    float b2 = A * ((A+1.0f) + (A-1.0f)*cos_w - 2.0f*std::sqrt(A)*alpha);
    float a1 = 2.0f * ((A-1.0f) - (A+1.0f)*cos_w);
    float a2 = (A+1.0f) - (A-1.0f)*cos_w - 2.0f*std::sqrt(A)*alpha;
    
    // Normalize coefficients (a0 = 1)
    b0 /= a0; b1 /= a0; b2 /= a0;
    a1 /= a0; a2 /= a0;
    
    // Apply biquad filter
    apply_biquad(samples, frames, channels, b0, b1, b2, a1, a2);
}
```

**Effect**:
- `tilt_db > 0`: Boost high freq (> 2 kHz) → sound more "bright", "metallic"
- `tilt_db < 0`: Boost low freq (< 2 kHz) → sound more "warm", "dark"

**weapon/usp range**:
- Boost: `+2` to `+6` dB
- Cut: `-3` to `-9` dB

**References**:
- [Audio EQ Cookbook](https://webaudio.github.io/Audio-EQ-Cookbook/audio-eq-cookbook.html) by Robert Bristow-Johnson

---

#### 5.3.6 High-Pass Filter (Butterworth 2nd order)

**Objective**: Attenuate frequencies below a cutoff (removes non-relevant low "rumble").

**Algorithm**: Butterworth 2nd order filter (maximally flat in passband).

**HP Coefficient Formula** (from Audio EQ Cookbook):

Given:
- `fc` = cutoff frequency (Hz)
- `Q` = quality factor (0.707 for Butterworth)

\[
\begin{aligned}
\omega_0 &= \frac{2\pi f_c}{f_s} \\
\alpha &= \frac{\sin(\omega_0)}{2Q} \\
a_0 &= 1 + \alpha \\
b_0 &= \frac{1 + \cos(\omega_0)}{2a_0} \\
b_1 &= \frac{-(1 + \cos(\omega_0))}{a_0} \\
b_2 &= \frac{1 + \cos(\omega_0)}{2a_0} \\
a_1 &= \frac{-2\cos(\omega_0)}{a_0} \\
a_2 &= \frac{1 - \alpha}{a_0}
\end{aligned}
\]

**C++ Implementation** (`audio_runtime_obf.cpp`, `butterworth_hp_coeffs()`, lines 354-370):

```cpp
static void butterworth_hp_coeffs(float fc, int sr, float& b0, float& b1, float& b2, float& a1, float& a2)
{
    const float Q = 0.707f;  // Butterworth
    float omega = 2.0f * M_PI * fc / sr;
    float cos_w = std::cos(omega);
    float sin_w = std::sin(omega);
    float alpha = sin_w / (2.0f * Q);
    
    float a0 = 1.0f + alpha;
    
    // HP coefficients (normalized by a0)
    b0 = (1.0f + cos_w) / (2.0f * a0);
    b1 = -(1.0f + cos_w) / a0;
    b2 = (1.0f + cos_w) / (2.0f * a0);
    a1 = (-2.0f * cos_w) / a0;
    a2 = (1.0f - alpha) / a0;
}
```

**Rolloff**: -40 dB/decade (12 dB/octave) → smooth transition.

**weapon/usp cutoff**: `150-250` Hz
- Removes low "rumble" (< 150 Hz)
- Preserves "body" of shot (300-800 Hz)

**Application**: See §5.3.8 for `apply_biquad()`

---

#### 5.3.7 Low-Pass Filter (Butterworth 2nd order)

**Objective**: Attenuate frequencies above a cutoff (removes high "hiss").

**LP Coefficient Formula** (from Audio EQ Cookbook):

\[
\begin{aligned}
b_0 &= \frac{1 - \cos(\omega_0)}{2a_0} \\
b_1 &= \frac{1 - \cos(\omega_0)}{a_0} \\
b_2 &= \frac{1 - \cos(\omega_0)}{2a_0} \\
a_1 &= \frac{-2\cos(\omega_0)}{a_0} \\
a_2 &= \frac{1 - \alpha}{a_0}
\end{aligned}
\]

**C++ Implementation** (`audio_runtime_obf.cpp`, `butterworth_lp_coeffs()`, lines 379-395):

```cpp
static void butterworth_lp_coeffs(float fc, int sr, float& b0, float& b1, float& b2, float& a1, float& a2)
{
    const float Q = 0.707f;
    float omega = 2.0f * M_PI * fc / sr;
    float cos_w = std::cos(omega);
    float sin_w = std::sin(omega);
    float alpha = sin_w / (2.0f * Q);
    
    float a0 = 1.0f + alpha;
    
    // LP coefficients
    b0 = (1.0f - cos_w) / (2.0f * a0);
    b1 = (1.0f - cos_w) / a0;
    b2 = (1.0f - cos_w) / (2.0f * a0);
    a1 = (-2.0f * cos_w) / a0;
    a2 = (1.0f - alpha) / a0;
}
```

**weapon/usp cutoff**: `8000-10000` Hz
- Cuts high freq beyond "significant" audible
- Preserves initial transient (< 8 kHz)

**Combined HP+LP effect**: Implicit bandpass (e.g., 150-10000 Hz)

---

#### 5.3.8 Biquad Filter Application (2nd order IIR)

**General Algorithm**: IIR (Infinite Impulse Response) 2nd order filter, aka "biquad".

**Difference Equation (Direct Form I)**:

\[ y[n] = b_0 x[n] + b_1 x[n-1] + b_2 x[n-2] - a_1 y[n-1] - a_2 y[n-2] \]

**C++ Implementation** (`audio_runtime_obf.cpp`, `apply_biquad()`, lines 320-345):

```cpp
struct BiquadState {
    float x1 = 0.0f, x2 = 0.0f;  // Input history (delay line)
    float y1 = 0.0f, y2 = 0.0f;  // Output history (feedback)
};

static void apply_biquad(float* samples, int frames, int channels, 
                         float b0, float b1, float b2, float a1, float a2)
{
    // Independent state per channel (avoids stereo leakage)
    std::vector<BiquadState> states(channels);
    
    for (int frame = 0; frame < frames; ++frame) {
        for (int ch = 0; ch < channels; ++ch) {
            int idx = frame * channels + ch;
            float x = samples[idx];
            
            BiquadState& s = states[ch];
            
            // Calculate output (feedforward + feedback)
            float y = b0*x + b1*s.x1 + b2*s.x2 - a1*s.y1 - a2*s.y2;
            
            // Update history (shift register)
            s.x2 = s.x1;
            s.x1 = x;
            s.y2 = s.y1;
            s.y1 = y;
            
            samples[idx] = y;  // Overwrite in-place (no extra memory)
        }
    }
}
```

**Implementation Details**:

1. **State per channel**: Each channel has its own `BiquadState` to avoid stereo cross-talk. Crucial for preserving stereo image.

2. **In-place processing**: Directly overwrites the `samples` buffer → no extra allocation, cache-friendly.

3. **Shift register**: 
   ```cpp
   s.x2 = s.x1;  // Move x[n-1] → x[n-2]
   s.x1 = x;     // Move x[n] → x[n-1]
   ```
   Implements the "delay line" for previous samples.

4. **Feedback loop**: `-a1*y1 - a2*y2` is the IIR feedback → key difference from FIR (which has only feedforward).

**Stability**: Butterworth with Q=0.707 guarantees **poles inside the unit circle** → stable filter (no infinite oscillations).

**References**:
- [Audio EQ Cookbook](https://webaudio.github.io/Audio-EQ-Cookbook/audio-eq-cookbook.html)
- [Digital Biquad Filter (Wikipedia)](https://en.wikipedia.org/wiki/Digital_biquad_filter)
- Zölzer, Udo (2011). *DAFX: Digital Audio Effects*. Wiley.

---

### 5.4 Processing Chain and Hook Points

#### 5.4.1 Effect Application Order

I defined a **fixed order** of effect application to maximize audio quality and reduce artifacts:

```
EQ Tilt → High-Pass → Low-Pass → Pitch Shift → Tone Injection → Noise Injection
```

**Order Motivations**:

1. **EQ Tilt first**: Modifies spectral color **before** filtering, so HP/LP filters operate on the already "tilted" spectrum

2. **HP/LP before Pitch**: Filters operate in the "original" frequency domain. If I applied pitch first, I would need to adapt cutoff frequencies dynamically

3. **Pitch before Tone/Noise**: Pitch shift can introduce small spectral artifacts. Adding tone/noise after masks these artifacts

4. **Tone/Noise last**: Additive perturbations applied as the last step to preserve the target SNR calculated on the already processed signal

**Processing Chain Code** (`audio_runtime_obf.cpp`, `aro_process_pcm_int16()`, lines 642-705):

```cpp
// STEP 5: Apply transformations (order: EQ → HP → LP → pitch → tone → noise)
bool modified = false;

// 5a) EQ Tilt
bool eq_applied = false;
if (std::abs(eq_tilt_db) >= 0.1f) {
    apply_eq_tilt(float_samples.data(), frames, channels, samplerate, eq_tilt_db);
    modified = true;
    eq_applied = true;
}

// 5b) High-pass filter
bool hp_applied = false;
if (hp_hz > 0 && hp_hz < samplerate / 2) {
    float b0, b1, b2, a1, a2;
    butterworth_hp_coeffs(static_cast<float>(hp_hz), samplerate, b0, b1, b2, a1, a2);
    apply_biquad(float_samples.data(), frames, channels, b0, b1, b2, a1, a2);
    modified = true;
    hp_applied = true;
}

// 5c) Low-pass filter
bool lp_applied = false;
if (lp_hz > 0 && lp_hz < samplerate / 2) {
    float b0, b1, b2, a1, a2;
    butterworth_lp_coeffs(static_cast<float>(lp_hz), samplerate, b0, b1, b2, a1, a2);
    apply_biquad(float_samples.data(), frames, channels, b0, b1, b2, a1, a2);
    modified = true;
    lp_applied = true;
}

// 5d) Pitch shift
bool pitch_applied = false;
if (pitch_cents != 0) {
#ifdef HAVE_SOUNDTOUCH
    if (apply_pitch_shift(float_samples.data(), frames, channels, samplerate, pitch_cents)) {
        modified = true;
        pitch_applied = true;
    }
#endif
}

// 5e) Tone injection
bool tone_applied = false;
if (audio_prof.noise_type == "tone" && tone_freq > 0 && noise_snr_db > 0) {
    add_tone(float_samples.data(), frames, channels, samplerate, tone_freq, noise_snr_db);
    modified = true;
    tone_applied = true;
}

// 5f) Noise injection (white or pink)
bool noise_applied = false;
if (noise_snr_db > 0) {
    if (audio_prof.noise_type == "white") {
        add_white_noise(float_samples.data(), total_samples, noise_snr_db);
        modified = true;
        noise_applied = true;
    } else if (audio_prof.noise_type == "pink") {
        add_pink_noise(float_samples.data(), total_samples, noise_snr_db);
        modified = true;
        noise_applied = true;
    }
}
```

**Compact log per sound**:
```cpp
// STEP 6: Compact log (required format)
std::printf("[AUDIO_OBF] %s → ", logical_name.c_str());

if (pitch_applied) std::printf("pitch:%+dc; ", pitch_cents);
else std::printf("pitch:off; ");

if (eq_applied) std::printf("eq:%+.1fdB; ", eq_tilt_db);
else std::printf("eq:off; ");

if (hp_applied || lp_applied) {
    std::printf("hp_lp:");
    if (hp_applied) std::printf("hp@%dHz", hp_hz);
    if (hp_applied && lp_applied) std::printf(",");
    if (lp_applied) std::printf("lp@%dHz", lp_hz);
    std::printf("; ");
} else {
    std::printf("hp_lp:off; ");
}

if (tone_applied) std::printf("tone:%dHz@%.1fdB; ", tone_freq, noise_snr_db);
else std::printf("tone:off; ");

if (noise_applied) std::printf("noise:%s@%.0fdB", audio_prof.noise_type.c_str(), noise_snr_db);
else std::printf("noise:off");

std::printf("\n");
std::fflush(stdout);
```

**Example Output**:
```
[AUDIO_OBF] weapon/usp → pitch:+150c; eq:+2.0dB; hp_lp:hp@150Hz,lp@10000Hz; tone:off; noise:white@35dB
```

#### 5.4.2 Hook Points in `openal.cpp`

I inserted the framework into AssaultCube's existing audio flow, intercepting PCM data **after OGG/WAV decode but before upload to OpenAL buffer**.

**OGG Hook** (`openal.cpp`, lines 318-336):

```cpp
// After OGG decode with libvorbis
{
    int16_t* pcm_data = (int16_t*)buf.getbuf();
    int channels = info->channels;
    int samplerate = info->rate;
    int bytes_total = buf.length();
    int frames = bytes_total / (sizeof(int16_t) * channels);
    
    // Logical name: use audio file name (without .ogg extension)
    std::string logical_name = name ? std::string(name) : "OGG::<unknown>";
    
    // DEBUG: print name to verify
    std::printf("[AUDIO_OBF_DEBUG] Loading OGG: '%s' (frames=%d, ch=%d, sr=%d)\n", 
                logical_name.c_str(), frames, channels, samplerate);
    std::fflush(stdout);
    
    // Process in-place (modify pcm_data directly)
    aro_process_pcm_int16(logical_name, pcm_data, frames, channels, samplerate);
}

// After processing, upload to OpenAL
alBufferData(id, info->channels == 2 ? AL_FORMAT_STEREO16 : AL_FORMAT_MONO16, 
             buf.getbuf(), buf.length(), info->rate);
```

**WAV Hook** (`openal.cpp`, lines 377-397):

```cpp
// After SDL_LoadWAV
if (wavspec.format == AUDIO_S16 || wavspec.format == AUDIO_U16)
{
    int16_t* pcm_data = (int16_t*)wavbuf;
    int channels = wavspec.channels;
    int samplerate = wavspec.freq;
    int frames = wavlen / (sizeof(int16_t) * channels);
    
    std::string logical_name = name ? std::string(name) : "WAV::<unknown>";
    
    std::printf("[AUDIO_OBF_DEBUG] Loading WAV: '%s' (frames=%d, ch=%d, sr=%d)\n", 
                logical_name.c_str(), frames, channels, samplerate);
    std::fflush(stdout);
    
    aro_process_pcm_int16(logical_name, pcm_data, frames, channels, samplerate);
}

alBufferData(id, format, wavbuf, wavlen, wavspec.freq);
```

**Hook Details**:

1. **In-place processing**: I directly modify the decoded PCM buffer (`pcm_data`) → no extra copy, efficient

2. **Logical name matching**: The name passed to the hook (e.g., `"weapon/usp"`) **must exactly match** the `file_name` in the CSV (without `.ogg`)

3. **Format support**: Only 16-bit int PCM (S16) supported. 8-bit and float are skipped with warning

4. **Timing**: Hook executed **once per sound** at load time (during `sbuffer::load()`), not at every playback, thus more efficient

#### 5.4.3 PCM int16 ↔ float Conversion

To apply floating-point DSP, I convert the buffer from `int16` to `float [-1,1]` and vice versa.

**int16 → float** (`audio_runtime_obf.cpp`, lines 55-62):

```cpp
static void int16_to_float(const int16_t* src, float* dst, int samples)
{
    // Standard conversion: int16 range [-32768, 32767] → float [-1.0, 1.0]
    const float scale = 1.0f / 32768.0f;
    for (int i = 0; i < samples; ++i) {
        dst[i] = src[i] * scale;
    }
}
```

**float → int16 with clipping** (`audio_runtime_obf.cpp`, lines 72-84):

```cpp
static void float_to_int16(const float* src, int16_t* dst, int samples)
{
    // Conversion with clipping: float [-1.0, 1.0] → int16 [-32768, 32767]
    for (int i = 0; i < samples; ++i) {
        float val = src[i] * 32768.0f;
        
        // Clipping to prevent overflow (hard distortion)
        if (val > 32767.0f) val = 32767.0f;
        if (val < -32768.0f) val = -32768.0f;
        
        dst[i] = static_cast<int16_t>(val);
    }
}
```

**Clipping necessity**: After adding noise or applying EQ with positive gain, some samples may exceed the `[-1.0, 1.0]` range. Clipping prevents catastrophic distortion (wrap-around).

**Operation order in `aro_process_pcm_int16()`**:

```cpp
// STEP 4: Convert int16 → float for processing
int total_samples = frames * channels;
std::vector<float> float_samples(total_samples);
int16_to_float(pcm, float_samples.data(), total_samples);

// STEP 5: Apply transformations (see §5.4.1)
// ... (processing chain) ...

// STEP 7: Reconvert float → int16 and overwrite original buffer
if (modified) {
    float_to_int16(float_samples.data(), pcm, total_samples);
}
```

---

### 5.5 Integration into AssaultCube Client

#### 5.5.1 Initialization in `main.cpp`

I added the initialization call in the client's `main()`:

```cpp
// In main() after argument parsing but before audio init
#include "audio_runtime_obf.h"

int main(int argc, char** argv)
{
    // ... (initial setup) ...
    
    // Initialize audio obfuscation framework
    aro_init_from_env_and_cli(argc, argv);
    aro_log_loaded();  // Log initial state
    
    // ... (init audio, video, etc.) ...
}
```

**Initial log output**:
```
[AUDIO_OBF] Loaded 1 profiles from config (audio_obf_config.csv)
[AUDIO_OBF] enabled=1 from=ENV use_pitch=0 use_noise=0 use_tone=0
```

#### 5.5.2 Makefile Integration

I added the new object files to the `Makefile`:

```makefile
CLIENT_OBJS = \
    ... (other .o) ... \
    audio_runtime_obf.o \
    openal.o

# Compilation rule for audio_runtime_obf.o
audio_runtime_obf.o: audio_runtime_obf.cpp audio_runtime_obf.h
    $(CXX) $(CXXFLAGS) $(CLIENT_INCLUDES) -DHAVE_SOUNDTOUCH -c audio_runtime_obf.cpp

# Link with SoundTouch
CLIENT_LIBS = -lSDL2 -lGL -lz -lenet -lopenal -lvorbisfile -lsoundtouch
```

**Key flags**:
- `-DHAVE_SOUNDTOUCH`: Enables pitch shift code
- `-lsoundtouch`: Link to SoundTouch library (installed via Homebrew on macOS)

#### 5.5.3 Complete Build Command

```bash
cd "AC/source/src"
make clean
make client -j8
```

**Compilation output**:
```
g++ -O2 -fomit-frame-pointer -DHAVE_SOUNDTOUCH -c audio_runtime_obf.cpp
g++ -O2 -fomit-frame-pointer -c openal.cpp
g++ -o ac_client *.o -lSDL2 -lGL -lz -lenet -lopenal -lvorbisfile -lsoundtouch
```

#### 5.5.4 Verification Test

**Base test command**:
```bash
cd "AC"
AC_AUDIO_OBF=1 ./ac_client 2>&1 | grep "AUDIO_OBF"
```

**Expected output**:
```
[AUDIO_OBF] Loaded 1 profiles from config (audio_obf_config.csv)
[AUDIO_OBF] enabled=1 from=ENV use_pitch=0 use_noise=0 use_tone=0
[AUDIO_OBF_DEBUG] Loading OGG: 'weapon/usp' (frames=2205, ch=1, sr=22050)
[AUDIO_OBF] weapon/usp → pitch:+150c; eq:+2.0dB; hp_lp:hp@150Hz,lp@10000Hz; tone:off; noise:white@35dB
```

---

### 5.6 Complete Architecture Summary

**End-to-End Data Flow**:

```
[Game requests sound "weapon/usp"]
         ↓
[openal.cpp: sbuffer::load()]
         ↓
[Decode OGG with libvorbis → PCM int16]
         ↓
[Hook: aro_process_pcm_int16("weapon/usp", pcm_data, ...)]
         ↓
[Lookup CSV: find profile for "weapon/usp"]
         ↓
[Convert int16 → float]
         ↓
[Apply DSP chain: EQ → HP → LP → Pitch → Tone → Noise]
         ↓
[Convert float → int16 with clipping]
         ↓
[Overwrite original pcm_data]
         ↓
[OpenAL: alBufferData() upload to GPU]
         ↓
[Sound ready for playback]
```

**Code Statistics**:
- `audio_runtime_obf.h`: 148 lines (API documentation)
- `audio_runtime_obf.cpp`: 791 lines (complete DSP implementation)
- `openal.cpp` (modifications): ~30 lines added (2 hook points)
- `main.cpp` (modifications): ~3 lines (init call)

**External Dependencies**:
- **SoundTouch**: Pitch shifting (LGPL, already used in other open-source audio projects)
- **libvorbisfile**: OGG decode (already present in AssaultCube)
- **OpenAL**: Audio backend (already present)
- **SDL2**: System layer (already present)

**Performance**:
- **Overhead per sound**: ~5-15 ms (one-time at load)
- **Memory overhead**: ~2x size of PCM buffer (temporary, deallocated after processing)
- **CPU**: Negligible (offline processing, not runtime during gameplay)

---

This completes the detailed technical documentation of the C++ implementation. 
In the next chapters I will document the subjective tests (calibration of `min_perc`/`max_ok` ranges) and integration with the ADV_ML framework for automated tests.

---

## 6. Subjective Tests and Range Calibration

### 6.1 Methodology: Coarse → Fine Sweep

I implemented a systematic two-phase procedure to identify optimal perceptibility thresholds:

**Phase 1 - Coarse Sweep**:
- Tests wide ranges: 0, ±10, ±25, ±50, ±100, ±200 cents
- Noise SNR: 40, 35, 30, 25, 20 dB
- Generate audio files with `cat > audio_obf_config.csv` + restart client

**Phase 2 - Fine Sweep**:
- Identifies candidate thresholds from coarse phase
- Tests narrow range: 10-20 cent steps around threshold
- Annotates subjective perception: Y/N (perceived?) + severity (1-5)

**Metrics**:
- **min_perc**: First value where I perceive difference
- **max_ok**: Last value I consider acceptable for gameplay

### 6.2 In-Game Test Setup

**Test command**:
```bash
cd AC
AC_AUDIO_OBF=1 ./ac_client
```

**Tested scenario**: Pistol Frenzy mode (weapon/usp), 10-15 minutes of gameplay per configuration.

**Actions performed**:
- Fire 30-50 shots with USP pistol
- Move around map (footsteps)
- Use voice command "Affirmative" (5 times)
- Reload weapon (10 times)

### 6.3 Results: weapon/usp (Pistol)

#### White Noise
- **Tested range**: 20, 25, 30, 35, 40, 45, 50 dB SNR
- **min_perc**: 45 dB (first perception, slight "hiss")
- **max_ok**: 35 dB (maximum acceptable, noise evident but not disturbing)
- **Note**: White noise is less perceptible than pink noise

#### Pink Noise
- **Tested range**: 10, 16, 20, 24, 30 dB SNR
- **min_perc**: 24 dB (first perception)
- **max_ok**: 16 dB (maximum acceptable)
- **Note**: More perceptible than white noise (has more energy at low frequencies)

#### Pitch Shift UP (+cents)
- **Tested range**: 0, 50, 100, 200, 300, 400, 500 cents
- **min_perc**: 100 cents (first perception, sound slightly more "sharp")
- **max_ok**: 500 cents (maximum acceptable, evident but not unnatural)
- **Note**: **Pitch shift is the least perceptible effect among all**

#### Pitch Shift DOWN (-cents)
- **Tested range**: 0, -50, -75, -100, -150, -200, -250 cents
- **min_perc**: -75 cents (first perception)
- **max_ok**: -200 cents (maximum acceptable)
- **Note**: Asymmetric range (DOWN more tolerable than UP)

#### EQ Tilt Boost (+dB)
- **Tested range**: 0, 1, 2, 3, 4, 5, 6, 9 dB
- **min_perc**: 2 dB (first perception, sound more "bright")
- **max_ok**: 6 dB (maximum acceptable, evident but not disturbing)

#### EQ Tilt Cut (-dB)
- **Tested range**: 0, -1, -3, -6, -9, -12 dB
- **min_perc**: -3 dB (first perception, sound more "dark")
- **max_ok**: -9 dB (maximum acceptable)
- **Note**: Boost and cut have symmetric ranges

#### High-Pass Filter (HP)
- **Tested range**: 0, 80, 100, 150, 200, 250, 300 Hz
- **min_perc**: 150 Hz (first perception, low freq cut)
- **max_ok**: 250 Hz (maximum acceptable, sound more "light")

#### Low-Pass Filter (LP)
- **Tested range**: 8000, 10000, 12000, 14000 Hz
- **min_perc**: 10000 Hz (first perception, high freq cut)
- **max_ok**: 8000 Hz (maximum acceptable, sound more "dark"/"muffled")

### 6.4 Final CSV Configuration
Based on the tests performed, below is an example of the CSV configuration file compilation. This configuration derives from the test on the pistol shot sound `weapon/usp`:

```csv
file_name,min_pitch_cents,max_pitch_cents,noise_type,noise_snr_db,min_freq,max_freq,eq_tilt_db,hp_hz,lp_hz
weapon/usp,-200,500,white,35,,,2,150,10000
```

**Explanation**:
- Pitch: asymmetric range [-200, +500] cents
- White noise: 35 dB SNR (toward max_ok)
- EQ tilt: +2 dB (minimum perceptible boost)
- HP: 150 Hz (minimum perceptible)
- LP: 10000 Hz (minimum perceptible)

### 6.5 Methodological Notes on Tests

It is important to emphasize that the range values presented in this section represent **rough estimates** obtained through preliminary subjective tests. These values were determined primarily through direct listening during gameplay sessions, without the use of automatic audio analysis algorithms.

The system was designed to be **scalable** to allow execution of an unlimited number of tests on any game sound. This approach allows defining much more precise range intervals through:

- **Systematic tests**: Application of coarse → fine sweep methodology on a larger sample of sounds
- **Objective validation**: Integration with perceptual analysis algorithms (PSNR, PESQ, STOI) to correlate quantitative measures with subjective perception
- **Multi-user calibration**: Extension of tests to more players to reduce subjective variability

The values presented in this section therefore provide a **starting base** for system calibration, which can be refined through more extensive tests and more rigorous validation methodologies.
 
**Priority for Step 3 (Randomization)**:
1. **Pitch Shift** — Least perceptible (use more often)
2. **EQ Tilt** — Moderate
3. **HP/LP Filters** — Moderate
4. **White Noise** — Perceptible (use with moderation)
5. **Pink Noise** — More perceptible (use rarely)

---

## 7. Step 3: Parameter Randomization with UNIFORM Distribution

### 7.1 Motivation and R₀ vs R₁ Model

**Strategic objective**: Prevent the attacker from training a stable ML model on our perturbed audio.

**FINAL Implementation Choice**: After theoretical analysis and comparison, I implemented **UNIFORM distribution** for all parameters (not gaussian/beta). Motivation: maximizes entropy, covers 100% of calibrated range, impossible to infer for the attacker.

**Attack scenario**:
1. Attacker collects dataset with perturbations R₀ (time t₀)
2. Trains ML model on R₀ + A (original audio + perturbation)
3. Model learns to recognize sounds despite **fixed** perturbation R₀

**R₁ Defense**:
- Change from R₀ to R₁ with **random parameters** within calibrated ranges
- Model trained on R₀ **degrades** on R₁
- Formula: \( \text{Degradation} = \text{Acc}(R_0) - \text{Acc}(R_1) \)
- Target: Degradation ≥ 20-30%

### 7.2 Why UNIFORM Distribution? (Comparative Analysis)

I initially considered non-uniform distributions (Gaussian, Beta) to favor "less perceptible" central values. However, after theoretical analysis I concluded that **UNIFORM distribution is superior** for the anti-ML objective:

| Criterion | Gaussian/Beta | **UNIFORM** ✅ |
|----------|----------------|-----------------|
| **Entropy H(X)** | ~2.5 bit | **3.0 bit** (maximum) |
| **Range coverage** | 68% (±1σ) | **100%** |
| **Attacker prediction** | Possible (central cluster) | **Impossible** (flat) |
| **Dataset variety** | Limited (extremes rare) | **Maximum** |
| **D_KL(R₁ ‖ R₀)** | ~0.3 | **~0.8** (maximum divergence) |

**Theoretical Motivations**:

1. **Maximum Entropy Principle** (Jaynes 1957): The uniform distribution **maximizes entropy** → maximum uncertainty for the attacker.

2. **Complete Range Exploitation**: Subjective tests calibrated `[min, max]` for **every** parameter. With gaussian, **extremes** are almost never used → waste of calibration work.

3. **Inference Impossibility**: With uniform, **every value has the same probability** → attacker cannot exploit statistical patterns.

### 7.3 Ranges Calibrated from Subjective Tests

Final ranges for `weapon/usp` (from `RANGE.md`):

| Parameter | Range Min | Range Max | Distribution |
|-----------|-----------|-----------|---------------|
| **Pitch UP** | 75 cents | 200 cents | Uniform[75,200] |
| **Pitch DOWN** | -200 cents | -75 cents | Uniform[-200,-75] |
| **White Noise** | 35 dB SNR | 45 dB SNR | Uniform[35,45] |
| **Pink Noise** | 16 dB SNR | 24 dB SNR | Uniform[16,24] |
| **EQ Tilt (boost)** | 2 dB | 6 dB | Uniform[2,6] |
| **EQ Tilt (cut)** | -9 dB | -3 dB | Uniform[-9,-3] |
| **HP Filter** | 150 Hz | 250 Hz | Uniform[150,250] |
| **LP Filter** | 8000 Hz | 10000 Hz | Uniform[8000,10000] |

**IMPORTANT NOTE**: Pitch has a **dead zone** `[-75, 75]` cents **excluded** → values too small are useless for anti-cheat (too similar to original).

### 7.4 C++ Implementation — UNIFORM Distribution

I modified `AC/source/src/audio_runtime_obf.cpp` to implement uniform randomization:

#### 7.4.1 RNG Initialization (Seed from Timestamp)

```cpp
// Seed RNG with nanoseconds since epoch → non-reproducible
if (g_randomize_enabled) {
    auto now = std::chrono::high_resolution_clock::now();
    auto seed = std::chrono::duration_cast<std::chrono::nanoseconds>(
        now.time_since_epoch()
    ).count();
    g_rng.seed(static_cast<unsigned int>(seed));
}
```

**Implication**: Each client startup has a different seed → unpredictable parameters.

#### 7.4.2 Uniform Pitch Shift (with Dead Zone)

```cpp
static int randomize_pitch_uniform(int min_cents, int max_cents)
{
    const int DEAD_ZONE = 75;  // Exclude [-75, 75] cents
    
    // 50% probability: negative [-200, -75], 50%: positive [75, 200]
    std::uniform_int_distribution<int> coin(0, 1);
    
    if (coin(g_rng) == 0) {
        // Negative
        std::uniform_int_distribution<int> dist(min_cents, -DEAD_ZONE);
        return dist(g_rng);
    } else {
        // Positive
        std::uniform_int_distribution<int> dist(DEAD_ZONE, max_cents);
        return dist(g_rng);
    }
}
```

**Dead zone motivation**: Pitch values `[-75, 75]` are **too similar to original** → not useful for confusing ML. Excluding them increases effective diversity.

#### 7.4.3 Uniform SNR/EQ/HP/LP (Generic)

```cpp
static float randomize_snr_uniform(float min_snr, float max_snr)
{
    std::uniform_real_distribution<float> dist(min_snr, max_snr);
    return dist(g_rng);
}

static float randomize_uniform(float min_val, float max_val)
{
    std::uniform_real_distribution<float> dist(min_val, max_val);
    return dist(g_rng);
}
```

#### 7.4.4 Runtime Application

```cpp
if (g_randomize_enabled) {
    // 1. PITCH: [-200..-75] ∪ [75..200]
    pitch_cents = randomize_pitch_uniform(-200, 200);
    
    // 2. SNR: [35, 45] dB for white noise
    noise_snr_db = randomize_snr_uniform(35.0f, 45.0f);
    
    // 3. EQ: [2, 6] dB for boost
    eq_tilt_db = randomize_uniform(2.0f, 6.0f);
    
    // 4. HP: [150, 250] Hz
    hp_hz = randomize_uniform(150.0f, 250.0f);
    
    // 5. LP: [8000, 10000] Hz
    lp_hz = randomize_uniform(8000.0f, 10000.0f);
}
```

**Log output** (with randomization active):
```
[AUDIO_OBF_RAND] weapon/usp → pitch:+156c, noise:white@42.1dB, eq:+2.8dB, hp:213Hz, lp:8456Hz
... in another session ... 
[AUDIO_OBF_RAND] weapon/usp → pitch:-127c, noise:white@37.8dB, eq:+4.2dB, hp:189Hz, lp:9234Hz
```

**Observation**: Parameters are randomized **only once at client initialization** (or at first sound load). During the same gameplay session, all shots of the same weapon type use the **same randomized parameters**. This behavior derives from the fact that the system processes and stores audio only once, reusing the same processed buffer for all subsequent playbacks. Variability is therefore guaranteed only between different sessions (at each client restart), not within the same session.

#### 7.4.5 Advanced Randomization: NOISE Type and EQ Sign

**UPDATE**: To further maximize entropy, I extended randomization to include:
1. **Noise type**: randomize BETWEEN white and pink noise (not just SNR)
2. **EQ sign**: randomize BETWEEN boost and cut (not just intensity)

**Motivation**: Each audio parameter has **two randomizable dimensions**:
- **Noise**: type (white/pink) + SNR → **entropy H = 4.0 bit** (vs. 3.0 bit with SNR only)
- **EQ**: sign (boost/cut) + intensity → **entropy H = 3.5 bit** (vs. 2.5 bit with intensity only)

##### NOISE Random Implementation (`noise_type="random"`)

```cpp
// 3. NOISE: Randomize BETWEEN white and pink (if noise_type="random")
if (audio_prof.noise_type == "random") {
    // NOISE TYPE RANDOMIZATION: 50% white, 50% pink
    std::uniform_int_distribution<int> coin(0, 1);
    if (coin(g_rng) == 0) {
        // White: [35, 45] dB (from RANGE.md)
        noise_type_actual = "white";
        noise_snr_db = randomize_snr_uniform(35.0f, 45.0f);
    } else {
        // Pink: [16, 24] dB (from RANGE.md)
        noise_type_actual = "pink";
        noise_snr_db = randomize_snr_uniform(16.0f, 24.0f);
    }
} else if (audio_prof.noise_type == "white") {
    // Fixed white: [35, 45] dB
    noise_type_actual = "white";
    noise_snr_db = randomize_snr_uniform(35.0f, 45.0f);
} else if (audio_prof.noise_type == "pink") {
    // Fixed pink: [16, 24] dB
    noise_type_actual = "pink";
    noise_snr_db = randomize_snr_uniform(16.0f, 24.0f);
} else {
    // None or other: disable noise
    noise_type_actual = "none";
    noise_snr_db = 0.0f;
}
```

**CSV Configuration**: To activate noise type randomization, use `noise_type=random`:
```csv
weapon/usp,-200,200,random,0,,,999,150,10000
```

**Log output** (example with noise random):
```
[AUDIO_OBF_RAND] weapon/usp → pitch:+156c; eq:+4.2dB; hp_lp:hp@201Hz,lp@9234Hz; tone:off; noise:white@42dB
[AUDIO_OBF_RAND] weapon/usp → pitch:-134c; eq:-6.1dB; hp_lp:hp@178Hz,lp@8765Hz; tone:off; noise:pink@19dB
[AUDIO_OBF_RAND] weapon/usp → pitch:+89c; eq:+5.7dB; hp_lp:hp@234Hz,lp@9876Hz; tone:off; noise:white@38dB
```

**Observation**: The noise type changes between `white` and `pink` → completely different noise spectrum between shots.

##### EQ Random Implementation (Sign) (`eq_tilt_db=999`)

```cpp
// 4. EQ TILT: Randomize BETWEEN boost and cut (if eq_tilt_db=999 in CSV)
if (audio_prof.eq_tilt_db == 999.0f) {
    // Magic value 999 = randomize between boost AND cut
    std::uniform_int_distribution<int> coin(0, 1);
    if (coin(g_rng) == 0) {
        // Boost: [2, 6] dB (from RANGE.md)
        eq_tilt_db = randomize_uniform(2.0f, 6.0f);
    } else {
        // Cut: [-9, -3] dB (from RANGE.md)
        eq_tilt_db = randomize_uniform(-9.0f, -3.0f);
    }
} else if (std::abs(audio_prof.eq_tilt_db) > 0.1f) {
    // Specific value in CSV: use range based on sign
    float eq_min = audio_prof.eq_tilt_db;
    float eq_max = (audio_prof.eq_tilt_db > 0) ? 6.0f : -9.0f;
    eq_tilt_db = randomize_uniform(eq_min, eq_max);
} else {
    eq_tilt_db = 0.0f;  // Disabled (CSV = 0)
}
```

**CSV Configuration**: To activate EQ sign randomization, use `eq_tilt_db=999`:
```csv
weapon/usp,-200,200,random,0,,,999,150,10000
```

**Magic value 999**: This special value in the CSV tells the system to randomize **BETWEEN** boost and cut (not just within a range).

**Log output** (example with EQ random):
```
[AUDIO_OBF_RAND] weapon/usp → pitch:+156c; eq:+4.2dB; ...  (boost)
[AUDIO_OBF_RAND] weapon/usp → pitch:-134c; eq:-6.1dB; ...  (cut)
```

##### Comparative Entropy Analysis

| Strategy | H(noise) | H(EQ) | H(total) | Attacker prediction |
|-----------|----------|-------|-----------|----------------------|
| **Fixed (Step 2)** | 0 bit | 0 bit | 0 bit | Easy (deterministic) |
| **Random SNR/intensity** | 3.0 bit | 2.5 bit | 5.5 bit | Possible (if infers type/sign) |
| **Random type+SNR, sign+intensity** | **4.0 bit** | **3.5 bit** | **7.5 bit** | **Impossible** ✅ |

**Advantages**:
1. **Maximum entropy**: 7.5 bit vs. 5.5 bit (+36%)
2. **Variable spectrum**: White (flat) vs. Pink (1/f) → completely different spectral characteristics
3. **Prevents clustering**: ML model cannot cluster by "noise type" or "EQ sign"

**Trade-offs**:
- **Imperceptibility**: No impact (all values within calibrated ranges)
- **Complexity**: +20 lines of code (minimal)
- **Performance**: +2 `if` per shot (negligible)

### 7.5 Randomized Variant Generation Script

I created `ADV_ML/scripts/run_random_variants.sh` to generate batches of audio with random parameters (for ML validation):

```bash
#!/bin/bash
# Generate N variants with UNIFORM random parameters
./run_random_variants.sh weapon/usp 100
```

**Output**: CSV with parameters used for each variant:
```
variant_id,pitch_cents,noise_snr_db,eq_tilt_db,hp_hz,lp_hz
1,161,35.3,3.1,223,9435
2,-80,43.7,5.7,232,8675
3,161,37.7,4.6,174,8828
...
```

**Uniform distribution verification** (pitch):
```bash
cat random_params.csv | awk -F',' '{print $2}' | sort -n
# Expected output: values uniformly distributed in [-200..-75] ∪ [75..200]
# NO values in [-75, 75] (dead zone)
```

### 7.6 ML Testing: R₀ vs R₁ (Proposed Future Validation Workflow)

**Note**: This section describes a **proposed workflow** for ML validation that **has not yet been implemented**. It represents a future plan to test the effectiveness of randomization against attackers using machine learning models.

**Proposed ML validation workflow** (to be implemented):

1. **Dataset R₀ (baseline)**: Generate 1000 audio samples with **fixed** parameters (e.g., pitch=150c, SNR=40dB)
2. **Training**: Train CNN on spectrograms/MFCC, expected accuracy ~95%
3. **Dataset R₁ (randomized)**: Generate 1000 audio samples with **uniform random** parameters
4. **Testing on R₁**: Test model trained on R₀ with R₁ dataset, expected accuracy **< 40%** (degradation from 95%)

**Proposed commands** (to be implemented):
```bash
# 1. Generate R₀
python3 ADV_ML/scripts/generate_dataset_R0.py

# 2. Train classifier
python3 ADV_ML/scripts/train_classifier.py --dataset R0

# 3. Generate R₁
./ADV_ML/scripts/run_random_variants.sh weapon/usp 1000

# 4. Test on R₁
python3 ADV_ML/scripts/test_classifier.py --model R0 --dataset R1
```

**Expected success metric**: Degradation ≥ 20-30% (from 95% to < 70%)

**Theoretical documentation**: `ADV_ML/docs/randomization_guide.md` (formulas, graphs, FAQ)

---

## 8. System Expansion: Adding New Sounds and Modifying Ranges

### 8.1 Versatile System Architecture

The system I implemented is designed to be **easily expandable** to other game sounds. So far I have calibrated and tested only `weapon/usp` (pistol), but the architecture supports any AssaultCube audio asset.

**Key files for expansion**:
1. `AC/audio_obf_config.csv` → Parameter configuration for each sound
2. `AC/source/src/audio_runtime_obf.cpp` → Code that applies transformations

### 8.2 How to Add a New Sound

**Example**: I want to add obfuscation for `weapon/auto` (automatic machine gun).

#### 8.2.1 Identify the Logical Sound Name

I must first understand how AssaultCube identifies the sound internally:

```bash
# 1. Check sound map in audiomanager.cpp
grep -r "auto" AC/source/src/audiomanager.cpp
# Output: "weapon/auto" → logical name

# 2. Verify audio file exists
ls AC/packages/audio/sounds/weapons/
# Output: auto_shot.ogg, auto_reload.ogg, etc.
```

**Logical name found**: `weapon/auto`

#### 8.2.2 Determine Obfuscation Ranges (Subjective Tests)

I follow the **same workflow** I used for `weapon/usp`:

**Step 1**: Test single effect at a time

```bash
cd AC

# TEST PITCH SHIFT UP
cat > audio_obf_config.csv << 'EOF'
file_name,min_pitch_cents,max_pitch_cents,noise_type,noise_snr_db,min_freq,max_freq,eq_tilt_db,hp_hz,lp_hz
weapon/auto,100,100,none,,,,0,0,0
EOF
AC_AUDIO_OBF=1 ./ac_client
# Play, fire with auto, annotate: "pitch +100 cents → perceptible? Y/N"

# Repeat with increasing values: 150, 200, 300, 500 cents
# Find min_perc (first perceptible value) and max_ok (last acceptable)

# TEST PITCH SHIFT DOWN
cat > audio_obf_config.csv << 'EOF'
file_name,min_pitch_cents,max_pitch_cents,noise_type,noise_snr_db,min_freq,max_freq,eq_tilt_db,hp_hz,lp_hz
weapon/auto,-75,-75,none,,,,0,0,0
EOF
AC_AUDIO_OBF=1 ./ac_client
# Repeat with -100, -150, -200 cents

# TEST WHITE NOISE
cat > audio_obf_config.csv << 'EOF'
file_name,min_pitch_cents,max_pitch_cents,noise_type,noise_snr_db,min_freq,max_freq,eq_tilt_db,hp_hz,lp_hz
weapon/auto,0,0,white,45,,,0,0,0
EOF
AC_AUDIO_OBF=1 ./ac_client
# Repeat with SNR: 40, 35, 30, 25 dB

# TEST EQ TILT, HP, LP (same method)
```

**Step 2**: Annotate results in a table

```
=== WEAPON/AUTO - CALIBRATED RANGES ===
Pitch UP:    min_perc = 50 cents,  max_ok = 300 cents
Pitch DOWN:  min_perc = -50 cents, max_ok = -250 cents
White Noise: min_perc = 40 dB,     max_ok = 30 dB
EQ Tilt:     min_perc = 1.5 dB,    max_ok = 5 dB
HP Filter:   min_perc = 100 Hz,    max_ok = 200 Hz
LP Filter:   min_perc = 12000 Hz,  max_ok = 9000 Hz
```

**NOTE**: Ranges can be **different** for each sound type! A machine gun has a different spectrum than a pistol → calibrate separately.

#### 8.2.3 Add Configuration to CSV

I modify `AC/audio_obf_config.csv`:

```csv
file_name,min_pitch_cents,max_pitch_cents,noise_type,noise_snr_db,min_freq,max_freq,eq_tilt_db,hp_hz,lp_hz
# weapon/usp - Pistol (already calibrated)
weapon/usp,-200,200,white,35,,,2,150,10000
# weapon/auto - Machine gun (new!)
weapon/auto,-250,300,white,30,,,1.5,100,12000
```

**CSV parameter interpretation**:
- `min_pitch_cents`, `max_pitch_cents`: Pitch range for uniform randomization
- `noise_type`: `white`, `pink`, or `none`
- `noise_snr_db`: Minimum SNR (lower = more noise). For randomized uniformity I use `min`, code generates in `[min, min+10]`
- `eq_tilt_db`, `hp_hz`, `lp_hz`: Base values, code randomizes in range `[val, max_from_RANGE]`

#### 8.2.4 Test and Verification

```bash
cd AC
export AC_AUDIO_OBF=1
export AC_AUDIO_OBF_RANDOMIZE=1
./ac_client

# In-game: fire with auto, check log
# [AUDIO_OBF_RAND] weapon/auto → pitch:+187c, noise:white@33.2dB, ...

# Verify imperceptibility and parameter variety
```

### 8.3 How to Modify Ranges of an Existing Sound

**Scenario**: I calibrated ranges poorly for `weapon/usp`, I want to modify them.

**Step 1**: Re-test with new values (as in 8.2.2)

**Step 2**: Update `AC/audio_obf_config.csv`:

```csv
# BEFORE (old):
weapon/usp,-200,200,white,35,,,2,150,10000

# AFTER (new):
weapon/usp,-300,400,pink,25,,,3,200,8000
```

**Step 3**: Update `AC/source/src/audio_runtime_obf.cpp` if necessary

If **hardcoded ranges** in C++ code differ from CSV, I must update:

```cpp
// Example: EQ boost max hardcoded at 6 dB, I want to bring it to 8 dB
if (audio_prof.eq_tilt_db > 0) {
    float eq_min = audio_prof.eq_tilt_db;  // e.g. 3 dB (from CSV)
    float eq_max = 8.0f;  // MODIFIED: was 6.0f
    eq_tilt_db = randomize_uniform(eq_min, eq_max);
}
```

**Step 4**: Recompile

```bash
cd AC/source/src
make client -j
```

### 8.4 Candidate Sounds List for Expansion

**Tactically relevant sounds** (priority for anti-cheat):

1. **`weapon/auto`** — Automatic machine gun (high rate-of-fire)
2. **`weapon/shotgun`** — Shotgun (close-range shot)
3. **`weapon/sniper`** — Sniper rifle (long-range shot)
4. **`player/footsteps`** — Enemy footsteps (audio wallhack)
5. **`voicecom/affirmative`** — Voice commands (squad position)
6. **`weapon/reload`** — Weapon reload (vulnerable moment)
7. **`player/pain`** — Damage sounds (hit confirmation)

**Suggested workflow**:
- Calibrate **first** weapon sounds (simpler, uniform spectrum)
- Then **footsteps** (more complex, depend on surface)
- Finally **voicecom** (vocal spectrum, more sensitive)

### 8.5 Template for Documenting New Sounds

When I add a new sound, I document in `RANGE.md`:

```markdown
### WEAPON/AUTO (Automatic Machine Gun)

**Test date**: November 2025  
**Mode**: Team Deathmatch

==== PITCH SHIFT ====
| Value (cents) | Perceptible? | Severity (1-5) | Notes |
|----------------|---------------|----------------|------|
| +50            | Barely        | 1              | OK for competitive gameplay |
| +100           | Slight        | 2              | Sound slightly sharper |
| +200           | Evident       | 3              | Sound clearly modified |
| +300           | Strong        | 4              | MAX acceptable |
| +400           | Too much      | 5              | Unacceptable |

**Conclusion**: min_perc = 50c, max_ok = 300c

==== WHITE NOISE ====
... (same format)

==== FINAL RANGES ====
weapon/auto,-250,300,white,30,,,1.5,100,12000
```

---

**⚠️ IMPORTANT NOTE**: The following sections describe **future developments** and **validation tests** that are **still in design and implementation phase**. The current system represents a working foundation, but further improvements and validations are necessary to consider the project complete.

---
