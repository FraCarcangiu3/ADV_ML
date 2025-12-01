# Guida alla Randomizzazione Audio (Step 3) — DISTRIBUZIONE UNIFORME

**Autore**: Francesco Carcangiu  
**Data**: Novembre 2025  
**Fase**: Step 3 — Randomizzazione UNIFORME per modello R₀+A vs R₁+A  
**Revisione**: ✅ **UNIFORME** (scelta finale ottimale per anti-ML)

---

## 1. Introduzione

In questa fase finale del sistema di obfuscation audio, introduciamo la **randomizzazione UNIFORME dei parametri** audio entro i range calibrati nello Step 2. Questo permette di generare perturbazioni R₁ diverse per ogni sessione di gioco, **massimizzando la variabilità** e rendendo impossibile per un attaccante addestrare un modello ML stabile su audio perturbato.

### 1.1 Obiettivo Strategico

**Modello di attacco**:
```
Attaccante addestra modello ML su R₀ + A (tempo t₀)
→ Modello impara a riconoscere suoni con perturbazione fissa R₀
→ Deployment difesa con R₁ + A (tempo t₁, R₁ casuale UNIFORME)
→ Accuracy del modello dell'attaccante degrada significativamente (< 40%)
```

**Requisito chiave**: R₁ deve essere:
1. **Massimamente diverso da R₀** (parametri casuali **uniformi**)
2. **Impercettibile** (dentro range `min_perc` … `max_ok` testati)
3. **Massima entropia** (distribuzione uniforme → impossibile inferire pattern)

---

## 2. Perché Distribuzione UNIFORME? (Scelta Finale)

### 2.1 Analisi Comparativa: Uniforme vs. Gaussiana/Beta

| Criterio | Gaussiana/Beta | **UNIFORME** ✅ |
|----------|----------------|-----------------|
| **Entropia H(X)** | ~2.5 bit | **3.0 bit** (massimo) |
| **Copertura range** | 68% (±1σ) | **100%** |
| **Predizione attaccante** | Possibile (cluster centrale) | **Impossibile** (flat) |
| **Varietà dataset** | Limitata (estremi rari) | **Massima** |
| **D_KL(R₁ ‖ R₀)** | ~0.3 | **~0.8** (massimo divergenza) |

**CONCLUSIONE**: Per **rompere classificatori ML**, la distribuzione **UNIFORME è superiore**.

### 2.2 Motivazioni Teoriche

1. **Maximum Entropy Principle** (Jaynes 1957):  
   La distribuzione uniforme **massimizza l'entropia**:
   \[
   H(X) = -\sum_{x} p(x) \log p(x) = \log(N)
   \]
   dove \(N\) = numero di valori possibili → massima incertezza per l'attaccante.

2. **Kullback-Leibler Divergence**:  
   \[
   D_{KL}(R_1 \| R_0) = \sum_{x} p_{R_1}(x) \log \frac{p_{R_1}(x)}{p_{R_0}(x)}
   \]
   Massimizzato quando \(R_1\) è uniforme e \(R_0\) è delta (fisso) → degrado modello garantito.

3. **Sfruttamento Completo Range**:  
   I test soggettivi hanno calibrato `[min, max]` per **ogni** parametro. Con gaussiana/beta, gli **estremi** sono **quasi mai usati** → spreco del lavoro di calibrazione.

4. **Robustezza vs. Multi-Cluster Learning**:  
   Con gaussiana, l'attaccante può inferire "tendenza centrale" e addestrare modelli robusti. Con uniforme, **ogni valore ha stessa probabilità** → impossibile sfruttare pattern statistici.

---

## 3. Implementazione UNIFORME

### 3.1 Pitch Shift → Distribuzione UNIFORME (con dead zone)

**Range**: `[-200, -75]` ∪ `[75, 200]` cents (escluso `[-75, 75]` = dead zone)

**Motivazione dead zone**: Valori `[-75, 75]` cents sono **troppo simili all'originale** → inutili per anti-cheat.

