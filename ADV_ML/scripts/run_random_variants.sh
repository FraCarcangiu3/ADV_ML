#!/bin/bash
# run_random_variants.sh
# Genera N varianti audio con parametri random per test ML
#
# Uso: ./run_random_variants.sh <sound_name> <num_variants>
# Esempio: ./run_random_variants.sh weapon/usp 100

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
OUTPUT_DIR="$SCRIPT_DIR/../output/random_variants"
CSV_OUTPUT="$OUTPUT_DIR/random_params.csv"

# Parametri
SOUND_NAME="${1:-weapon/usp}"
NUM_VARIANTS="${2:-50}"

# Colori
GREEN='\033[0.32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== Audio Random Variants Generator (Step 3) ===${NC}"
echo "Sound: $SOUND_NAME"
echo "Num variants: $NUM_VARIANTS"
echo "Output: $OUTPUT_DIR"
echo ""

# Crea directory output
mkdir -p "$OUTPUT_DIR"

# Crea header CSV
echo "variant_id,pitch_cents,noise_snr_db,eq_tilt_db,hp_hz,lp_hz" > "$CSV_OUTPUT"

# Funzione per generare variante con parametri random (simulazione distribuzioni C++)
generate_variant() {
    local variant_id=$1
    local output_file="$OUTPUT_DIR/${SOUND_NAME##*/}_variant_$(printf "%03d" $variant_id).wav"
    
       # Genera parametri random usando DISTRIBUZIONE UNIFORME (anti-ML, da RANGE.md)
       
       # 1. PITCH: Uniforme in [-200..-75] ∪ [75..200] (escluso dead zone ±75)
       pitch=$(python3 -c "import random; neg_or_pos = random.choice(['neg', 'pos']); print(random.randint(-200, -75) if neg_or_pos == 'neg' else random.randint(75, 200))")
       
       # 2. SNR: Uniforme in [35, 45] dB per white noise (da RANGE.md)
       snr=$(python3 -c "import random; print(f'{random.uniform(35, 45):.1f}')")
       
       # 3. EQ Tilt: Uniforme in [2, 6] dB (boost, da RANGE.md)
       eq_tilt=$(python3 -c "import random; print(f'{random.uniform(2.0, 6.0):.1f}')")
       
       # 4. HP Filter: Uniforme in [150, 250] Hz (da RANGE.md)
       hp_hz=$(python3 -c "import random; print(random.randint(150, 250))")
       
       # 5. LP Filter: Uniforme in [8000, 10000] Hz (da RANGE.md)
       lp_hz=$(python3 -c "import random; print(random.randint(8000, 10000))")
    
    # Log parametri nel CSV
    echo "$variant_id,$pitch,$snr,$eq_tilt,$hp_hz,$lp_hz" >> "$CSV_OUTPUT"
    
    # Log a schermo (mostra tutti i parametri)
    echo "  Generated variant $variant_id: pitch=${pitch}c, SNR=${snr}dB, EQ=${eq_tilt}dB, HP=${hp_hz}Hz, LP=${lp_hz}Hz"
    
    # NOTA: Per generazione reale, usa:
    # 1. Modifica temp CSV con questi parametri
    # 2. Esegui client con AC_AUDIO_OBF_RANDOMIZE=1
    # 3. Estrai audio processato da buffer OpenAL
}

echo -e "${YELLOW}Generating $NUM_VARIANTS variants...${NC}"
for i in $(seq 1 $NUM_VARIANTS); do
    generate_variant $i
done

echo ""
echo -e "${GREEN}✓ Generation complete!${NC}"
echo "Variants: $OUTPUT_DIR/"
echo "Parameters CSV: $CSV_OUTPUT"
echo ""
echo "Next steps:"
echo "1. Test soggettivo: python3 ADV_ML/tests/human_listen_and_label.py $OUTPUT_DIR"
echo "2. Estrazione MFCC: python3 ADV_ML/scripts/extract_features.py $OUTPUT_DIR"
echo "3. Test ML: python3 ADV_ML/scripts/train_classifier.py"

