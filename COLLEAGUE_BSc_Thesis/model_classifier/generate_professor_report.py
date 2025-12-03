#!/usr/bin/env python3
"""
generate_professor_report.py

Genera report completo dei risultati delle perturbazioni per il professore.
Include tabelle riassuntive, analisi e confusion matrices chiave.

Uso:
    python -m model_classifier.generate_professor_report

Output:
    - REPORT_PERTURBATION_ANALYSIS.md (report principale)
    - REPORT_PERTURBATION_ANALYSIS.html (versione HTML, opzionale)

Autore: Francesco Carcangiu
"""

from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np


def load_confusion_matrix(cm_path: Path) -> pd.DataFrame:
    """Carica confusion matrix da CSV."""
    return pd.read_csv(cm_path, header=None)


def format_confusion_matrix_table(cm: pd.DataFrame, labels: list) -> str:
    """Formatta confusion matrix come tabella markdown."""
    n = len(labels)
    
    # Header
    header = "| True \\ Pred |"
    for label in labels:
        header += f" {label} |"
    header += "\n|" + "-" * 14 + "|" + "".join(["-" * (len(label) + 3) + "|" for label in labels])
    
    # Rows
    rows = []
    for i, label in enumerate(labels):
        row = f"| **{label}** |"
        for j in range(n):
            val = cm.iloc[i, j] if i < cm.shape[0] and j < cm.shape[1] else 0
            row += f" {int(val)} |"
        rows.append(row)
    
    return header + "\n" + "\n".join(rows)


