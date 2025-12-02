#!/usr/bin/env python3
"""
analyze_perturbation_results.py

Script per analizzare e visualizzare i risultati del sweep di perturbazioni.

Uso:
    python -m model_classifier.analyze_perturbation_results

Output:
    - Stampa tabelle riassuntive a schermo
    - Identifica perturbazioni più/meno efficaci
    - Ranking per tipo di perturbazione

Autore: Francesco Carcangiu
"""

import pandas as pd
from pathlib import Path


def analyze_results():
    """Analizza i risultati del sweep perturbazioni."""
    
    # Carica CSV
    csv_path = Path(__file__).parent / "results" / "summary_perturbations_best_models.csv"
    
    if not csv_path.exists():
        print(f"❌ File non trovato: {csv_path}")
        print(f"\nEsegui prima:")
        print(f"  python -m model_classifier.run_best_models_perturb_sweep")
        return
    
    df = pd.read_csv(csv_path)
    
    print("="*80)
    print("ANALISI RISULTATI PERTURBAZIONI")
    print("="*80)
    print(f"CSV: {csv_path}")
    print(f"Totale test: {len(df)} righe\n")
    
    # Statistiche per modello
    print("-"*80)
    print("STATISTICHE PER MODELLO")
    print("-"*80)
    
    for model in df['model'].unique():
        df_model = df[df['model'] == model]
        model_desc = df_model['model_desc'].iloc[0]
        
        print(f"\n{model_desc}:")
        print(f"  Baseline:")
        print(f"    - Direction accuracy: {df_model['angle_base'].iloc[0]:.4f}")
        print(f"    - Distance accuracy:  {df_model['dist_base'].iloc[0]:.4f}")
        print(f"    - Joint accuracy:     {df_model['joint_base'].iloc[0]:.4f}")
        print(f"    - MAE:                {df_model['mae_base'].iloc[0]:.2f}°")
        
        print(f"\n  Degr degradazione media:")
        print(f"    - Direction drop:     {df_model['angle_drop'].mean():+.4f}")
        print(f"    - Distance drop:      {df_model['dist_drop'].mean():+.4f}")
        print(f"    - Joint drop:         {df_model['joint_drop'].mean():+.4f}")
        print(f"    - MAE increase:       {df_model['mae_increase'].mean():+.2f}°")
    
    # Top 10 perturbazioni più efficaci (per joint_drop)
    print("\n" + "-"*80)
    print("TOP 10 PERTURBAZIONI PIÙ EFFICACI (maggior degradazione joint accuracy)")
    print("-"*80)
    
    df_sorted = df.sort_values('joint_drop', ascending=False).head(10)
    
    print(f"\n{'Model':<15} {'Perturbation':<20} {'Level':<8} {'Joint Drop':<12} {'MAE Increase':<12}")
    print("-"*80)
    for _, row in df_sorted.iterrows():
        model_short = row['model']
        pert = row['perturbation']
        level = row['level']
        joint_drop = row['joint_drop']
        mae_inc = row['mae_increase']
        print(f"{model_short:<15} {pert:<20} {level:<8} {joint_drop:+.4f}       {mae_inc:+.2f}°")
    
    # Ranking per tipo di perturbazione (media su tutti i livelli)
    print("\n" + "-"*80)
    print("RANKING PERTURBAZIONI (media su tutti i livelli)")
    print("-"*80)
    
    # Raggruppa per tipo perturbazione
    df_grouped = df.groupby('perturbation').agg({
        'angle_drop': 'mean',
        'dist_drop': 'mean',
        'joint_drop': 'mean',
        'mae_increase': 'mean',
    }).sort_values('joint_drop', ascending=False)
    
    print(f"\n{'Perturbation Type':<25} {'Angle Drop':<12} {'Dist Drop':<12} {'Joint Drop':<12} {'MAE Inc':<10}")
    print("-"*80)
    for pert_type, row in df_grouped.iterrows():
        print(f"{pert_type:<25} {row['angle_drop']:+.4f}       {row['dist_drop']:+.4f}       {row['joint_drop']:+.4f}       {row['mae_increase']:+.2f}°")
    
    # Effetto dei livelli (LOW vs MEDIUM vs HIGH)
    print("\n" + "-"*80)
    print("EFFETTO LIVELLI (LOW vs MEDIUM vs HIGH)")
    print("-"*80)
    
    for level in ['LOW', 'MEDIUM', 'HIGH']:
        df_level = df[df['level'] == level]
        print(f"\n{level}:")
        print(f"  - Media joint drop: {df_level['joint_drop'].mean():+.4f}")
        print(f"  - Media MAE incr:   {df_level['mae_increase'].mean():+.2f}°")
        print(f"  - N° test:          {len(df_level)}")
    
    # Best practices per tesi
    print("\n" + "="*80)
    print("RACCOMANDAZIONI PER LA TESI")
    print("="*80)
    
    # Identifica perturbazioni più efficaci
    best_pert = df.nlargest(3, 'joint_drop')
    print("\n1. PERTURBAZIONI PIÙ EFFICACI (usa questi nella discussione):")
    for i, (_, row) in enumerate(best_pert.iterrows(), 1):
        print(f"   {i}. {row['perturbation']} (level {row['level']})")
        print(f"      → Joint drop: {row['joint_drop']:+.4f}, MAE increase: {row['mae_increase']:+.2f}°")
    
    # Identifica perturbazioni meno efficaci
    worst_pert = df.nsmallest(3, 'joint_drop')
    print("\n2. PERTURBAZIONI MENO EFFICACI (spiega perché non funzionano):")
    for i, (_, row) in enumerate(worst_pert.iterrows(), 1):
        print(f"   {i}. {row['perturbation']} (level {row['level']})")
        print(f"      → Joint drop: {row['joint_drop']:+.4f}")
        print(f"      → Motivo: Feature spaziali (IPD/ILD) invarianti a questa perturbazione")
    
    print("\n3. GRAFICI SUGGERITI:")
    print("   - Barplot: joint_drop per tipo perturbazione")
    print("   - Heatmap: drop vs livello (LOW/MED/HIGH)")
    print("   - Confusion matrix: baseline vs worst perturbation")
    
    print("\n4. TABELLE PER TESI:")
    print("   - Tabella riassuntiva baseline (accuracy per modello)")
    print("   - Tabella top-5 perturbazioni con metriche complete")
    print("   - Tabella confronto LOW/MED/HIGH su 2-3 perturbazioni chiave")
    
    print("\n" + "="*80)
    print(f"Dati completi disponibili in: {csv_path}")
    print(f"Confusion matrices in: {csv_path.parent / 'confusion_matrices'}/")
    print("="*80 + "\n")


if __name__ == "__main__":
    analyze_results()

