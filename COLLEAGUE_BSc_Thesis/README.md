# BSc_Thesis — Audio-Driven Direction Assistant for AssaultCube

## Overview
This repository captures synchronized audio + minimap labels, cleans the dataset, and trains deep multi-task models that predict shooter angle and relative distance from 8-channel 96 kHz audio. It also provides a PySide6 overlay to display the inferred direction.

## Architecture by Component
- **gathering_data/automator.py** — Orchestrator; listens to clicks, generates UUIDs, sends UDP `SHOT|<uuid>` to the recorder, enqueues minimap capture, auto-presses `r` every 8 clicks to diversify the dataset, monitors backlog.
- **audio_loopback/record_audio.py** — 8‑ch/96 kHz recorder; 0.5 s pre-buffer + 1.4 s post-trigger; writes `audio_event_<uuid>.flac` and metadata `flac_metadata_<uuid>.json`.
- **player_positions/grab_player_position.py** — macOS Quartz/AppKit minimap extractor; crops the minimap, isolates red/green arrows with HSV + morphology, template matching (72 rotations @5°), smoothing/hysteresis, bins angles (macro/micro) and distances (macro/micro), enforces caps; outputs `position_<uuid>.json`, `labels_<uuid>.csv`, minimap PNGs/debug, updates `all_labels.csv`.
- **fix_dataset/database_fixer.py** — Incremental toolbox: merges `position_*` + `flac_metadata_*` into `merged_<uuid>.json`, optional +180° angle normalization, converts FLAC→CSV/WAV, prunes zero-only audio CSVs, alignment helpers.
- **model_classifier/deep_cv.py** — Deep multi-task trainer (ResNet18-like, CRNN, Conv1D separable) on log-Mel+IPD/ILD or raw waveform; 9-fold CV with early stopping, angle-penalty, confusion matrices; logs results to `results_<timestamp>.txt`.
- **game_overlay/arrow_widget.py** — PySide6 fullscreen overlay with 8 translucent arrows to visualize inferred direction.
- **Audio QA utilities** — `flac_to_wav.py`, `reproduce_audio.py`, `convert_and_plot.py` for conversion, playback, and quick inspection.

## Data Layout (after capture)
- `Data/audio/audio_loopback_flac/`: `audio_event_<uuid>.flac` (+ optional WAV).
- `Data/Json/flac_json/`: `flac_metadata_<uuid>.json`.
- `Data/Json/position_json/`: `position_<uuid>.json`.
- `Data/Json/merged_samples/`: `merged_<uuid>.json` (+ optional `merged_fixed_<uuid>.json` if angle-normalized).
- `Data/csv/audio_loopback_csv/`: `audio_event_<uuid>.csv` (audio matrix).
- `Data/csv/labels_csv/`: `labels_<uuid>.csv` (centroids/angle/distance bins) + `all_labels.csv`.
- `Data/csv/merged_samples_csv/`: optional polar CSVs from `export-polar`.
- `Data/screenshots/`: minimap PNG + debug masks.

## Quick Setup
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```
On macOS, grant Screen Recording, Accessibility, and Input Monitoring to your terminal/IDE.

## Key Commands
- Full capture loop: `python gathering_data/automator.py`
- Recorder only: `python audio_loopback/record_audio.py`
- Single minimap grab: `python player_positions/grab_player_position.py --uuid demo`
- Data pipeline: `python fix_dataset/database_fixer.py incremental`
- Deep trainer (use all cores):  
  `CLASSIFIER_LOAD_WORKERS=$(nproc) OMP_NUM_THREADS=$(nproc) MKL_NUM_THREADS=$(nproc) python model_classifier/deep_cv.py`
- Override specific files in trainer:  
  `CLASSIFIER_AUDIO_FILE=path/to/audio.csv CLASSIFIER_LABEL_FILE=path/to/labels.csv python model_classifier/deep_cv.py`

## Operational Notes
- Filenames embed UUIDs for deterministic pairing.
- Label CSVs accepted as `<uuid>.csv` or `labels_<uuid>.csv`; the trainer detects both.
- Explicit file overrides via env vars are supported (see above).
- Detailed logs and confusion matrices are written to `model_classifier/results_<timestamp>.txt`.

## Dependencies (core)
- Audio/CV: `soundfile`, `soundcard`, `opencv-python`, `Pillow`, `pyobjc` (macOS).
- GUI: `PySide6`.
- ML: `torch`, `librosa`, `numpy`, `pandas`.

## Anti-Overfitting Measures
- 9-fold stratified CV (angle×distance).
- Early stopping and LR reduction on plateau in deep models.
- Angular penalty for large direction errors.
- Per-fold normalization; confusion matrices for diagnostics.