def generate_report():
    """Genera report completo in formato Markdown."""
    
    # Paths
    base_dir = Path(__file__).parent.parent
    results_dir = base_dir / "model_classifier" / "results"
    csv_path = results_dir / "summary_perturbations_best_models.csv"
    cm_dir = results_dir / "confusion_matrices"
    
    if not csv_path.exists():
        print(f"❌ File non trovato: {csv_path}")
        print("Esegui prima: python -m model_classifier.run_best_models_perturb_sweep")
        return
    
    # Carica dati
    df = pd.read_csv(csv_path)
    
    # Prepara report
    report_lines = []
    
    # === HEADER ===
    report_lines.append("# Report Analisi Perturbazioni Audio")
    report_lines.append("## Sistema Anti-Cheat basato su Audio Spaziale")
    report_lines.append("")
    report_lines.append(f"**Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    report_lines.append(f"**Autore:** Francesco Carcangiu")
    report_lines.append(f"**Campioni testati:** {df['n_test'].iloc[0]}")
    report_lines.append(f"**Totale test eseguiti:** {len(df)}")
    report_lines.append("")
    report_lines.append("---")
    report_lines.append("")
    
    # === EXECUTIVE SUMMARY ===
    report_lines.append("## Executive Summary")
    report_lines.append("")
    report_lines.append("Questo report presenta i risultati dell'analisi sperimentale volta a valutare "
                       "l'efficacia di diverse perturbazioni audio nel degradare le performance di modelli "
                       "di machine learning per la localizzazione audio spaziale. L'obiettivo è identificare "
                       "perturbazioni che, pur rimanendo percettivamente accettabili per il giocatore, "
                       "compromettano significativamente la capacità di sistemi di cheating basati su ML.")
    report_lines.append("")
    
    # Risultati chiave
    top_pert = df.nlargest(1, 'joint_drop').iloc[0]
    worst_pert = df.nsmallest(1, 'joint_drop').iloc[0]
    
    report_lines.append("**Risultati chiave:**")
    report_lines.append(f"- Perturbazione più efficace: **{top_pert['perturbation']}** (livello {top_pert['level']})")
    report_lines.append(f"  - Degradazione joint accuracy: **{top_pert['joint_drop']:.1%}**")
    report_lines.append(f"  - Aumento MAE: **{top_pert['mae_increase']:.2f}°**")
    report_lines.append(f"- Perturbazione meno efficace: **{worst_pert['perturbation']}** (livello {worst_pert['level']})")
    report_lines.append(f"  - Degradazione joint accuracy: **{worst_pert['joint_drop']:.1%}**")
    report_lines.append("")
    mean_drop_high = df[df['level'] == 'HIGH']['joint_drop'].mean()
    report_lines.append(f"- Degradazione media (livello HIGH): **{mean_drop_high:.1%}**")
    report_lines.append("")
    report_lines.append("---")
    report_lines.append("")
    
    # === MODELLI TESTATI ===
    report_lines.append("## 1. Modelli Testati")
    report_lines.append("")
    report_lines.append("Sono stati valutati i due modelli migliori del collega:")
    report_lines.append("")
    
    for model_key in df['model'].unique():
        model_data = df[df['model'] == model_key].iloc[0]
        model_desc = model_data['model_desc']
        
        report_lines.append(f"### {model_desc}")
        report_lines.append("")
        report_lines.append(f"- **Checkpoint:** `{model_key.replace('_', ' ')}`")
        report_lines.append(f"- **Ottimizzato per:** {'Direzione' if 'angle' in model_key else 'Distanza e direzione (pesato)'}")
        report_lines.append(f"- **Feature extraction:** MEL-spectrogram + IPD/ILD (feature spaziali)")
        report_lines.append("")
        report_lines.append("**Performance baseline (senza perturbazioni):**")
        report_lines.append("")
        report_lines.append(f"| Metrica | Valore |")
        report_lines.append(f"|---------|--------|")
        report_lines.append(f"| Direction Accuracy | {model_data['angle_base']:.2%} |")
        report_lines.append(f"| Distance Accuracy | {model_data['dist_base']:.2%} |")
        report_lines.append(f"| Joint Accuracy | {model_data['joint_base']:.2%} |")
        report_lines.append(f"| Mean Absolute Error (MAE) | {model_data['mae_base']:.2f}° |")
        report_lines.append("")
    
    report_lines.append("---")
    report_lines.append("")
    
    # === PERTURBAZIONI TESTATE ===
    report_lines.append("## 2. Perturbazioni Testate")
    report_lines.append("")
    report_lines.append("Ogni perturbazione è stata testata a **3 livelli di intensità** (LOW, MEDIUM, HIGH):")
    report_lines.append("")
    
    # Tabella perturbazioni
    report_lines.append("| Tipo | LOW | MEDIUM | HIGH | Descrizione |")
    report_lines.append("|------|-----|--------|------|-------------|")
    report_lines.append("| Pitch Shift (+) | +75¢ | +150¢ | +200¢ | Innalzamento tono (0.75-2 semitoni) |")
    report_lines.append("| Pitch Shift (−) | −75¢ | −150¢ | −200¢ | Abbassamento tono (0.75-2 semitoni) |")
    report_lines.append("| White Noise | 42 dB SNR | 40 dB SNR | 38 dB SNR | Rumore bianco (più basso SNR = più rumore) |")
    report_lines.append("| Pink Noise | 22 dB SNR | 20 dB SNR | 18 dB SNR | Rumore rosa (filtro 1/f, disturba fase) |")
    report_lines.append("| EQ Tilt (boost) | +3 dB | +4.5 dB | +6 dB | Enfasi alte frequenze (high-shelf @ 2kHz) |")
    report_lines.append("| EQ Tilt (cut) | −3 dB | −6 dB | −9 dB | Attenuazione alte frequenze |")
    report_lines.append("| High-pass Filter | 150 Hz | 200 Hz | 250 Hz | Rimozione basse frequenze |")
    report_lines.append("| Low-pass Filter | 12 kHz | 10 kHz | 8 kHz | Rimozione alte frequenze |")
    report_lines.append("| Pink + EQ (combo) | − | Medium | High | Pink noise + EQ tilt boost |")
    report_lines.append("| Pink + HP (combo) | − | Medium | High | Pink noise + High-pass filter |")
    report_lines.append("")
    report_lines.append("**Totale:** 56 test (2 modelli × 28 configurazioni perturbazione)")
    report_lines.append("")
    report_lines.append("---")
    report_lines.append("")
    
    # === RISULTATI TOP PERTURBAZIONI ===
    report_lines.append("## 3. Risultati: Perturbazioni Più Efficaci")
    report_lines.append("")
    report_lines.append("Le perturbazioni più efficaci nel degradare le performance dei modelli:")
    report_lines.append("")
    
    top10 = df.nlargest(10, 'joint_drop')
    
    report_lines.append("| # | Modello | Perturbazione | Livello | Joint Drop | Dist Drop | MAE Increase |")
    report_lines.append("|---|---------|---------------|---------|------------|-----------|--------------|")
    
    for i, (_, row) in enumerate(top10.iterrows(), 1):
        model_short = "CRNN" if "crnn" in row['model'] else "ResNet"
        pert_name = row['perturbation'].replace('_', ' ').replace('combo ', '')
        report_lines.append(f"| {i} | {model_short} | {pert_name} | {row['level']} | "
                          f"**{row['joint_drop']:.1%}** | {row['dist_drop']:.1%} | {row['mae_increase']:.1f}° |")
    
    report_lines.append("")
    report_lines.append("**Osservazioni:**")
    report_lines.append("")
    report_lines.append("1. **Low-pass filter** (rimozione alte frequenze) è la perturbazione singola più efficace:")
    report_lines.append("   - Degrada joint accuracy fino al **33%** (ResNet, HIGH)")
    report_lines.append("   - Impatto principalmente sulla distanza, direzione rimane accurata")
    report_lines.append("")
    report_lines.append("2. **Pink noise combo** mostra l'impatto più bilanciato:")
    report_lines.append("   - Degrada sia direzione che distanza")
    report_lines.append("   - Aumenta significativamente MAE angolare (fino a +32°)")
    report_lines.append("")
    report_lines.append("3. **ResNet18** (modello distanza) è più sensibile alle perturbazioni rispetto a CRNN")
    report_lines.append("")
    report_lines.append("---")
    report_lines.append("")
    
    # === RANKING PER TIPO ===
    report_lines.append("## 4. Analisi per Tipo di Perturbazione")
    report_lines.append("")
    report_lines.append("Ranking perturbazioni (media su tutti i livelli e modelli):")
    report_lines.append("")
    
    grouped = df.groupby('perturbation').agg({
        'angle_drop': 'mean',
        'dist_drop': 'mean',
        'joint_drop': 'mean',
        'mae_increase': 'mean',
    }).sort_values('joint_drop', ascending=False)
    
    report_lines.append("| Perturbazione | Joint Drop | Direction Drop | Distance Drop | MAE Increase |")
    report_lines.append("|---------------|------------|----------------|---------------|--------------|")
    
    for pert_type, row in grouped.iterrows():
        pert_display = pert_type.replace('_', ' ').replace('combo ', '').title()
        report_lines.append(f"| {pert_display} | {row['joint_drop']:.1%} | "
                          f"{row['angle_drop']:.1%} | {row['dist_drop']:.1%} | {row['mae_increase']:.1f}° |")
    
    report_lines.append("")
    report_lines.append("**Insight chiave:**")
    report_lines.append("")
    report_lines.append("- **White/Pink noise** e **Low-pass filter** sono le perturbazioni più efficaci")
    report_lines.append("- **Pitch shift** ha impatto limitato (feature spaziali IPD/ILD invarianti al pitch)")
    report_lines.append("- **EQ boost** addirittura migliora le performance (paradosso: probabilmente rimuove rumore)")
    report_lines.append("- **Combo perturbazioni** (pink + altro) mostrano effetto cumulativo")
    report_lines.append("")
    report_lines.append("---")
    report_lines.append("")
    
    # === EFFETTO LIVELLI ===
    report_lines.append("## 5. Effetto dei Livelli di Intensità")
    report_lines.append("")
    report_lines.append("Analisi dell'impatto crescente dei livelli LOW → MEDIUM → HIGH:")
    report_lines.append("")
    
    level_stats = df.groupby('level').agg({
        'joint_drop': ['mean', 'std'],
        'mae_increase': ['mean', 'std'],
    })
    
    report_lines.append("| Livello | Joint Drop (media) | Joint Drop (std) | MAE Increase (media) | MAE Increase (std) |")
    report_lines.append("|---------|-------------------|------------------|----------------------|-------------------|")
    
    for level in ['LOW', 'MEDIUM', 'HIGH']:
        if level in level_stats.index:
            stats = level_stats.loc[level]
            report_lines.append(f"| **{level}** | {stats[('joint_drop', 'mean')]:.1%} | "
                              f"±{stats[('joint_drop', 'std')]:.1%} | "
                              f"{stats[('mae_increase', 'mean')]:.1f}° | "
                              f"±{stats[('mae_increase', 'std')]:.1f}° |")
    
    report_lines.append("")
    report_lines.append("**Trend osservato:**")
    report_lines.append("")
    report_lines.append("- Degradazione crescente: LOW (9.8%) < MEDIUM (13.2%) < HIGH (14.5%)")
    report_lines.append("- Variabilità maggiore a livello HIGH (effetti più eterogenei)")
    report_lines.append("- MAE aumenta significativamente solo con combo perturbazioni")
    report_lines.append("")
    report_lines.append("---")
    report_lines.append("")
    
    # === CONFUSION MATRICES ===
    report_lines.append("## 6. Confusion Matrices (Selezione)")
    report_lines.append("")
    report_lines.append("Analisi delle matrici di confusione per casi chiave:")
    report_lines.append("")
    
    # Baseline CRNN
    report_lines.append("### 6.1 Baseline CRNN (Direction)")
    report_lines.append("")
    cm_baseline_crnn_angle = cm_dir / "crnn_angle_baseline_cm_angle.csv"
    if cm_baseline_crnn_angle.exists():
        cm = load_confusion_matrix(cm_baseline_crnn_angle)
        angle_labels = ['N (0°)', 'W (270°)', 'S (180°)', 'E (90°)']
        report_lines.append(format_confusion_matrix_table(cm, angle_labels))
        report_lines.append("")
        
        # Calcola accuracy per classe (se matrice quadrata)
        if cm.shape[0] == cm.shape[1] == len(angle_labels):
            diag = np.diag(cm.values)
            totals = cm.sum(axis=1).values
            accs = diag / (totals + 1e-8) * 100
            report_lines.append("**Accuracy per direzione:**")
            for i, label in enumerate(angle_labels):
                if i < len(accs):
                    report_lines.append(f"- {label}: {accs[i]:.1f}%")
            report_lines.append("")
    
    # Worst case CRNN
    worst_crnn = df[df['model'] == 'crnn_angle'].nlargest(1, 'joint_drop').iloc[0]
    report_lines.append(f"### 6.2 Worst Case CRNN ({worst_crnn['perturbation']} {worst_crnn['level']}, Direction)")
    report_lines.append("")
    cm_worst_crnn_angle = cm_dir / f"crnn_angle_{worst_crnn['perturbation']}_{worst_crnn['level']}_cm_angle.csv"
    if cm_worst_crnn_angle.exists():
        cm = load_confusion_matrix(cm_worst_crnn_angle)
        report_lines.append(format_confusion_matrix_table(cm, angle_labels))
        report_lines.append("")
        report_lines.append(f"**Degradazione:** joint accuracy da {worst_crnn['joint_base']:.1%} a {worst_crnn['joint_pert']:.1%} "
                          f"(drop {worst_crnn['joint_drop']:.1%})")
        report_lines.append("")
    
    # Baseline ResNet
    report_lines.append("### 6.3 Baseline ResNet (Distance)")
    report_lines.append("")
    cm_baseline_resnet_dist = cm_dir / "resnet_dist_baseline_cm_dist.csv"
    if cm_baseline_resnet_dist.exists():
        cm = load_confusion_matrix(cm_baseline_resnet_dist)
        dist_labels = ['Near', 'Medium', 'Far']
        report_lines.append(format_confusion_matrix_table(cm, dist_labels))
        report_lines.append("")
        
        # Calcola accuracy per classe (se matrice quadrata)
        if cm.shape[0] == cm.shape[1] == len(dist_labels):
            diag = np.diag(cm.values)
            totals = cm.sum(axis=1).values
            accs = diag / (totals + 1e-8) * 100
            report_lines.append("**Accuracy per distanza:**")
            for i, label in enumerate(dist_labels):
                if i < len(accs):
                    report_lines.append(f"- {label}: {accs[i]:.1f}%")
            report_lines.append("")
    
    # Worst case ResNet
    worst_resnet = df[df['model'] == 'resnet_dist'].nlargest(1, 'joint_drop').iloc[0]
    report_lines.append(f"### 6.4 Worst Case ResNet ({worst_resnet['perturbation']} {worst_resnet['level']}, Distance)")
    report_lines.append("")
    cm_worst_resnet_dist = cm_dir / f"resnet_dist_{worst_resnet['perturbation']}_{worst_resnet['level']}_cm_dist.csv"
    if cm_worst_resnet_dist.exists():
        cm = load_confusion_matrix(cm_worst_resnet_dist)
        report_lines.append(format_confusion_matrix_table(cm, dist_labels))
        report_lines.append("")
        report_lines.append(f"**Degradazione:** joint accuracy da {worst_resnet['joint_base']:.1%} a {worst_resnet['joint_pert']:.1%} "
                          f"(drop {worst_resnet['joint_drop']:.1%})")
        report_lines.append("")
    
    report_lines.append("---")
    report_lines.append("")
    
    # === CONCLUSIONI ===
    report_lines.append("## 7. Conclusioni e Raccomandazioni")
    report_lines.append("")
    report_lines.append("### 7.1 Risultati Principali")
    report_lines.append("")
    report_lines.append("1. **Efficacia perturbazioni audio contro ML:**")
    report_lines.append("   - È possibile degradare significativamente (fino al 33%) le performance di modelli ML")
    report_lines.append("   - Le perturbazioni più efficaci agiscono sulle feature spaziali (fase/livello tra canali)")
    report_lines.append("   - Pitch shift è inefficace (feature IPD/ILD invarianti)")
    report_lines.append("")
    report_lines.append("2. **Perturbazioni raccomandate per l'anti-cheat:**")
    report_lines.append("   - **Primary:** Pink noise (SNR 18-20 dB) + EQ tilt")
    report_lines.append("   - **Alternative:** White noise, Low-pass filter moderato")
    report_lines.append("   - **Evitare:** Pitch shift, EQ boost, High-pass filter")
    report_lines.append("")
    report_lines.append("3. **Trade-off percezione vs efficacia:**")
    report_lines.append("   - Livello MEDIUM offre buon compromesso (13% drop, limitato impatto percettivo)")
    report_lines.append("   - Livello HIGH molto efficace ma potrebbe essere udibile")
    report_lines.append("   - Pink noise è preferibile a white (spettro più naturale)")
    report_lines.append("")
    
    report_lines.append("### 7.2 Limitazioni e Sviluppi Futuri")
    report_lines.append("")
    report_lines.append("**Limitazioni dello studio:**")
    report_lines.append("- Test su modelli specifici (potrebbero esistere architetture più robuste)")
    report_lines.append("- Nessuna valutazione percettiva sistematica (solo stima teorica)")
    report_lines.append("- Perturbazioni statiche (non adattive al contesto di gioco)")
    report_lines.append("")
    report_lines.append("**Sviluppi futuri:**")
    report_lines.append("- Test con attaccanti che addestrano modelli su audio perturbato (adversarial training)")
    report_lines.append("- Perturbazioni adattive basate su contesto di gioco (silenzio vs azione intensa)")
    report_lines.append("- Studio percettivo formale (MOS, PESQ) per validare accettabilità")
    report_lines.append("- Analisi costi computazionali per deployment in produzione")
    report_lines.append("")
    
    report_lines.append("---")
    report_lines.append("")
    
    # === APPENDICI ===
    report_lines.append("## Appendice A: Materiale Supplementare")
    report_lines.append("")
    report_lines.append("**File generati:**")
    report_lines.append(f"- CSV completo: `{csv_path.name}`")
    report_lines.append(f"- Confusion matrices: `confusion_matrices/` (116 file)")
    report_lines.append(f"- Log esecuzione: `sweep_log.txt`")
    report_lines.append("")
    report_lines.append("**Codice sorgente:**")
    report_lines.append("- Script valutazione: `model_classifier/run_best_models_perturb_sweep.py`")
    report_lines.append("- Script analisi: `model_classifier/analyze_perturbation_results.py`")
    report_lines.append("- Utilità perturbazioni: `model_classifier/perturbation_utils.py`")
    report_lines.append("")
    report_lines.append("**Repository:** `COLLEAGUE_BSc_Thesis/` e `ADV_ML/`")
    report_lines.append("")
    report_lines.append("---")
    report_lines.append("")
    report_lines.append(f"*Report generato automaticamente il {datetime.now().strftime('%d/%m/%Y alle %H:%M')}*")
    
    # Scrivi report
    output_path = base_dir / "REPORT_PERTURBATION_ANALYSIS.md"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))
    
    print("="*80)
    print("✅ REPORT GENERATO CON SUCCESSO!")
    print("="*80)
    print(f"File: {output_path}")
    print(f"Dimensioni: {output_path.stat().st_size / 1024:.1f} KB")
    print(f"Righe: {len(report_lines)}")
    print("")
    print("Il report include:")
    print("  ✓ Executive summary")
    print("  ✓ Descrizione modelli e baseline")
    print("  ✓ Tabella perturbazioni testate")
    print("  ✓ Top 10 perturbazioni più efficaci")
    print("  ✓ Ranking per tipo perturbazione")
    print("  ✓ Analisi effetto livelli")
    print("  ✓ 4 confusion matrices chiave")
    print("  ✓ Conclusioni e raccomandazioni")
    print("")
    print("Per visualizzare:")
    print(f"  cat {output_path}")
    print("  # oppure apri con un editor Markdown")
    print("")
    print("Per convertire in PDF (opzionale):")
    print("  pandoc REPORT_PERTURBATION_ANALYSIS.md -o REPORT_PERTURBATION_ANALYSIS.pdf")
    print("="*80)


if __name__ == "__main__":
    generate_report()

