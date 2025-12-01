# Panoramica Pipeline ML del Collega

> **Data creazione**: 2025-01-XX  
> **Repository analizzato**: `COLLEAGUE_BSc_Thesis/`  
> **Scopo**: Analisi della pipeline ML per identificare dove inserire la perturbazione audio anti-cheat

---

## 1. Panoramica Pipeline (Step-by-Step)

### 1.1 Flusso Generale

La pipeline del collega segue questo percorso:

```
1. Audio FLAC (8 canali, 96kHz) 
   ↓
2. Conversione FLAC → CSV (audio numerico)
   Script: fix_dataset/convert_flac_to_csv.py
   Output: Data/csv/audio_loopback_csv/audio_event_<uuid>.csv
   ↓
3. Estrazione Labels (angolo, distanza)
   Script: player_positions/grab_player_position.py
   Output: Data/csv/labels_csv/labels_<uuid>.csv
   ↓
4. Preparazione Dataset (X, y)
   Script: model_classifier/deep_cv.py (funzione load_pairs())
   - Carica coppie (audio CSV, label CSV)
   - Estrae angle_deg e distance_rel dalle label
   ↓
5. Feature Extraction
   Script: model_classifier/deep_cv.py (AudioFeatureDataset)
   - Opzione A: log-Mel + IPD/ILD (mel_ipd)
   - Opzione B: raw waveform downsampled (raw1d)
   ↓
6. Training Modelli Deep Learning (3 modelli)
   Script: model_classifier/deep_cv.py
   - ResNet18MT (ResNet18-like con multi-task heads)
   - CRNN (Conv2D + BiGRU)
   - Conv1DSeparable (depthwise-separable 1D conv)
   - 9-fold Cross-Validation stratificata
   ↓
7. Valutazione e Predizioni
   Script: model_classifier/deep_cv.py (funzione evaluate())
   - Calcola accuracy su validation set
   - Genera confusion matrices
   - Output: model_classifier/results_<timestamp>.txt
```

### 1.2 Descrizione Dettagliata per Principianti

**Step 1: Audio FLAC**
- Formato: 8 canali, 96 kHz, ~1.9 secondi per clip (0.5s pre-buffer + 1.4s post-trigger)
- Posizione: `Data/audio/audio_loopback_flac/audio_event_<uuid>.flac`
- ~970 file FLAC disponibili

**Step 2: Conversione FLAC → CSV**
- Script: `fix_dataset/convert_flac_to_csv.py` (wrapper che delega a `database_fixer.py convert-flac`)
- Oppure: `fix_dataset/database_fixer.py convert-flac`
- Output: CSV con 8 colonne (una per canale), ogni riga = un campione audio
- Posizione: `Data/csv/audio_loopback_csv/audio_event_<uuid>.csv`

**Step 3: Estrazione Labels**
- Script: `player_positions/grab_player_position.py`
- Processo:
  1. Cattura screenshot minimap dal gioco
  2. Estrae frecce rosse/verdi con OpenCV (HSV masks, template matching)
  3. Calcola angolo e distanza relativa
  4. Classifica in macro/micro bins (4 angoli × 3 distanze)
- Output: 
  - `Data/csv/labels_csv/labels_<uuid>.csv` (per ogni campione)
  - `Data/csv/merged_samples_csv/all_labels.csv` (aggregato)

**Step 4: Preparazione Dataset**
- Script: `model_classifier/deep_cv.py` (funzione `load_pairs()`)
- Processo:
  1. Trova tutte le coppie (audio CSV, label CSV) con UUID matching
  2. Per ogni label CSV, estrae `angle_deg` e `distance_rel`
  3. Converte angoli in classi (4 classi: n, w, s, e)
  4. Converte distanze in classi (3 bins: near, medium, far)
- Output: Lista di tuple `(Path(audio_csv), Path(label_csv))`

**Step 5: Feature Extraction**
- Script: `model_classifier/deep_cv.py` (classe `AudioFeatureDataset`)
- Due modalità:
  - **mel_ipd**: log-Mel spectrogram + IPD (Interaural Phase Difference) + ILD (Interaural Level Difference)
  - **raw1d**: waveform raw downsampled (es. 48kHz)
- Output: Tensor PyTorch pronto per i modelli

