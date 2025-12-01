# BSc_Thesis — Detailed Technical Report

> Goal: build an audio-driven assistant for AssaultCube that infers shooter angle and relative distance from 8‑channel 96 kHz audio and renders the direction on an overlay.  
> This document, written as a thesis-style report, explains every file, setting, and safeguard in the codebase.

## 1. End-to-End Flow
1. **Event orchestration** (`gathering_data/automator.py`)  
   - Listens to left clicks (200 ms debounce) and generates a UUID per event.  
   - Sends `SHOT|<uuid>` via UDP to the recorder.  
   - Enqueues the UUID for the minimap capture worker.  
   - Auto-presses `r` every 8 clicks to reset the in-game scenario and diversify samples.  
   - Monitors queue depth to avoid backlog; optionally drops if overloaded.
2. **Audio capture** (`audio_loopback/record_audio.py`)  
   - Maintains a 0.5 s rolling pre-buffer; records 1.4 s post-trigger.  
   - 8 channels @ 96 kHz; normalizes to PCM16.  
   - Outputs `Data/audio/audio_loopback_flac/audio_event_<uuid>.flac`; metadata in `Data/Json/flac_json/flac_metadata_<uuid>.json` (codec, sample rate, channels, paths).
3. **Minimap extraction** (`player_positions/grab_player_position.py`, macOS Quartz/AppKit)  
   - Finds the `assaultcube` window and optionally brings it to foreground.  
   - Crops minimap (11% width, 16% height, top-right offset).  
   - Uses HSV masks for red/green arrows, morphology, small-component suppression, circle constraint.  
   - Template matching over 72 rotations (5° step) to stabilize heading; fallback atan2 on arrow tip.  
   - Temporal smoothing (centroids/angles), hysteresis, distance clamps.  
   - Binning: angle macro/micro (4×3) and distance macro/micro (3×3, range 5–75 px).  
   - Dataset caps: per distance macro, per angle micro, per combination, and total (~972 by default).  
   - Outputs `position_<uuid>.json`, `Data/csv/labels_csv/labels_<uuid>.csv` (centroids + angle/distance bins), minimap PNGs + debug masks (if `DEBUG_SAVE=True`), and appends to `Data/csv/merged_samples_csv/all_labels.csv`.
4. **Dataset maintenance** (`fix_dataset/database_fixer.py`)  
   - Merge: aligns `flac_metadata_<uuid>.json` with `position_<uuid>.json` into `Data/Json/merged_samples/merged_<uuid>.json`.  
   - Angle normalization: optional +180° shift to `merged_fixed_<uuid>.json` (`fix-angles`).  
   - Conversion: FLAC→CSV (float32) and optional WAV; filters to new IDs; supports export-all or name filters.  
   - Cleanup: removes zero-only audio CSVs and corresponding merged files.  
   - Alignment helpers (disabled by default in incremental) for audio CSV vs label CSV.  
   - `incremental`: merge → FLAC→CSV → zero-only prune (interactive, new IDs only).
5. **Model training** (`model_classifier/deep_cv.py`)  
   - Loads paired audio CSV (`Data/csv/audio_loopback_csv/audio_event_<uuid>.csv`) and label CSV (`Data/csv/labels_csv/<uuid>.csv` or `labels_<uuid>.csv`). Explicit overrides via env `CLASSIFIER_AUDIO_FILE` / `CLASSIFIER_LABEL_FILE`.  
   - Features: log-Mel + IPD/ILD (configurable `n_mels`) or raw 1D waveform (downsampled) for Conv1D.  
   - Models: ResNet18-like, CRNN (Conv2D + BiGRU), Conv1D separable; multi-task heads (angle class, distance class, sin/cos regression).  
   - Loss: CE for angle + CE for distance + 0.3·L1(sin/cos) + angular penalty scaled by `CLASSIFIER_ANGLE_PENALTY`.  
   - CV: 9-fold stratified (angle×distance), early stopping, ReduceLROnPlateau.  
   - Runtime: uses all CPU cores (`torch.set_num_threads`, DataLoader `num_workers=os.cpu_count`, `pin_memory=True`, `cudnn.benchmark=True`).  
   - Output: confusion matrices (angle, distance), per-fold and mean metrics, logged to `model_classifier/results_<timestamp>.txt`.
6. **Overlay** (`game_overlay/arrow_widget.py`)  
   - PySide6 fullscreen black window with eight translucent arrows; methods to show/hide arrows for manual tests or inference integration.

## 2. Data Layout and Formats
- `Data/audio/audio_loopback_flac/audio_event_<uuid>.flac` — 8‑ch 96 kHz clip (~1.9 s).  
- `Data/Json/flac_json/flac_metadata_<uuid>.json` — audio metadata (codec, sr, channels, paths).  
- `Data/Json/position_json/position_<uuid>.json` — polar labels, centroids, debug info.  
- `Data/Json/merged_samples/merged_<uuid>.json` — merged audio+position; optional `merged_fixed_<uuid>.json` after angle normalization.  
- `Data/csv/audio_loopback_csv/audio_event_<uuid>.csv` — audio matrix (float).  
- `Data/csv/labels_csv/labels_<uuid>.csv` — centroids + angle/distance bins; aggregate `all_labels.csv`.  
- `Data/csv/merged_samples_csv/<uuid>.csv` — optional polar CSV from `export-polar`.  
- `Data/screenshots/` — minimap PNG + debug masks.

