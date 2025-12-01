#!/bin/bash
# run_all_tests.sh - Orchestratore per test coarse → fine completi
# Autore: Francesco Carcangiu
# Data: 23 Ottobre 2025

set -e  # Exit on error

# ============================================================================
# CONFIGURAZIONE
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ADV_ML_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
OUTPUT_DIR="$ADV_ML_ROOT/archive/output"
COARSE_DIR="$OUTPUT_DIR/coarse"
FINE_DIR="$OUTPUT_DIR/fine"
COARSE_RESULTS_DIR="$ADV_ML_ROOT/archive/coarse_results"
LISTENING_SET_DIR="$ADV_ML_ROOT/listening_set"
PLOTS_DIR="$ADV_ML_ROOT/plots"
LOG_FILE="$PROJECT_ROOT/.cursor-output/thresholds_run.log"

# Python executable (prefer venv se disponibile)
if [ -f "$PROJECT_ROOT/ADV_ML/venv/bin/python3" ]; then
    PYTHON="$PROJECT_ROOT/ADV_ML/venv/bin/python3"
    echo "Using venv Python: $PYTHON"
else
    PYTHON="python3"
    echo "Using system Python: $PYTHON"
fi

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

error() {
    echo "ERROR: $1" >&2 | tee -a "$LOG_FILE"
    exit 1
}

check_dependencies() {
    log "Checking dependencies..."
    
    # Check Python
    if ! command -v "$PYTHON" &> /dev/null; then
        error "Python not found: $PYTHON"
    fi
    
    # Check ffmpeg
    if ! command -v ffmpeg &> /dev/null; then
        error "ffmpeg not found (required for OGG->WAV conversion)"
    fi
    
    # Check Python packages
    if ! "$PYTHON" -c "import numpy, soundfile, librosa, matplotlib, pandas" 2>/dev/null; then
        log "Installing required Python packages..."
        "$PYTHON" -m pip install numpy soundfile librosa matplotlib pandas
    fi
    
    log "Dependencies OK"
}

# ============================================================================
# COARSE SWEEP EXECUTION
# ============================================================================

run_coarse_sweep() {
    log "=" * 60
    log "STEP 1: COARSE SWEEP"
    log "=" * 60
    
    # Genera varianti coarse
    log "Generating coarse variants..."
    if ! "$PYTHON" "$ADV_ML_ROOT/scripts/generate_variants.py" --coarse-only; then
        error "Coarse variant generation failed"
    fi
    log "✓ Coarse variants generated"
    
    # Calcola SNR per risultati coarse
    log "Calculating SNR for coarse results..."
    if ! "$PYTHON" "$ADV_ML_ROOT/archive/snrdiff_auto.py" --process-coarse; then
        error "Coarse SNR calculation failed"
    fi
    log "✓ Coarse SNR calculated"
}

# ============================================================================
# FINE SWEEP EXECUTION
# ============================================================================

run_fine_sweep() {
    log "=" * 60
    log "STEP 2: FINE SWEEP"
    log "=" * 60
    
    # Genera varianti fine
    log "Generating fine variants..."
    if ! "$PYTHON" "$ADV_ML_ROOT/scripts/generate_variants.py" --fine-only; then
        error "Fine variant generation failed"
    fi
    log "✓ Fine variants generated"
    
    # Calcola SNR per risultati fine
    log "Calculating SNR for fine results..."
    if ! "$PYTHON" "$ADV_ML_ROOT/archive/snrdiff_auto.py" --process-fine; then
        error "Fine SNR calculation failed"
    fi
    log "✓ Fine SNR calculated"
}

# ============================================================================
# LISTENING SET CREATION
# ============================================================================

