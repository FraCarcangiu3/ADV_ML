#!/bin/bash
# Script per generare tutti i dataset di test perturbati
# 
# Questo script genera tutti i livelli di perturbazione definiti nella guida:
# - Pitch: P1, P2, P3
# - White Noise: W1, W2, W3
# - Pink Noise: K1, K2
# - EQ Tilt: E1, E2, E3
# - High-Pass Filter: H1, H2
# - Low-Pass Filter: L1, L2
#
# Uso:
#   chmod +x ADV_ML/generate_all_perturbations.sh
#   ./ADV_ML/generate_all_perturbations.sh
#
# Oppure esegui singoli comandi commentando gli altri

set -e  # Esci se un comando fallisce

# Configurazione
DATASET_ROOT="COLLEAGUE_BSc_Thesis/Data/audio/audio_loopback_flac"
OUTPUT_DIR="ADV_ML/output"
NUM_SAMPLES=50

# Crea la cartella output se non esiste
mkdir -p "$OUTPUT_DIR"

echo "=========================================="
echo "Generazione Dataset Perturbati"
echo "=========================================="
echo "Dataset root: $DATASET_ROOT"
echo "Output dir: $OUTPUT_DIR"
echo "Numero campioni per livello: $NUM_SAMPLES"
echo ""

# ==========================================
# PITCH SHIFT (P1, P2, P3)
# ==========================================
echo "--- Generando Pitch Shift ---"

echo "P1 - Pitch ±100 cents (leggero)..."
python ADV_ML/offline_perturb.py \
  --dataset-root "$DATASET_ROOT" \
  --perturbation pitch \
  --mode random \
  --min-cents -100 \
  --max-cents 100 \
  --num-samples "$NUM_SAMPLES" \
  --output-csv "$OUTPUT_DIR/pistol_pitch_P1_light.csv" \
  --verbose

echo "P2 - Pitch ±150 cents (medio)..."
python ADV_ML/offline_perturb.py \
  --dataset-root "$DATASET_ROOT" \
  --perturbation pitch \
  --mode random \
  --min-cents -150 \
  --max-cents 150 \
  --num-samples "$NUM_SAMPLES" \
  --output-csv "$OUTPUT_DIR/pistol_pitch_P2_medium.csv" \
  --verbose

echo "P3 - Pitch ±200 cents (forte)..."
python ADV_ML/offline_perturb.py \
  --dataset-root "$DATASET_ROOT" \
  --perturbation pitch \
  --mode random \
  --min-cents -200 \
  --max-cents 200 \
  --num-samples "$NUM_SAMPLES" \
  --output-csv "$OUTPUT_DIR/pistol_pitch_P3_strong.csv" \
  --verbose

# ==========================================
# WHITE NOISE (W1, W2, W3)
# ==========================================
echo ""
echo "--- Generando White Noise ---"

echo "W1 - White Noise [35-38] dB (leggero)..."
python ADV_ML/offline_perturb.py \
  --dataset-root "$DATASET_ROOT" \
  --perturbation white_noise \
  --mode random \
  --min-snr 35 \
  --max-snr 38 \
  --num-samples "$NUM_SAMPLES" \
  --output-csv "$OUTPUT_DIR/pistol_noiseW_W1_light.csv" \
  --verbose

echo "W2 - White Noise [38-42] dB (medio)..."
python ADV_ML/offline_perturb.py \
  --dataset-root "$DATASET_ROOT" \
  --perturbation white_noise \
  --mode random \
  --min-snr 38 \
  --max-snr 42 \
  --num-samples "$NUM_SAMPLES" \
  --output-csv "$OUTPUT_DIR/pistol_noiseW_W2_medium.csv" \
  --verbose

echo "W3 - White Noise [42-45] dB (forte)..."
python ADV_ML/offline_perturb.py \
  --dataset-root "$DATASET_ROOT" \
  --perturbation white_noise \
  --mode random \
  --min-snr 42 \
  --max-snr 45 \
  --num-samples "$NUM_SAMPLES" \
  --output-csv "$OUTPUT_DIR/pistol_noiseW_W3_strong.csv" \
  --verbose

# ==========================================
# PINK NOISE (K1, K2)
# ==========================================
echo ""
echo "--- Generando Pink Noise ---"

echo "K1 - Pink Noise [16-20] dB (leggero)..."
python ADV_ML/offline_perturb.py \
  --dataset-root "$DATASET_ROOT" \
  --perturbation pink_noise \
  --mode random \
  --min-snr 16 \
  --max-snr 20 \
  --num-samples "$NUM_SAMPLES" \
  --output-csv "$OUTPUT_DIR/pistol_noiseK_K1_light.csv" \
  --verbose

