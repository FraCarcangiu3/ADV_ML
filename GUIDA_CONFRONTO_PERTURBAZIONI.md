# Guida: Confronto Accuracy con Perturbazioni Audio

## 🎯 Obiettivo

Dopo aver completato il training baseline (9-fold CV), confrontare l'accuracy del modello **clean** vs **perturbato** per ogni tipo di rumore/perturbazione singola (pitch shift positivo, pitch shift negativo, white noise, pink noise, ecc.).

---

## 📋 Prerequisiti

### ✅ Verifica che il training sia completato

Sul server SSH, verifica:

```bash
cd COLLEAGUE_BSc_Thesis

# 1. Controlla che i checkpoint siano stati creati
ls -lh model_classifier/checkpoints/

# Dovresti vedere 27 file totali (3 modelli × 9 fold):
# - resnet18_mel96_fold1.pth ... fold9.pth
# - crnn_mel80_fold1.pth ... fold9.pth
# - conv1d_sep_ds48k_fold1.pth ... fold9.pth

# 2. Conta i checkpoint
echo "Checkpoint trovati:"
ls model_classifier/checkpoints/*.pth 2>/dev/null | wc -l
# Deve stampare: 27

# 3. Verifica che il file risultati baseline sia stato creato
ls -lh model_classifier/results_*.txt

# 4. Visualizza i risultati baseline
tail -50 model_classifier/results_*.txt | head -30
```

**Cosa ti aspetti di vedere:**
```
resnet18_mel96  | angle=0.6234 | dist=0.7145 | joint=0.4856 | mae=28.34°
crnn_mel80      | angle=0.5923 | dist=0.6987 | joint=0.4512 | mae=31.12°
conv1d_sep_ds48k| angle=0.5645 | dist=0.6734 | joint=0.4123 | mae=34.56°
```

---

## 🚀 STEP 1: Scegli il Modello da Testare

In base ai risultati baseline, scegli il modello con **migliore accuracy** (di solito `resnet18_mel96`).

```bash
# Variabile per il modello scelto (modifica se necessario)
export TEST_MODEL="resnet18_mel96"
echo "Modello selezionato: $TEST_MODEL"
```

---

## 🧪 STEP 2: Test Singolo Preset (Verifica Funzionamento)

Prima di lanciare tutti i test, verifica con un singolo preset:

```bash
cd COLLEAGUE_BSc_Thesis

# Test pitch shift positivo +150 cents
python -m model_classifier.eval_perturbation_cv \
    --model resnet18_mel96 \
    --perturb-preset pitch_P2_pos \
    --results-csv results/test_pitch_P2_pos.csv

# Visualizza risultati
cat results/test_pitch_P2_pos.csv
```

**Output atteso:**
```csv
fold,preset,n_test,angle_base,angle_pert,angle_drop,dist_base,dist_pert,dist_drop,...
1,pitch_P2_pos,108,0.6200,0.4500,+0.1700,0.7100,0.6300,+0.0800,...
2,pitch_P2_pos,108,0.6100,0.4400,+0.1700,0.7000,0.6200,+0.0800,...
...
mean,pitch_P2_pos,972,0.6150,0.4450,+0.1700,0.7050,0.6250,+0.0800,...
```

**Interpretazione:**
- `angle_drop` positivo = il modello è **meno accurato** con la perturbazione (BUONO per noi!)
- `angle_drop` grande (~0.10-0.20) = perturbazione **efficace** nel confondere il modello

---

## 🔄 STEP 3: Test Completo - Tutte le Perturbazioni

### 3A. Crea cartella risultati

```bash
cd COLLEAGUE_BSc_Thesis
mkdir -p results/perturbations
```

### 3B. Script Batch per Tutte le Perturbazioni

Crea uno script per testare tutte le perturbazioni in sequenza:

```bash
cd COLLEAGUE_BSc_Thesis

# Crea script di test
cat > run_all_perturbations.sh << 'EOF'
#!/bin/bash

# Configurazione
MODEL="resnet18_mel96"
RESULTS_DIR="results/perturbations"
mkdir -p "$RESULTS_DIR"

# Lista preset da testare
PRESETS=(
    # Pitch Shift Positivo
    "pitch_P1_pos"
    "pitch_P2_pos"
    "pitch_P3_pos"
    
    # Pitch Shift Negativo
    "pitch_P1_neg"
    "pitch_P2_neg"
    "pitch_P3_neg"
    
    # White Noise
    "white_W1"
    "white_W2"
    "white_W3"
    
    # Pink Noise
    "pink_K1"
    "pink_K2"
    "pink_K3"
    
    # EQ Boost
    "eq_boost_light"
    "eq_boost_medium"
    "eq_boost_strong"
    
    # EQ Cut
    "eq_cut_light"
    "eq_cut_medium"
    "eq_cut_strong"
)

# Loop su tutti i preset
echo "========================================="
echo "INIZIO TEST PERTURBAZIONI"
echo "Modello: $MODEL"
echo "Numero preset da testare: ${#PRESETS[@]}"
echo "========================================="
echo ""

for preset in "${PRESETS[@]}"; do
    echo ">>> Testing preset: $preset"
    echo "    Timestamp: $(date '+%Y-%m-%d %H:%M:%S')"
    
    python -m model_classifier.eval_perturbation_cv \
        --model "$MODEL" \
        --perturb-preset "$preset" \
        --results-csv "$RESULTS_DIR/${preset}.csv"
    
    if [ $? -eq 0 ]; then
        echo "    ✅ Completato con successo"
    else
        echo "    ❌ ERRORE - Controlla i log"
    fi
    echo ""
done

echo "========================================="
echo "TEST COMPLETATI"
echo "Risultati salvati in: $RESULTS_DIR"
echo "========================================="
EOF

# Rendi eseguibile
chmod +x run_all_perturbations.sh
```

### 3C. Lancia lo Script

```bash
# Versione foreground (vedi output in tempo reale)
./run_all_perturbations.sh

# OPPURE versione background (consigliata per SSH)
nohup ./run_all_perturbations.sh > logs_perturbations.txt 2>&1 &

# Monitora progresso
tail -f logs_perturbations.txt
```

**Tempo stimato:** 2-4 ore per 18 preset (dipende da dataset e CPU)

---

## 📊 STEP 4: Aggregazione e Confronto Risultati

### 4A. Script per Aggregare Tutti i CSV

```bash
cd COLLEAGUE_BSc_Thesis

# Crea script di aggregazione
cat > aggregate_results.py << 'EOF'
#!/usr/bin/env python3
"""Aggrega risultati di tutte le perturbazioni in un CSV comparativo."""

import pandas as pd
from pathlib import Path

# Configurazione
RESULTS_DIR = Path("results/perturbations")
OUTPUT_CSV = "results/comparison_all_perturbations.csv"

def main():
    all_results = []
    
    # Leggi tutti i CSV
    csv_files = sorted(RESULTS_DIR.glob("*.csv"))
    
    print(f"Trovati {len(csv_files)} file CSV")
    
    for csv_file in csv_files:
        try:
            df = pd.read_csv(csv_file)
            # Prendi solo la riga 'mean'
            mean_row = df[df['fold'] == 'mean'].copy()
            if not mean_row.empty:
                all_results.append(mean_row)
                print(f"✅ {csv_file.name}")
        except Exception as e:
            print(f"❌ {csv_file.name}: {e}")
    
    if not all_results:
        print("ERRORE: Nessun risultato trovato!")
        return
    
    # Concatena tutti i risultati
    comparison_df = pd.concat(all_results, ignore_index=True)
    
    # Ordina per angle_drop (discendente = perturbazioni più efficaci)
    comparison_df = comparison_df.sort_values('angle_drop', ascending=False)
    
    # Salva
    comparison_df.to_csv(OUTPUT_CSV, index=False)
    
    print(f"\n{'='*70}")
    print(f"Risultati aggregati salvati in: {OUTPUT_CSV}")
    print(f"{'='*70}\n")
    
    # Stampa top 5 perturbazioni più efficaci
    print("TOP 5 PERTURBAZIONI PIÙ EFFICACI (maggiore degradazione direzione):\n")
    top5 = comparison_df.head(5)
    for idx, row in top5.iterrows():
        print(f"{idx+1}. {row['preset']:20s} | "
              f"angle_drop={row['angle_drop']:+.4f} | "
              f"joint_drop={row['joint_drop']:+.4f} | "
              f"mae_increase={row['mae_increase']:+.2f}°")
    
    print(f"\n{'='*70}")

if __name__ == "__main__":
    main()
EOF

# Esegui aggregazione
python aggregate_results.py
```

**Output atteso:**

```
TOP 5 PERTURBAZIONI PIÙ EFFICACI:
1. pitch_P3_pos          | angle_drop=+0.2145 | joint_drop=+0.1923 | mae_increase=+18.34°
2. pitch_P3_neg          | angle_drop=+0.2012 | joint_drop=+0.1856 | mae_increase=+17.12°
3. pitch_P2_pos          | angle_drop=+0.1734 | joint_drop=+0.1567 | mae_increase=+14.56°
4. white_W3              | angle_drop=+0.1523 | joint_drop=+0.1345 | mae_increase=+12.89°
5. pink_K3               | angle_drop=+0.1456 | joint_drop=+0.1289 | mae_increase=+11.67°
```