**Step 6: Training Modelli**
- Script: `model_classifier/deep_cv.py` (funzione `main()`)
- **3 modelli diversi** (non RandomForest!):
  1. **ResNet18MT**: ResNet18-like con multi-task heads (angle class, distance class, sin/cos regression)
  2. **CRNN**: Conv2D front-end + BiGRU + multi-task heads
  3. **Conv1DSeparable**: Depthwise-separable 1D convolutions + multi-task heads
- Training:
  - 9-fold Cross-Validation stratificata (su angle×distance)
  - Early stopping con patience
  - ReduceLROnPlateau scheduler
  - Loss multi-task: CE(angle) + CE(distance) + 0.3·L1(sin/cos) + angular penalty

**Step 7: Valutazione**
- Script: `model_classifier/deep_cv.py` (funzione `evaluate()`)
- Processo:
  1. Carica validation set
  2. Fa predizioni con modelli addestrati
  3. Calcola accuracy (angle, distance, joint)
  4. Calcola MAE angolare
  5. Genera confusion matrices
- Output: `model_classifier/results_<timestamp>.txt` con metriche per tutti i modelli

---

## 2. Tabella File/Cartelle Chiave

| Path | Ruolo | Descrizione |
|------|-------|-------------|
| `Data/audio/audio_loopback_flac/` | Dataset audio | ~970 file FLAC (8 canali, 96kHz) |
| `Data/csv/audio_loopback_csv/` | Audio processato | CSV audio (8 colonne per canale) |
| `Data/csv/labels_csv/` | Labels | CSV con angle_deg, distance_rel, macro/micro bins |
| `Data/Json/flac_json/` | Metadati audio | JSON con metadati audio (sample rate, channels, ecc.) |
| `Data/Json/position_json/` | Metadati posizione | JSON con coordinate polari, centroids, debug info |
| `Data/Json/merged_samples/` | Dati merged | JSON merged (audio + position) |
| `fix_dataset/convert_flac_to_csv.py` | Conversione | Wrapper per convertire FLAC → CSV |
| `fix_dataset/database_fixer.py` | Toolbox dataset | Merge, conversione, export polar, alignment check |
| `player_positions/grab_player_position.py` | Estrazione labels | Cattura minimap, estrae angolo/distanza, salva CSV |
| `model_classifier/deep_cv.py` | **Script principale ML** | Training, feature extraction, valutazione |
| `model_classifier/discretization.py` | Utilità ML | Funzioni per convertire angoli/distanze in classi |
| `model_classifier/results_*.txt` | Output training | Metriche, confusion matrices, best model |

---

## 3. Dove Inserire la Perturbazione Audio di Ubi

### 3.1 Punto di Inserimento

Il punto migliore per inserire la perturbazione è **nella funzione `evaluate()` o in uno script di test separato**, **dopo il caricamento del test set e prima delle predizioni**.

**File target**: `model_classifier/deep_cv.py`

**Funzione target**: `evaluate()` (linee 477-524) oppure creare nuova funzione `evaluate_with_perturbation()`

### 3.2 Pseudo-codice di Integrazione

