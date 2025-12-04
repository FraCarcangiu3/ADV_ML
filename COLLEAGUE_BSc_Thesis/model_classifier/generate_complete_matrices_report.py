#!/usr/bin/env python3
"""
Script per generare un report completo con tutte le confusion matrices
per i rumori base (pink_noise, white_noise, pitch) a tutti i livelli.
"""

import pandas as pd
from pathlib import Path

# Paths
RESULTS_DIR = Path(__file__).parent / "results"
CSV_PATH = RESULTS_DIR / "summary_perturbations_best_models.csv"
CM_DIR = RESULTS_DIR / "confusion_matrices"
OUTPUT_PATH = Path(__file__).parent.parent / "REPORT_COMPLETE_CONFUSION_MATRICES.md"

# Perturbazioni base da includere
BASE_PERTURBATIONS = [
    "pink_noise",
    "white_noise", 
    "pitch_pos",
    "pitch_neg",
    "eq_boost",
    "eq_cut",
    "hp",
    "lp",
]

def read_confusion_matrix(cm_file):
    """Legge una confusion matrix da CSV"""
    if not cm_file.exists():
        return None
    df = pd.read_csv(cm_file)
    # Le colonne sono già i nomi corretti, gli indici sono impliciti
    df.index = df.columns  # Imposta gli stessi nomi per le righe
    return df

def format_cm_as_markdown(df, title):
    """Formatta una confusion matrix come tabella Markdown"""
    if df is None:
        return f"### {title}\n\n*Matrice non disponibile*\n\n"
    
    md = f"### {title}\n\n"
    md += "| True \\ Pred |"
    for col in df.columns:
        md += f" {col} |"
    md += "\n|" + "---|" * (len(df.columns) + 1) + "\n"
    
    for idx in df.index:
        md += f"| **{idx}** |"
        for col in df.columns:
            val = int(df.loc[idx, col]) if pd.notna(df.loc[idx, col]) else 0
            md += f" {val} |"
        md += "\n"
    
    md += "\n"
    return md

def main():
    print("Generazione report completo confusion matrices...")
    
    # Leggi CSV summary
    df = pd.read_csv(CSV_PATH)
    
    # Crea report
    report = []
    report.append("# Report Completo: Confusion Matrices per Rumori Base\n")
    report.append("Questo report include le confusion matrices per tutti i rumori base ")
    report.append("(pink_noise, white_noise, pitch, eq, hp, lp) a tutti i livelli (LOW, MEDIUM, HIGH).\n\n")
    report.append("---\n\n")
    
    # Per ogni perturbazione base
    for pert in BASE_PERTURBATIONS:
        report.append(f"## {pert.upper().replace('_', ' ')}\n\n")
        
        # Per ogni livello
        for level in ["LOW", "MEDIUM", "HIGH"]:
            report.append(f"### Livello: {level}\n\n")
            
            # CRNN (angle)
            report.append(f"#### CRNN (Direction)\n\n")
            cm_angle_file = CM_DIR / f"crnn_angle_{pert}_{level}_cm_angle.csv"
            cm_angle = read_confusion_matrix(cm_angle_file)
            report.append(format_cm_as_markdown(cm_angle, f"Direction - {pert} {level}"))
            
            # Trova accuracy dal CSV
            row = df[(df['model'] == 'crnn_angle') & 
                    (df['perturbation'] == pert) & 
                    (df['level'] == level)]
            if not row.empty:
                angle_base = row['angle_base'].values[0]
                angle_pert = row['angle_pert'].values[0]
                angle_drop = row['angle_drop'].values[0]
                mae_base = row['mae_base'].values[0]
                mae_pert = row['mae_pert'].values[0]
                mae_increase = row['mae_increase'].values[0]
                
                report.append(f"**Metriche:**\n")
                report.append(f"- Direction Accuracy: {angle_base:.1%} → {angle_pert:.1%} (drop: {angle_drop:.1%})\n")
                report.append(f"- MAE: {mae_base:.1f}° → {mae_pert:.1f}° (+{mae_increase:.1f}°)\n\n")
            
            # ResNet (distance)
            report.append(f"#### ResNet (Distance)\n\n")
            cm_dist_file = CM_DIR / f"resnet_dist_{pert}_{level}_cm_dist.csv"
            cm_dist = read_confusion_matrix(cm_dist_file)
            report.append(format_cm_as_markdown(cm_dist, f"Distance - {pert} {level}"))
            
            # Trova accuracy dal CSV
            row = df[(df['model'] == 'resnet_dist') & 
                    (df['perturbation'] == pert) & 
                    (df['level'] == level)]
            if not row.empty:
                dist_base = row['dist_base'].values[0]
                dist_pert = row['dist_pert'].values[0]
                dist_drop = row['dist_drop'].values[0]
                joint_base = row['joint_base'].values[0]
                joint_pert = row['joint_pert'].values[0]
                joint_drop = row['joint_drop'].values[0]
                
                report.append(f"**Metriche:**\n")
                report.append(f"- Distance Accuracy: {dist_base:.1%} → {dist_pert:.1%} (drop: {dist_drop:.1%})\n")
                report.append(f"- Joint Accuracy: {joint_base:.1%} → {joint_pert:.1%} (drop: {joint_drop:.1%})\n\n")
            
            report.append("---\n\n")
        
        report.append("\n")
    
    # Scrivi report
    with open(OUTPUT_PATH, 'w') as f:
        f.write(''.join(report))
    
    print(f"✅ Report generato: {OUTPUT_PATH}")
    print(f"   Dimensioni: {OUTPUT_PATH.stat().st_size / 1024:.1f} KB")

if __name__ == "__main__":
    main()