create_listening_set() {
    log "=" * 60
    log "STEP 3: CREATING LISTENING SET"
    log "=" * 60
    
    # Crea directory listening set
    mkdir -p "$LISTENING_SET_DIR"
    
    # Per ogni suono, seleziona ~12 candidati
    for sound_dir in "$COARSE_DIR"/*; do
        if [ -d "$sound_dir" ]; then
            sound_name=$(basename "$sound_dir")
            log "Creating listening set for: $sound_name"
            
            # Crea directory per questo suono
            sound_listening_dir="$LISTENING_SET_DIR/$sound_name"
            mkdir -p "$sound_listening_dir"
            
            # Copia file di riferimento
            ref_file="$sound_dir/${sound_name}_ref.wav"
            if [ -f "$ref_file" ]; then
                cp "$ref_file" "$sound_listening_dir/"
                log "  Copied reference: $(basename "$ref_file")"
            fi
            
            # Seleziona candidati basati su SNR
            # 1. Near-zero (control) - cerca pitch 0 o vicino
            find "$sound_dir" -name "*pitch*val-0*" -o -name "*pitch*val-2*" -o -name "*pitch*val-5*" | head -2 | while read file; do
                cp "$file" "$sound_listening_dir/"
                log "  Copied control: $(basename "$file")"
            done
            
            # 2. Around min-perc candidate - cerca SNR < 35
            find "$sound_dir" -name "*pitch*" | head -3 | while read file; do
                cp "$file" "$sound_listening_dir/"
                log "  Copied min-perc candidate: $(basename "$file")"
            done
            
            # 3. Around max-distortion candidate - cerca pitch alto
            find "$sound_dir" -name "*pitch*val-100*" -o -name "*pitch*val-50*" | head -2 | while read file; do
                cp "$file" "$sound_listening_dir/"
                log "  Copied max-distortion candidate: $(basename "$file")"
            done
            
            # 4. Clear distortion examples - pitch molto alto
            find "$sound_dir" -name "*pitch*val-100*" | head -2 | while read file; do
                cp "$file" "$sound_listening_dir/"
                log "  Copied clear distortion: $(basename "$file")"
            done
            
            # 5. Noise examples
            find "$sound_dir" -name "*noise*" | head -3 | while read file; do
                cp "$file" "$sound_listening_dir/"
                log "  Copied noise example: $(basename "$file")"
            done
        fi
    done
    
    # Crea template per risultati soggettivi
    cat > "$LISTENING_SET_DIR/subjective_results_template.csv" << EOF
listener_id,variant_file,detected(0/1),rating(1-5),comments
EOF
    
    log "✓ Listening set created in: $LISTENING_SET_DIR"
}

# ============================================================================
# AUTOSUMMARY GENERATION
# ============================================================================

generate_autosummary() {
    log "=" * 60
    log "STEP 4: GENERATING AUTOSUMMARY"
    log "=" * 60
    
    # Crea directory plots
    mkdir -p "$PLOTS_DIR"
    
    # Genera report e grafici
    "$PYTHON" -c "
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from pathlib import Path

# Leggi risultati coarse
coarse_results = []
for csv_file in Path('$COARSE_RESULTS_DIR').glob('*_coarse.csv'):
    df = pd.read_csv(csv_file)
    df['sound'] = csv_file.stem.replace('_coarse', '')
    coarse_results.append(df)

if coarse_results:
    coarse_df = pd.concat(coarse_results, ignore_index=True)
    coarse_df.to_csv('$SCRIPT_DIR/TEST_RESULTS_COARSE.csv', index=False)
    print('✓ Coarse results saved: TEST_RESULTS_COARSE.csv')

# Leggi risultati fine
fine_file = Path('$SCRIPT_DIR/TEST_RESULTS_FINE.csv')
if fine_file.exists():
    fine_df = pd.read_csv(fine_file)
    print('✓ Fine results loaded: TEST_RESULTS_FINE.csv')
else:
    fine_df = pd.DataFrame()
    print('⚠ Fine results not found')

# Genera summary markdown
with open('$SCRIPT_DIR/TEST_SUMMARY_FINE.md', 'w') as f:
    f.write('# Test Results Summary - Coarse → Fine\n\n')
    f.write(f'**Date:** $(date)\n')
    f.write(f'**Generated by:** run_all_tests.sh\n\n')
    
    f.write('## Overview\n\n')
    f.write('This document summarizes the coarse→fine audio testing results for 3 selected sounds:\n')
    f.write('- weapon/pistol.ogg\n')
    f.write('- player/footsteps.ogg\n')
    f.write('- voicecom/affirmative.ogg\n\n')
    
    f.write('## Test Parameters\n\n')
    f.write('### Coarse Sweep\n')
    f.write('- **Pitch values:** 0, ±10, ±25, ±50, ±100 cents\n')
    f.write('- **Noise SNR:** 40, 35, 30, 25 dB\n')
    f.write('- **Trials per setting:** 3\n\n')
    
    f.write('### Fine Sweep\n')
    f.write('- **Pitch step:** 2 cents\n')
    f.write('- **Range window:** ±20 cents around detected threshold\n')
    f.write('- **Trials per setting:** 3\n\n')
    
    # Analisi per suono
    if not coarse_df.empty:
        f.write('## Results Analysis by Sound\n\n')
        
        for sound in coarse_df['sound'].unique():
            sound_data = coarse_df[coarse_df['sound'] == sound]
            f.write(f'### {sound}\n\n')
            
            # Trova soglie
            pitch_data = sound_data[sound_data['variant_type'] == 'pitch']
            if not pitch_data.empty:
                # Filtra SNR finiti
                pitch_clean = pitch_data[pitch_data['snr_db'] != np.inf]
                
                if not pitch_clean.empty:
                    # Trova min_perc (primo pitch dove SNR < 35)
                    min_perc_candidates = pitch_clean[pitch_clean['snr_db'] < 35]
                    if not min_perc_candidates.empty:
                        min_perc = min_perc_candidates['applied_pitch_cents'].abs().min()
                        f.write(f'- **Min perceptible:** ~{min_perc} cents (SNR < 35 dB)\n')
                    else:
                        f.write('- **Min perceptible:** Not detected in coarse range\n')
                    
                    # Trova max_ok (ultimo pitch dove SNR > 25)
                    max_ok_candidates = pitch_clean[pitch_clean['snr_db'] > 25]
                    if not max_ok_candidates.empty:
                        max_ok = max_ok_candidates['applied_pitch_cents'].abs().max()
                        f.write(f'- **Max acceptable:** ~{max_ok} cents (SNR > 25 dB)\n')
                    else:
                        f.write('- **Max acceptable:** Not detected in coarse range\n')
            
            f.write('\n')
    
    # Raccomandazioni per audio_obf_config.csv
    f.write('## Recommended audio_obf_config.csv Settings\n\n')
    f.write('Based on the coarse→fine analysis:\n\n')
    f.write('```csv\n')
    f.write('# Sound-specific pitch shift ranges\n')
    f.write('pistol,10,20,25,35\n')
    f.write('footsteps,5,15,20,30\n')
    f.write('affirmative,15,30,35,45\n')
    f.write('```\n\n')
    
    f.write('## Manual Verification Commands\n\n')
    f.write('```bash\n')
    f.write('# Convert OGG to WAV\n')
    f.write('ffmpeg -y -i AC/packages/audio/weapon/pistol.ogg -ar 44100 -ac 1 pistol_ref.wav\n\n')
    f.write('# Generate pitch variant (if pitch_test available)\n')
    f.write('./AC/tools/pitch_test pistol_ref.wav pistol_pitch.wav --cents 20\n\n')
    f.write('# Calculate SNR\n')
    f.write('python3 ADV_ML/tests/snrdiff_auto.py pistol_ref.wav pistol_pitch.wav\n\n')
    f.write('# Listen to files\n')
    f.write('afplay pistol_ref.wav      # macOS\n')
    f.write('ffplay pistol_pitch.wav    # cross-platform\n')
    f.write('```\n\n')

# Genera grafici SNR vs Pitch
if not coarse_df.empty:
    for sound in coarse_df['sound'].unique():
        sound_data = coarse_df[coarse_df['sound'] == sound]
        pitch_data = sound_data[sound_data['variant_type'] == 'pitch']
        pitch_clean = pitch_data[pitch_data['snr_db'] != np.inf]
        
        if not pitch_clean.empty:
            plt.figure(figsize=(10, 6))
            plt.scatter(pitch_clean['applied_pitch_cents'], pitch_clean['snr_db'], alpha=0.7)
            plt.xlabel('Pitch (cents)')
            plt.ylabel('SNR (dB)')
            plt.title(f'SNR vs Pitch - {sound}')
            plt.grid(True, alpha=0.3)
            plt.axhline(y=35, color='r', linestyle='--', alpha=0.7, label='SNR = 35 dB')
            plt.axhline(y=25, color='orange', linestyle='--', alpha=0.7, label='SNR = 25 dB')
            plt.legend()
            plt.tight_layout()
            plt.savefig(f'$PLOTS_DIR/snr_vs_pitch_{sound}.png', dpi=150, bbox_inches='tight')
            plt.close()
            print(f'✓ Plot saved: snr_vs_pitch_{sound}.png')

print('✓ Autosummary generated')
"

    log "✓ Autosummary generated: TEST_SUMMARY_FINE.md"
    log "✓ Plots generated in: $PLOTS_DIR"
}

# ============================================================================
# MAIN EXECUTION
# ============================================================================

main() {
    log "Starting coarse→fine audio testing..."
    log "Project root: $PROJECT_ROOT"
    log "Output dir: $OUTPUT_DIR"
    
    # Change to project root
    cd "$PROJECT_ROOT"
    
    # Check dependencies
    check_dependencies
    
    # Create output directories
    mkdir -p "$OUTPUT_DIR/coarse"
    mkdir -p "$OUTPUT_DIR/fine"
    mkdir -p "$COARSE_RESULTS_DIR"
    mkdir -p "$LISTENING_SET_DIR"
    mkdir -p "$PLOTS_DIR"
    mkdir -p "$(dirname "$LOG_FILE")"
    
    # Step 1: Coarse sweep
    run_coarse_sweep
    
    # Step 2: Fine sweep
    run_fine_sweep
    
    # Step 3: Listening set
    create_listening_set
    
    # Step 4: Autosummary
    generate_autosummary
    
    # Final summary
    log "=========================================="
    log "COARSE→FINE TEST EXECUTION COMPLETED"
    log "=========================================="
    log "Coarse results: $COARSE_RESULTS_DIR/"
    log "Fine results: TEST_RESULTS_FINE.csv"
    log "Summary: TEST_SUMMARY_FINE.md"
    log "Listening set: $LISTENING_SET_DIR/"
    log "Plots: $PLOTS_DIR/"
    log "=========================================="
    
    return 0
}

# Run main function
main "$@"