```python
# In model_classifier/deep_cv.py o nuovo script di test

def evaluate_with_perturbation(model, loader, device, perturbation_config=None):
    """
    Valuta modello con opzionale perturbazione audio sul test set.
    
    Args:
        model: Modello addestrato (ResNet18MT, CRNN, o Conv1DSeparable)
        loader: DataLoader con test set
        device: torch.device
        perturbation_config: Dict con configurazione perturbazione (None = baseline)
    """
    model.eval()
    
    # Metriche baseline (senza perturbazione)
    metrics_baseline = evaluate(model, loader, device, collect_preds=False)
    
    if perturbation_config is None:
        return metrics_baseline
    
    # ===== PUNTO DI ATTACCO: PERTURBAZIONE =====
    # 1. Carica i FLAC originali corrispondenti al test set
    flac_paths_test = [get_flac_path_for_uuid(uuid) for uuid in test_uuids]
    
    # 2. Applica perturbazione agli audio FLAC
    #    (usa ADV_ML/offline_perturb.py o ADV_ML/audio_effects.py)
    from ADV_ML.offline_perturb import perturb_flac_files
    flac_paths_pert = perturb_flac_files(flac_paths_test, perturbation_config)
    
    # 3. Converti FLAC perturbati → CSV perturbati
    #    (usa fix_dataset/database_fixer.py convert-flac)
    csv_paths_pert = convert_flac_to_csv(flac_paths_pert)
    
    # 4. Ricarica dataset con audio perturbati
    test_pairs_pert = [(csv_pert, label_csv) for csv_pert, (_, label_csv) in zip(csv_paths_pert, test_pairs)]
    test_ds_pert = AudioFeatureDataset(test_pairs_pert, feature_type, feature_cfg, dist_thresholds, dist_bins)
    test_loader_pert = DataLoader(test_ds_pert, batch_size=batch_size, shuffle=False)
    
    # 5. Fai predizioni su audio perturbati
    metrics_pert, y_true_angle, y_pred_angle_pert, y_true_dist, y_pred_dist_pert = evaluate(
        model, test_loader_pert, device, collect_preds=True
    )
    
    # 6. Confronta accuracy baseline vs perturbata
    degradation = {
        "angle_acc": metrics_baseline["angle_acc"] - metrics_pert["angle_acc"],
        "dist_acc": metrics_baseline["dist_acc"] - metrics_pert["dist_acc"],
        "joint_acc": metrics_baseline["joint_acc"] - metrics_pert["joint_acc"],
        "angle_mae": metrics_pert["angle_mae"] - metrics_baseline["angle_mae"],
    }
    
    return {
        "baseline": metrics_baseline,
        "perturbed": metrics_pert,
        "degradation": degradation,
    }


# Esempio di uso nella funzione train_one_fold o in script separato:

def test_with_perturbations(model, val_pairs, perturbation_configs):
    """
    Testa modello con diverse perturbazioni.
    
    Args:
        model: Modello addestrato
        val_pairs: Lista di (audio_csv, label_csv) per test set
        perturbation_configs: Lista di dict con configurazioni perturbazione
    """
    results = []
    
    # Baseline (senza perturbazione)
    val_ds = AudioFeatureDataset(val_pairs, feature_type, feature_cfg, dist_thresholds, dist_bins)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False)
    metrics_baseline = evaluate(model, val_loader, DEVICE, collect_preds=False)
    
    # Test con ogni perturbazione
    for pert_config in perturbation_configs:
        metrics_result = evaluate_with_perturbation(
            model, val_loader, DEVICE, perturbation_config=pert_config
        )
        results.append({
            "perturbation": pert_config,
            "baseline": metrics_baseline,
            "perturbed": metrics_result["perturbed"],
            "degradation": metrics_result["degradation"],
        })
    
    return results
```

### 3.3 Note Importanti

1. **Training set intatto**: La perturbazione va applicata **SOLO** al test/validation set, mai al training set.

2. **Perturbazione su FLAC, non su CSV**: 
   - Carica i FLAC originali corrispondenti al test set
   - Applica perturbazione ai FLAC (usa `ADV_ML/offline_perturb.py`)
   - Converti FLAC perturbati → CSV perturbati
   - Ricarica dataset con CSV perturbati

3. **Feature extraction invariata**: Dopo la perturbazione, le feature (mel_ipd o raw1d) vengono estratte nello stesso modo del training.

4. **Modelli multi-task**: I 3 modelli predicono:
   - `angle_logits`: classi angolo (4 classi: n, w, s, e)
   - `dist_logits`: classi distanza (3 bins: near, medium, far)
   - `vec_pred`: vettore sin/cos per regressione angolare continua

5. **Metriche da confrontare**:
   - `angle_acc`: Accuracy classificazione angolo
   - `dist_acc`: Accuracy classificazione distanza
   - `joint_acc`: Accuracy congiunta (angolo E distanza corretti)
   - `angle_mae`: Mean Absolute Error angolare (in gradi)

---

## 4. TODO per Ubi

### Step 1: Preparare Funzione di Perturbazione
- [ ] Verificare che `ADV_ML/offline_perturb.py` possa essere importato da `COLLEAGUE_BSc_Thesis/`
- [ ] Creare wrapper che mappa UUID → path FLAC originale
- [ ] Testare perturbazione su singolo campione

### Step 2: Creare Script di Test con Perturbazione
- [ ] Creare `model_classifier/test_with_perturbations.py`
- [ ] Caricare modello addestrato (checkpoint o ri-addestrare)
- [ ] Caricare test set (val_pairs da CV fold)
- [ ] Implementare `evaluate_with_perturbation()`
- [ ] Testare con una perturbazione semplice (es. white noise)