### 4B. Visualizza Tabella Completa

```bash
# Visualizza primi 20 risultati
head -20 results/comparison_all_perturbations.csv | column -t -s,
```

---

## 📈 STEP 5: Analisi e Visualizzazione

### 5A. Grafici Confronto (opzionale)

```bash
cd COLLEAGUE_BSc_Thesis

cat > plot_comparison.py << 'EOF'
#!/usr/bin/env python3
"""Crea grafici di confronto per perturbazioni."""

import pandas as pd
import matplotlib.pyplot as plt

# Leggi risultati aggregati
df = pd.read_csv("results/comparison_all_perturbations.csv")

# Figura con 3 subplot
fig, axes = plt.subplots(1, 3, figsize=(18, 6))

# 1. Direction Accuracy Drop
ax1 = axes[0]
df_sorted = df.sort_values('angle_drop', ascending=True)
ax1.barh(df_sorted['preset'], df_sorted['angle_drop'], color='tomato')
ax1.set_xlabel('Direction Accuracy Drop')
ax1.set_title('Degradazione Accuracy Direzione')
ax1.axvline(0, color='black', linewidth=0.5)
ax1.grid(axis='x', alpha=0.3)

# 2. Distance Accuracy Drop
ax2 = axes[1]
df_sorted = df.sort_values('dist_drop', ascending=True)
ax2.barh(df_sorted['preset'], df_sorted['dist_drop'], color='orange')
ax2.set_xlabel('Distance Accuracy Drop')
ax2.set_title('Degradazione Accuracy Distanza')
ax2.axvline(0, color='black', linewidth=0.5)
ax2.grid(axis='x', alpha=0.3)

# 3. Joint Accuracy Drop
ax3 = axes[2]
df_sorted = df.sort_values('joint_drop', ascending=True)
ax3.barh(df_sorted['preset'], df_sorted['joint_drop'], color='steelblue')
ax3.set_xlabel('Joint Accuracy Drop')
ax3.set_title('Degradazione Accuracy Congiunta')
ax3.axvline(0, color='black', linewidth=0.5)
ax3.grid(axis='x', alpha=0.3)

plt.tight_layout()
plt.savefig('results/perturbation_comparison.png', dpi=150)
print("Grafico salvato in: results/perturbation_comparison.png")
EOF

# Esegui (richiede matplotlib)
python plot_comparison.py
```

### 5B. Scarica Risultati dal Server al Mac

Sul tuo Mac:

```bash
# Naviga nella cartella locale
cd "/Users/francesco03/Documents/GitHub/AssaultCube Server/COLLEAGUE_BSc_Thesis"

# Scarica risultati dal server (modifica con indirizzo server reale)
scp -r username@server:/path/to/COLLEAGUE_BSc_Thesis/results ./

# Ora hai i risultati localmente per analisi ulteriore
```

---

## 📝 STEP 6: Interpretazione Risultati

### Metriche Chiave

| Metrica | Significato | Valore Ideale per Tesi |
|---------|-------------|------------------------|
| `angle_drop` | Quanto peggiora l'accuracy direzione | **Positivo e grande** (>0.10) = perturbazione efficace |
| `dist_drop` | Quanto peggiora l'accuracy distanza | Positivo = perturbazione impatta anche distanza |
| `joint_drop` | Quanto peggiora l'accuracy congiunta | Positivo e grande = perturbazione impatta entrambi |
| `mae_increase` | Quanto aumenta l'errore angolare | Positivo = errori più grandi con perturbazione |

### Domande di Ricerca

Per la tua tesi, analizza:

1. **Quale perturbazione è più efficace nel degradare il modello?**
   - Guarda `angle_drop` e `joint_drop`
   - Confronta pitch shift vs noise vs EQ

2. **Il pitch shift positivo è più efficace del negativo?**
   - Confronta `pitch_P2_pos` vs `pitch_P2_neg`

3. **L'intensità della perturbazione impatta linearmente?**
   - Confronta P1 vs P2 vs P3 (light vs medium vs strong)

4. **Il modello è più sensibile a pitch shift o noise?**
   - Media `angle_drop` per categoria

### Tabella di Confronto per Tesi

Crea una tabella simile:

| Categoria | Preset | Baseline Acc | Perturbato Acc | Drop | MAE Increase |
|-----------|--------|--------------|----------------|------|--------------|
| Pitch+ | P2_pos | 0.6150 | 0.4450 | **+0.1700** | +14.06° |
| Pitch- | P2_neg | 0.6150 | 0.4520 | +0.1630 | +13.45° |
| White | W2 | 0.6150 | 0.4980 | +0.1170 | +9.23° |
| Pink | K2 | 0.6150 | 0.5050 | +0.1100 | +8.67° |

---

## 🔧 Troubleshooting

### Problema: "Checkpoint non trovato"

```bash
# Verifica che i checkpoint esistano
ls model_classifier/checkpoints/*.pth

# Se mancano, rilancia training
python -m model_classifier.deep_cv
```

### Problema: Script si interrompe

```bash
# Controlla log errori
tail -100 logs_perturbations.txt | grep -i error

# Rilancia singolo preset fallito
python -m model_classifier.eval_perturbation_cv \
    --model resnet18_mel96 \
    --perturb-preset <preset_fallito>
```

### Problema: File CSV vuoti o corrotti

```bash
# Rimuovi CSV parziali
rm results/perturbations/<preset_problematico>.csv

# Rilancia per quel preset
./run_all_perturbations.sh
```

### Warning "pin_memory" durante esecuzione

**Messaggio:**
```
UserWarning: 'pin_memory' argument is set as true but no accelerator is found
```

**Causa:** Training su CPU (nessuna GPU disponibile)

**Soluzione:** ✅ Nessuna azione necessaria - è solo un warning informativo, il training funziona normalmente su CPU.

---

## 📦 Consegna Risultati

### File da Includere nella Tesi

```
COLLEAGUE_BSc_Thesis/
├── model_classifier/
│   ├── results_<timestamp>.txt          # Risultati baseline
│   └── checkpoints/                      # Checkpoint modelli (opzionale)
├── results/
│   ├── comparison_all_perturbations.csv # Tabella aggregata ⭐
│   ├── perturbation_comparison.png      # Grafici (se generati)
│   └── perturbations/                    # CSV singoli per preset
│       ├── pitch_P1_pos.csv
│       ├── pitch_P2_pos.csv
│       └── ...
```

### Backup Locale

```bash
# Sul Mac
cd "/Users/francesco03/Documents/GitHub/AssaultCube Server"

# Commit risultati
git add COLLEAGUE_BSc_Thesis/results
git commit -m "Add perturbation evaluation results - 9-fold CV"
git push
```

---

## ⏱️ Timeline Stimata

| Step | Tempo | Nota |
|------|-------|------|
| Verifica training completato | 5 min | |
| Test singolo preset | 10 min | Verifica funzionamento |
| Test tutti i preset (18) | 2-4 ore | Dipende da CPU e dataset |
| Aggregazione risultati | 5 min | |
| Analisi e grafici | 30 min | |
| **TOTALE** | **~3-5 ore** | La maggior parte è automatica |

---

## 🎓 Prossimi Passi per la Tesi

Dopo aver completato questa guida:

1. ✅ Hai risultati baseline (clean)
2. ✅ Hai risultati per 18 perturbazioni diverse
3. ✅ Hai tabella comparativa aggregata

**Cosa fare dopo:**

- 📊 Analizzare pattern (pitch vs noise, positivo vs negativo)
- 📝 Scrivere sezione "Risultati Sperimentali" della tesi
- 📈 Creare grafici professionali per presentazione
- 🔬 Testare altri modelli (`crnn_mel80`, `conv1d_sep_ds48k`) se tempo disponibile
- 💡 Proporre contromisure (data augmentation, adversarial training)

---

## 📞 Riferimenti Rapidi

### Comandi Essenziali

```bash
# Verifica training completato
ls model_classifier/checkpoints/*.pth | wc -l  # Deve essere 27

# Test singolo preset
python -m model_classifier.eval_perturbation_cv --model resnet18_mel96 --perturb-preset pitch_P2_pos

# Test tutti i preset
./run_all_perturbations.sh

# Aggrega risultati
python aggregate_results.py

# Visualizza top risultati
head -10 results/comparison_all_perturbations.csv
```

### Preset Più Importanti da Testare

Se hai poco tempo, testa almeno questi:

1. `pitch_P2_pos` - Pitch +150 cents (medio, positivo) ⭐
2. `pitch_P2_neg` - Pitch -150 cents (medio, negativo)
3. `white_W2` - White noise 40 dB
4. `pink_K2` - Pink noise 20 dB

---

**Fine Guida** 🚀

**Ultimo aggiornamento:** 2025-12-02
**Autore:** Francesco Carcangiu