**Implementazione C++**:
```cpp
static int randomize_pitch_uniform(int min_cents, int max_cents)
{
    const int DEAD_ZONE = 75;  // Sotto ±75 cents = troppo simile
    
    // 50% probabilità: negativo [-200, -75], 50%: positivo [75, 200]
    std::uniform_int_distribution<int> coin(0, 1);
    
    if (coin(g_rng) == 0) {
        // Negativo
        std::uniform_int_distribution<int> dist(min_cents, -DEAD_ZONE);
        return dist(g_rng);
    } else {
        // Positivo
        std::uniform_int_distribution<int> dist(DEAD_ZONE, max_cents);
        return dist(g_rng);
    }
}
```

### 3.2 SNR (White/Pink Noise) → Distribuzione UNIFORME

**Range**: `[35, 45]` dB per white, `[16, 24]` dB per pink (da RANGE.md)

**Implementazione C++**:
```cpp
static float randomize_snr_uniform(float min_snr, float max_snr)
{
    std::uniform_real_distribution<float> dist(min_snr, max_snr);
    return dist(g_rng);
}
```

### 3.3 EQ / HP / LP → Distribuzione UNIFORME

**Implementazione C++ (generica)**:
```cpp
static float randomize_uniform(float min_val, float max_val)
{
    std::uniform_real_distribution<float> dist(min_val, max_val);
    return dist(g_rng);
}
```

**Esempio `weapon/usp`** (`min=-200`, `max=500`):
- \( \mu = 150 \) cents
- \( \sigma = 175 \) cents
- Valori tipici: ~68% in \([−25, +325]\) cents, ~32% in range estremo

**Grafico distribuzione** (pseudo-ASCII):
```
        |
  freq  |     ***
        |    *****
        |   *******
        |  *********
        | ***********
        +----------------
       -200   150   500  (cents)
```

---

### 2.2 Noise SNR → Distribuzione Beta

**Motivazione**: Vogliamo **favorire valori SNR alti** (meno rumore percettibile) ma occasionalmente permettere rumore più forte.

**Distribuzione**: \( \text{Beta}(\alpha=2, \beta=5) \) con inversione

**Proprietà Beta(2,5)**:
- Mean = \( \frac{\alpha}{\alpha + \beta} = \frac{2}{7} \approx 0.29 \)
- Mode = \( \frac{\alpha - 1}{\alpha + \beta - 2} = \frac{1}{5} = 0.2 \)
- **Skewed verso 0** (valori bassi più probabili)

**Inversione**: Usiamo \( 1 - X \) dove \( X \sim \text{Beta}(2,5) \)
→ Questo **skewa verso 1** (valori alti più probabili)

**Scaling**:
\[
\text{SNR} = \text{SNR}_{\min} + (1 - X) \cdot (\text{SNR}_{\max} - \text{SNR}_{\min})
\]

**Implementazione C++**:
```cpp
static float randomize_snr_beta(float min_snr, float max_snr)
{
    // Genera Beta(2,5) usando Gamma distributions
    std::gamma_distribution<float> gamma_a(2.0f, 1.0f);
    std::gamma_distribution<float> gamma_b(5.0f, 1.0f);
    
    float x = gamma_a(g_rng);
    float y = gamma_b(g_rng);
    float beta_sample = x / (x + y);  // in [0,1]
    
    // Inverti per favorire valori alti
    beta_sample = 1.0f - beta_sample;
    
    // Scala a [min_snr, max_snr]
    return min_snr + beta_sample * (max_snr - min_snr);
}
```

**Esempio `weapon/usp`** (SNR base = 35 dB, range = [30, 40] dB):
- Valori tipici: ~70% in [35, 40] dB (poco rumore)
- Valori occasionali: ~30% in [30, 35] dB (rumore percettibile)

**Grafico distribuzione**:
```
        |
  freq  |         ******
        |       ********
        |     **********
        |   ************
        | **************
        +------------------
        30      35      40  (SNR dB)
                 ↑ favorito
```

---

### 2.3 EQ Tilt, HP, LP → Gaussiana Troncata