### Step 3: Integrare con Pipeline CV
- [ ] Modificare `deep_cv.py` per salvare modelli addestrati (checkpoint)
- [ ] Dopo ogni fold, testare modello con perturbazioni
- [ ] Salvare risultati (accuracy baseline vs perturbata) in CSV/JSON

### Step 4: Test con Tutte le Perturbazioni
- [ ] Loop su tutti i tipi di perturbazione:
  - Pitch shift (light/medium/strong)
  - White noise (light/medium/strong)
  - Pink noise (light/medium/strong)
  - EQ tilt (boost/cut, light/medium/strong)
  - High-pass (150/200/250 Hz)
  - Low-pass (8000/10000/12000 Hz)
- [ ] Per ogni perturbazione, misurare:
  - Accuracy angle (baseline vs perturbata)
  - Accuracy distance (baseline vs perturbata)
  - Joint accuracy (baseline vs perturbata)
  - Angle MAE (baseline vs perturbata)

### Step 5: Analisi Risultati
- [ ] Creare script di visualizzazione:
  - Grafico: accuracy vs tipo perturbazione
  - Grafico: degradazione vs intensità perturbazione
  - Tabella: risultati per ogni modello (ResNet18MT, CRNN, Conv1DSeparable)
- [ ] Identificare perturbazioni più efficaci per degradare i modelli
- [ ] Confrontare robustezza dei 3 modelli

### Step 6: Documentazione
- [ ] Documentare risultati in formato tabellare
- [ ] Creare grafici per tesi
- [ ] Scrivere conclusioni su efficacia perturbazioni

---

## 5. File Accessori (Non Centrali per la Tesi di Ubi)

I seguenti file sono utili per il cheat del collega ma **non essenziali** per la pipeline ML e gli esperimenti di robustezza:

### 5.1 File da Potenzialmente Archiviare

| File/Cartella | Ruolo | Perché Accessorio |
|---------------|-------|-------------------|
| `game_overlay/arrow_widget.py` | Overlay PySide6 | Visualizzazione direzione predetta, non necessario per ML |
| `gathering_data/automator.py` | Orchestratore raccolta dati | Utile per raccogliere nuovi dati, non per training/test |
| `audio_loopback/record_audio.py` | Registratore audio | Utile per catturare nuovi dati, non per ML |
| `audio_loopback/reproduce_audio.py` | Riproduzione audio | Utility per QA, non necessaria per ML |
| `audio_loopback/convert_and_plot.py` | Conversione e plot | Utility per debugging, non necessaria per ML |
| `audio_loopback/flac_to_wav.py` | Conversione FLAC→WAV | Utility per QA, non necessaria per ML |
| `fix_dataset/check_uuid_alignment.py` | Verifica allineamento UUID | Utility per QA dataset, non necessaria per training |
| `Data/screenshots/` | Screenshot minimap | Debug/visualizzazione, non necessari per ML |
| `templates/red_arrow_32.png` | Template freccia | Usato da grab_player_position, non necessario per ML |

### 5.2 File Essenziali (NON Archiviare)

| File/Cartella | Ruolo | Perché Essenziale |
|---------------|-------|-------------------|
| `Data/audio/audio_loopback_flac/` | Dataset audio | **Core**: audio originali per perturbazione |
| `Data/csv/audio_loopback_csv/` | CSV audio | **Core**: input per modelli |
| `Data/csv/labels_csv/` | CSV labels | **Core**: ground truth per training/test |
| `fix_dataset/database_fixer.py` | Toolbox dataset | **Core**: conversione FLAC→CSV |
| `fix_dataset/convert_flac_to_csv.py` | Wrapper conversione | **Core**: conversione FLAC→CSV |
| `player_positions/grab_player_position.py` | Estrazione labels | **Core**: genera labels (già fatto, ma utile per validazione) |
| `model_classifier/deep_cv.py` | **Script principale ML** | **Core**: training, feature extraction, valutazione |
| `model_classifier/discretization.py` | Utilità ML | **Core**: conversione angoli/distanze in classi |

### 5.3 Cartella di Archivio

**Creare** (se non esiste):
- `COLLEAGUE_BSc_Thesis/archive_unused_for_ubi/`

**Nota**: Non spostare file automaticamente ancora. Attendere conferma dopo aver testato la pipeline completa.