echo "K2 - Pink Noise [20-24] dB (forte)..."
python ADV_ML/offline_perturb.py \
  --dataset-root "$DATASET_ROOT" \
  --perturbation pink_noise \
  --mode random \
  --min-snr 20 \
  --max-snr 24 \
  --num-samples "$NUM_SAMPLES" \
  --output-csv "$OUTPUT_DIR/pistol_noiseK_K2_strong.csv" \
  --verbose

# ==========================================
# EQ TILT (E1, E2, E3)
# ==========================================
echo ""
echo "--- Generando EQ Tilt ---"

echo "E1 - EQ Tilt leggero [-6, -4] dB cut o [3, 4] dB boost..."
python ADV_ML/offline_perturb.py \
  --dataset-root "$DATASET_ROOT" \
  --perturbation eq_tilt \
  --mode random \
  --cut-min -6 \
  --cut-max -4 \
  --boost-min 3 \
  --boost-max 4 \
  --num-samples "$NUM_SAMPLES" \
  --output-csv "$OUTPUT_DIR/pistol_eqtilt_E1_light.csv" \
  --verbose

echo "E2 - EQ Tilt medio [-4, -3] dB cut o [4, 5] dB boost..."
python ADV_ML/offline_perturb.py \
  --dataset-root "$DATASET_ROOT" \
  --perturbation eq_tilt \
  --mode random \
  --cut-min -4 \
  --cut-max -3 \
  --boost-min 4 \
  --boost-max 5 \
  --num-samples "$NUM_SAMPLES" \
  --output-csv "$OUTPUT_DIR/pistol_eqtilt_E2_medium.csv" \
  --verbose

echo "E3 - EQ Tilt forte [-5, -3] dB cut o [5, 6] dB boost..."
python ADV_ML/offline_perturb.py \
  --dataset-root "$DATASET_ROOT" \
  --perturbation eq_tilt \
  --mode random \
  --cut-min -5 \
  --cut-max -3 \
  --boost-min 5 \
  --boost-max 6 \
  --num-samples "$NUM_SAMPLES" \
  --output-csv "$OUTPUT_DIR/pistol_eqtilt_E3_strong.csv" \
  --verbose

# ==========================================
# HIGH-PASS FILTER (H1, H2)
# ==========================================
echo ""
echo "--- Generando High-Pass Filter ---"

echo "H1 - High-Pass [150, 200] Hz (leggero)..."
python ADV_ML/offline_perturb.py \
  --dataset-root "$DATASET_ROOT" \
  --perturbation highpass \
  --mode random \
  --min-hz 150 \
  --max-hz 200 \
  --num-samples "$NUM_SAMPLES" \
  --output-csv "$OUTPUT_DIR/pistol_hp_H1_light.csv" \
  --verbose

echo "H2 - High-Pass [200, 250] Hz (forte)..."
python ADV_ML/offline_perturb.py \
  --dataset-root "$DATASET_ROOT" \
  --perturbation highpass \
  --mode random \
  --min-hz 200 \
  --max-hz 250 \
  --num-samples "$NUM_SAMPLES" \
  --output-csv "$OUTPUT_DIR/pistol_hp_H2_strong.csv" \
  --verbose

# ==========================================
# LOW-PASS FILTER (L1, L2)
# ==========================================
echo ""
echo "--- Generando Low-Pass Filter ---"

echo "L1 - Low-Pass [8000, 9000] Hz (leggero)..."
python ADV_ML/offline_perturb.py \
  --dataset-root "$DATASET_ROOT" \
  --perturbation lowpass \
  --mode random \
  --min-hz 8000 \
  --max-hz 9000 \
  --num-samples "$NUM_SAMPLES" \
  --output-csv "$OUTPUT_DIR/pistol_lp_L1_light.csv" \
  --verbose

echo "L2 - Low-Pass [9000, 10000] Hz (forte)..."
python ADV_ML/offline_perturb.py \
  --dataset-root "$DATASET_ROOT" \
  --perturbation lowpass \
  --mode random \
  --min-hz 9000 \
  --max-hz 10000 \
  --num-samples "$NUM_SAMPLES" \
  --output-csv "$OUTPUT_DIR/pistol_lp_L2_strong.csv" \
  --verbose

# ==========================================
# RIEPILOGO
# ==========================================
echo ""
echo "=========================================="
echo "Generazione completata!"
echo "=========================================="
echo ""
echo "File generati in: $OUTPUT_DIR"
echo ""
echo "Lista file generati:"
ls -lh "$OUTPUT_DIR"/pistol_*.csv 2>/dev/null || echo "Nessun file trovato"
echo ""
echo "Totale file CSV:"
ls -1 "$OUTPUT_DIR"/pistol_*.csv 2>/dev/null | wc -l || echo "0"
echo ""