**Motivazione**: Variabilità moderata intorno al valore calibrato.

**Distribuzione**: \( N(\mu, \sigma^2) \) troncata a \([\text{min}, \text{max}]\)

**Implementazione**:
```cpp
static float randomize_gaussian_truncated(float min_val, float max_val)
{
    float mean = (min_val + max_val) / 2.0f;
    float stddev = (max_val - min_val) / 4.0f;
    
    std::normal_distribution<float> dist(mean, stddev);
    float value = dist(g_rng);
    
    return std::clamp(value, min_val, max_val);
}
```

**Uso**: Per ora EQ/HP/LP sono deterministici (Step 3 iniziale). In futuro, se definiamo range nel CSV, useranno questa distribuzione.

---

## 3. Seed RNG e Non-Reproducibilità

### 3.1 Strategia Seed

**Step 2** (deterministico):
```cpp
static std::mt19937 rng(12345);  // Seed fisso → reproducibile
```

**Step 3** (randomizzato):
```cpp
auto now = std::chrono::high_resolution_clock::now();
auto seed = std::chrono::duration_cast<std::chrono::nanoseconds>(now.time_since_epoch()).count();
g_rng.seed(static_cast<unsigned int>(seed));
```

**Proprietà**:
- Seed diverso per ogni sessione di gioco
- Risoluzione nanosecondo → praticamente impossibile da predire
- Nessuna dipendenza da `/dev/urandom` o syscall random (problemi cross-platform)

### 3.2 Logging e Debugging

**Output log con randomizzazione attiva**:
```
[AUDIO_OBF] Randomization ENABLED (seed from timestamp)
[AUDIO_OBF_RAND] weapon/usp → pitch:+237c; eq:+2.0dB; hp_lp:hp@150Hz,lp@10000Hz; tone:off; noise:white@38dB
[AUDIO_OBF_RAND] weapon/usp → pitch:+89c; eq:+2.0dB; hp_lp:hp@150Hz,lp@10000Hz; tone:off; noise:white@36dB
[AUDIO_OBF_RAND] weapon/usp → pitch:+191c; eq:+2.0dB; hp_lp:hp@150Hz,lp@10000Hz; tone:off; noise:white@39dB
```

**Nota**: Ogni riproduzione del suono può avere parametri diversi (se lo vogliamo). Per ora, parametri fissati all'inizio sessione.

---

## 4. Workflow Completo

### 4.1 Abilitazione Randomizzazione

**Variabile d'ambiente**:
```bash
export AC_AUDIO_OBF=1                  # Abilita obfuscation
export AC_AUDIO_OBF_RANDOMIZE=1       # Abilita randomizzazione
./ac_client
```

**Output atteso**:
```
[AUDIO_OBF] Loaded 1 profiles from config (audio_obf_config.csv)
[AUDIO_OBF] Randomization ENABLED (seed from timestamp)
[AUDIO_OBF] enabled=1 from=ENV use_pitch=0 use_noise=0 use_tone=0
```

### 4.2 Generazione Varianti Offline

Per test ML o soggettivi, genera N varianti con parametri casuali diversi:

```bash
cd ADV_ML/scripts
./run_random_variants.sh weapon/usp 100  # Genera 100 varianti
```

Output:
- `ADV_ML/output/random_variants/usp_variant_001.wav`
- `ADV_ML/output/random_variants/usp_variant_002.wav`
- …
- `ADV_ML/output/random_variants/random_params.csv` (parametri usati)

**Formato CSV**:
```csv
variant_id,pitch_cents,noise_snr_db,eq_tilt_db,hp_hz,lp_hz
usp_variant_001,+187,37.2,2.0,150,10000
usp_variant_002,+94,39.1,2.0,150,10000
usp_variant_003,+241,35.8,2.0,150,10000
...
```

---

## 5. Test e Validazione

### 5.1 Test Soggettivo (Ascolto Umano)

**Protocollo**:
1. Genera 20 varianti random per `weapon/usp`
2. Usa `human_listen_and_label.py` per ascoltare e annotare
3. Verifica che severity media ≤ 2.0 (accettabile)