---

## 6. Dettagli Tecnici Modelli

### 6.1 Architetture Modelli

**ResNet18MT**:
- Input: log-Mel + IPD/ILD (shape: `[B, C', M, T]` dove C'=24 canali, M=n_mels, T=time)
- Backbone: ResNet18-like (4 layer con residual blocks)
- Heads: 3 multi-task heads (angle class, distance class, sin/cos regression)

**CRNN**:
- Input: log-Mel + IPD/ILD (shape: `[B, C', M, T]`)
- Front-end: Conv2D (2 layer)
- Backend: BiGRU (2 layer, bidirectional)
- Heads: 3 multi-task heads

**Conv1DSeparable**:
- Input: raw waveform downsampled (shape: `[B, C, L]` dove C=8 canali, L=length)
- Layers: Depthwise-separable 1D convolutions (3 layer)
- Heads: 3 multi-task heads

### 6.2 Feature Extraction

**mel_ipd**:
- `compute_mel_ipd_ild()` in `deep_cv.py` (linee 179-255)
- Log-Mel spectrogram per ogni canale (8 canali)
- IPD (Interaural Phase Difference) relativo a canale 0
- ILD (Interaural Level Difference) relativo a canale 0
- Output: `[24, n_mels, T]` (8 Mel + 8 IPD + 8 ILD)

**raw1d**:
- `downsample_wave()` in `deep_cv.py` (linee 258-261)
- Waveform raw downsampled (es. 48kHz da 96kHz)
- Output: `[8, L]` (8 canali, L=length downsampled)

### 6.3 Loss Function

```python
loss = CE(angle_logits, angle_cls) + 
       CE(dist_logits, dist_cls) + 
       0.3 * L1(vec_pred, ang_vec) + 
       PENALTY_SCALE * angular_penalty
```

Dove:
- `CE`: Cross-Entropy
- `L1`: L1 loss per regressione sin/cos
- `angular_penalty`: Penalità basata su distanza angolare tra classi

---

## 7. Riferimenti File Chiave

| File | Path | Descrizione | Linee Chiave |
|------|------|-------------|-------------|
| Script ML principale | `model_classifier/deep_cv.py` | Training, feature extraction, valutazione | `load_pairs()` (118-153), `AudioFeatureDataset` (264-315), `evaluate()` (477-524), `train_one_fold()` (527-593) |
| Utilità discretizzazione | `model_classifier/discretization.py` | Conversione angoli/distanze in classi | `angle_deg_to_class()` (12-20), `dist_to_class()` (29-57) |
| Conversione FLAC→CSV | `fix_dataset/database_fixer.py` | Toolbox dataset (merge, convert, export) | `convert_file()` (180-211), `convert_new_flacs()` (214-258) |
| Estrazione labels | `player_positions/grab_player_position.py` | Cattura minimap, estrae angolo/distanza | `capture_minimap()` (1424-1782), `analyze_minimap_pil()` (937-1346) |

---

## 8. Note Finali

### 8.1 Stato Attuale

- ✅ Dataset audio FLAC disponibile (~970 file)
- ✅ Script di conversione FLAC → CSV disponibili
- ✅ Labels (angle, distance) disponibili in CSV
- ✅ **Codice ML presente**: `model_classifier/deep_cv.py` con 3 modelli deep learning
- ✅ Feature extraction implementata (mel_ipd, raw1d)
- ✅ Training e valutazione implementati con 9-fold CV

### 8.2 Prossimi Passi Immediati

1. **Verificare che ADV_ML sia accessibile** da COLLEAGUE_BSc_Thesis
2. **Creare script di test con perturbazione** (`test_with_perturbations.py`)
3. **Integrare perturbazione nella pipeline di valutazione**
4. **Testare con una perturbazione semplice** per validare il flusso
5. **Eseguire test completi** con tutte le perturbazioni

### 8.3 Dipendenze

Il progetto del collega richiede:
- `torch` (PyTorch)
- `librosa` (per feature Mel/IPD/ILD)
- `numpy`, `pandas`
- `scikit-learn` (per StratifiedKFold)
- `soundfile` (per lettura FLAC)

Per la perturbazione, usare:
- `ADV_ML/audio_effects.py` (effetti audio)
- `ADV_ML/offline_perturb.py` (wrapper perturbazione)

---

**Fine documento**