## 3. Key Parameters by File
- **gathering_data/automator.py**: debounce 200 ms; auto `r` every 8 clicks; UDP `SHOT|<uuid>` to 127.0.0.1:9999 (fallback 10000); queue bounds; dataset balance read from `labels_csv`.  
- **audio_loopback/record_audio.py**: `PRE_SECONDS=0.5`, `POST_SECONDS=1.4`, `SAMPLERATE=96000`, `CHANNELS=8`; device name “Black” (update if needed); writes FLAC + metadata; optional WAV.  
- **player_positions/grab_player_position.py**: minimap crop 11%×16%; HSV red [(0,80,80)-(10,255,255)] and [(170,80,80)-(179,255,255)], green [(35,60,60)-(90,255,255)]; template 5° step; smoothing centroids/angles; binning 4×3 angles, 3×3 distances (5–75 px); caps per combo and total; outputs CSV/PNG/JSON; env overrides (`MINIMAP_UPSCALE`, `PLAYER_ANGLE_OFFSET`, etc.).  
- **fix_dataset/database_fixer.py**: defaults under `Data/...`; `incremental` does merge (new IDs), FLAC→CSV/WAV, zero-prune; optional delete extras; `fix-angles` shifts +180°; `convert-flac` supports export-all or name filters; `export-polar` writes `angle_deg,distance_rel` from `merged_fixed_*`.  
- **model_classifier/deep_cv.py**: envs `CLASSIFIER_FOLDS` (default 9), `CLASSIFIER_DIST_BINS` (2/3), `CLASSIFIER_ANGLE_PENALTY`, `CLASSIFIER_LOAD_WORKERS`, `CLASSIFIER_MAX_FILES`, `CLASSIFIER_AUDIO_FILE`, `CLASSIFIER_LABEL_FILE`; runtime set to max CPU threads, `cudnn.benchmark=True`; DataLoader with many workers and `pin_memory`.  
- **game_overlay/arrow_widget.py**: fullscreen window, 8 triangular widgets; show/hide controls; process title via `setproctitle`.

## 4. Design Choices and Safeguards
- **Synchronization**: UUID ties audio and minimap; debounce and periodic reset encourage diverse captures.  
- **Label quality**: template matching + hysteresis reduce jitter; distance jump clamp; dataset caps prevent class imbalance.  
- **Data hygiene**: zero-only audio CSV pruning removes paired merged files; file existence checks throughout.  
- **Robust loading**: trainer accepts `<uuid>.csv` or `labels_<uuid>.csv`, parses numeric columns by name or first numeric fallback.  
- **Anti-overfitting**: 9-fold stratified CV, early stopping, LR reduction, angular penalty, per-fold normalization, confusion matrices for diagnostics.  
- **Performance**: max CPU threads, DataLoader workers = cores, `pin_memory`, `cudnn.benchmark`; logging of batches/workers and per-model summaries. AMP can be added to speed up GPU runs.

## 5. Commands and Recipes
- Full capture: `python gathering_data/automator.py`  
- Recorder only: `python audio_loopback/record_audio.py`  
- Single minimap: `python player_positions/grab_player_position.py --uuid demo`  
- Data pipeline: `python fix_dataset/database_fixer.py incremental`  
- Deep trainer (max cores):  
  `CLASSIFIER_LOAD_WORKERS=$(nproc) OMP_NUM_THREADS=$(nproc) MKL_NUM_THREADS=$(nproc) python model_classifier/deep_cv.py`  
- Override specific files for the trainer:  
  `CLASSIFIER_AUDIO_FILE=path/to/audio.csv CLASSIFIER_LABEL_FILE=path/to/labels.csv python model_classifier/deep_cv.py`

## 6. Trainer Outputs
- Per-fold logs: joint/angle/dist accuracy, angular MAE.  
- Confusion matrices (angle, distance) aggregated across folds.  
- `model_classifier/results_<timestamp>.txt` with metrics for all configs, durations, confusion matrices, and best model.

## 7. Risks and Notes
- **Missing data**: `Data/` is empty until you capture; many routines will error if expected files are absent.  
- **Hardware binding**: recorder assumes device “Black”; adjust `mic_name` as needed.  
- **macOS requirements**: Quartz/AppKit need Screen Recording/Accessibility/Input Monitoring permissions.  
- **Dataset imbalance**: caps in `grab_player_position.py` limit over-collection; review thresholds for new sessions.  
- **I/O performance**: prefer SSD for FLAC/CSV; raise `CLASSIFIER_LOAD_WORKERS` carefully.  
- **Compatibility**: some torch versions don’t accept `verbose` on ReduceLROnPlateau (already removed); `librosa` required for Mel features.

## 8. Possible Extensions
- Add AMP for FP16 speedup on GPU.  
- Export best-model checkpoints for runtime inference with the overlay.  
- Real-time inference script to publish direction via IPC to the overlay.  
- Richer audio augmentation (time-shift, per-channel gain) and class balancing.  
- Structured logs (CSV/JSON) for multi-run comparisons.