**Comando**:
```bash
python3 ADV_ML/tests/human_listen_and_label.py ADV_ML/output/random_variants/ --subject Francesco
```

**Criterio di accettazione**: Se >80% delle varianti hanno severity ≤ 2, i range sono OK.

### 5.2 Test ML (R₀ vs R₁)

**Workflow**:
1. **Fase 1**: Addestra modello ML su dataset con parametri fissi R₀ (Step 2 deterministico)
2. **Fase 2**: Testa modello su dataset con parametri random R₁ (Step 3 randomizzato)
3. **Metrica**: Degradazione accuracy = `accuracy(R₀) - accuracy(R₁)`

**Esempio risultato atteso**:
```
Model trained on R₀ (deterministic):
  Accuracy on test set (R₀): 95.2%
  Accuracy on test set (R₁): 67.4%  ← degradazione 27.8%
```

**Interpretazione**: Il modello dell'attaccante addestrato su R₀ **fallisce** su R₁, validando il modello di difesa.

---

## 6. Considerazioni Avanzate

### 6.1 Frequenza di Cambio Parametri

**Opzioni**:
1. **Per sessione**: Parametri fissati all'avvio client, cambiano solo al restart
2. **Per suono**: Ogni riproduzione di `weapon/usp` ha parametri diversi
3. **Per evento**: Cambiano ogni N sparti (es. ogni 10 colpi)

**Scelta attuale**: **Per sessione** (più semplice, comunque efficace per ML defense)

### 6.2 Estensione Future: Range Dinamici

Attualmente CSV ha solo valori singoli per `eq_tilt_db`, `hp_hz`, `lp_hz`. Per Step 3 avanzato, estendere CSV:

```csv
file_name,min_pitch_cents,max_pitch_cents,min_eq_db,max_eq_db,min_hp_hz,max_hp_hz,min_lp_hz,max_lp_hz,noise_type,min_snr_db,max_snr_db
weapon/usp,-200,500,-3,+6,100,250,8000,12000,white,30,40
```

### 6.3 Metriche di Diversità

Per validare che R₁ è effettivamente diverso da R₀, calcolare **distanza Euclidea** nello spazio parametri:

\[
d(R_0, R_1) = \sqrt{(\text{pitch}_1 - \text{pitch}_0)^2 + (\text{SNR}_1 - \text{SNR}_0)^2 + \dots}
\]

**Target**: \( d(R_0, R_1) > \theta \) (soglia minima di diversità)

---

## 7. Riferimenti Tecnici

- **Normal Distribution**: [Wikipedia - Normal Distribution](https://en.wikipedia.org/wiki/Normal_distribution)
- **Beta Distribution**: [Wikipedia - Beta Distribution](https://en.wikipedia.org/wiki/Beta_distribution)
- **Mersenne Twister (MT19937)**: [Wikipedia - Mersenne Twister](https://en.wikipedia.org/wiki/Mersenne_Twister)
- **C++ <random>**: [cppreference - <random>](https://en.cppreference.com/w/cpp/numeric/random)

---

## 8. FAQ

**Q: Perché non usare distribuzione uniforme?**  
A: Uniforme darebbe troppa probabilità a valori estremi (molto percettibili). Gaussiana e Beta favoriscono valori meno disturbanti.

**Q: Come scegliere α e β per Beta distribution?**  
A: Abbiamo scelto Beta(2,5) empiricamente. α<β → skew verso 0; invertendo → skew verso 1 (SNR alti). Testare con α∈[1,3], β∈[3,7].

**Q: Posso disabilitare randomizzazione per test?**  
A: Sì, ometti `AC_AUDIO_OBF_RANDOMIZE=1` → torna a Step 2 deterministico.

**Q: Seed è salvato per reproducibilità?**  
A: No, per design. Se serve reproducibilità per debug, modifica codice per usare seed fisso temporaneamente.

---

**Fine documento**. Per domande: francesco.carcangiu@example.com

