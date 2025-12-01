#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
extract_features.py
===================

Script per estrarre feature MFCC dai file audio del dataset.

COSA FA QUESTO SCRIPT:
1. Legge tutti i file .wav dalle cartelle dataset/original e dataset/obfuscated
2. Per ogni file, calcola i coefficienti MFCC (Mel-Frequency Cepstral Coefficients)
3. Crea una matrice X con tutte le feature
4. Crea un vettore y con le etichette (0=original, 1=obfuscated)
5. Salva X e y in formato NumPy (.npy)

COME USARLO:
    python3 extract_features.py

OUTPUT:
    - features/X.npy : Matrice delle feature (n_samples, n_features)
    - features/y.npy : Vettore delle etichette (n_samples,)

REQUISITI:
    - librosa
    - numpy
    - tqdm (per progress bar)
"""

# ==============================================================================
# IMPORT DELLE LIBRERIE
# ==============================================================================

import os                    # Per navigare il filesystem
import glob                  # Per cercare file con pattern (*.wav)
import numpy as np           # Per operazioni numeriche e array
import librosa               # Per elaborazione audio
from tqdm import tqdm        # Per barre di progresso carine
import sys                   # Per gestire errori ed exit

# ==============================================================================
# CONFIGURAZIONE
# ==============================================================================

# Path delle cartelle (relative allo script)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__)) #os.path.dirname(os.path.abspath(__file__)) ottiene il percorso assoluto dello script corrente --> ADV_ML/scripts
PROJECT_DIR = os.path.dirname(SCRIPT_DIR) #os.path.dirname(SCRIPT_DIR) ottiene il percorso della cartella principale del progetto --> ASSAULTCUBE SERVER
DATASET_DIR = os.path.join(PROJECT_DIR, "dataset") #--> ASSAULTCUBE SERVER/ADV_ML/dataset
ORIGINAL_DIR = os.path.join(DATASET_DIR, "original") #--> ASSAULTCUBE SERVER/ADV_ML/dataset/original
OBFUSCATED_DIR = os.path.join(DATASET_DIR, "obfuscated") #--> ASSAULTCUBE SERVER/ADV_ML/dataset/obfuscated
OUTPUT_DIR = os.path.join(PROJECT_DIR, "features") #--> ASSAULTCUBE SERVER/ADV_ML/features

# Parametri per l'estrazione MFCC
SAMPLE_RATE = 22050          # Frequenza di campionamento (Hz)
                             # 22050 Hz è lo standard per audio processing
                             # (librosa ricampiona automaticamente a questo valore)

N_MFCC = 13                  # Numero di coefficienti MFCC da estrarre
                             # 13 è il valore standard (cattura bene il timbro)

HOP_LENGTH = 512             # Numero di sample tra frame successivi
                             # Più basso = più precisione temporale (ma più dati)

N_FFT = 2048                 # Dimensione della finestra FFT
                             # Potenza di 2 per efficienza computazionale

# Etichette (labels)
LABEL_ORIGINAL = 0           # 0 = file audio originale
LABEL_OBFUSCATED = 1         # 1 = file audio obfuscato (pitch shifted)

# ==============================================================================
# FUNZIONI HELPER
# ==============================================================================

def check_directories():
    """
    Verifica che le cartelle necessarie esistano.
    
    Se le cartelle del dataset non esistono, mostra un errore e termina.
    Se la cartella output non esiste, la crea.
    
    Returns:
        bool: True se tutto OK, altrimenti esce dal programma
    """
    # Controlla cartella original
    if not os.path.exists(ORIGINAL_DIR):
        print(f"❌ ERRORE: Cartella non trovata: {ORIGINAL_DIR}")
        print("   Crea la cartella e inserisci i file audio originali.")
        sys.exit(1)
    
    # Controlla cartella obfuscated
    if not os.path.exists(OBFUSCATED_DIR):
        print(f"❌ ERRORE: Cartella non trovata: {OBFUSCATED_DIR}")
        print("   Crea la cartella e inserisci i file audio modificati.")
        sys.exit(1)
    
    # Crea cartella output se non esiste
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"📁 Creata cartella: {OUTPUT_DIR}")
    
    return True


def load_audio_files(directory):
    """
    Carica tutti i file .wav da una cartella.
    
    Args:
        directory (str): Path della cartella da cui caricare i file
    
    Returns:
        list: Lista di path completi ai file .wav trovati
    """
    # glob.glob cerca tutti i file che matchano il pattern
    # os.path.join costruisce il path completo
    pattern = os.path.join(directory, "*.wav")
    files = glob.glob(pattern)
    
    # Ordina i file alfabeticamente per consistenza
    files.sort()
    
    return files


def extract_mfcc(audio_path):
    """
    Estrae i coefficienti MFCC da un file audio.
    
    COSA SONO LE MFCC?
    Le MFCC sono una rappresentazione compatta dell'audio che cattura
    le caratteristiche timbriche del suono. Invece di migliaia di sample,
    otteniamo pochi numeri che descrivono "com'è fatto" il suono.
    
    PROCESSO:
    1. Carica il file audio
    2. Calcola le MFCC con librosa
    3. Prende la media su tutti i frame temporali
    4. Restituisce un vettore di n_mfcc valori
    
    Args:
        audio_path (str): Path al file audio .wav
    
    Returns:
        np.ndarray: Array di shape (n_mfcc,) con i coefficienti MFCC medi
    
    Raises:
        Exception: Se il file non può essere caricato
    """
    try:
        # Carica il file audio
        # y = array con i sample audio (valori tra -1 e 1)
        # sr = sample rate (frequenza di campionamento)
        y, sr = librosa.load(audio_path, sr=SAMPLE_RATE)
        
        # Calcola le MFCC
        # Restituisce una matrice di shape (n_mfcc, n_frames)
        # Ogni colonna è un frame temporale
        mfcc = librosa.feature.mfcc(
            y=y,                    # Segnale audio
            sr=sr,                  # Sample rate
            n_mfcc=N_MFCC,          # Numero di coefficienti
            n_fft=N_FFT,            # Dimensione FFT
            hop_length=HOP_LENGTH   # Distanza tra frame
        )
        
        # Prende la media su tutti i frame temporali (axis=1)
        # Da (n_mfcc, n_frames) a (n_mfcc,)
        # Questo ci dà una rappresentazione "media" di tutto il file
        mfcc_mean = np.mean(mfcc, axis=1)
        
        return mfcc_mean
    
    except Exception as e:
        # Se c'è un errore, mostra quale file ha causato il problema
        print(f"\n❌ Errore nel processare {audio_path}")
        print(f"   Dettagli: {str(e)}")
        return None


def process_dataset(file_list, label, dataset_name):
    """
    Processa un intero dataset estraendo le MFCC da tutti i file.
    
    Args:
        file_list (list): Lista di path ai file audio
        label (int): Etichetta da assegnare (0 o 1)
        dataset_name (str): Nome del dataset (per visualizzazione)
    
    Returns:
        tuple: (features, labels)
            - features: lista di array MFCC
            - labels: lista di etichette
    """
    features = []  # Conterrà gli array MFCC
    labels = []    # Conterrà le etichette
    
    # tqdm crea una progress bar carina
    print(f"\n🔍 Processamento {dataset_name}...")
    for audio_path in tqdm(file_list, desc=dataset_name, unit="file"):
        # Estrae MFCC
        mfcc = extract_mfcc(audio_path)
        
        # Se l'estrazione ha avuto successo
        if mfcc is not None:
            features.append(mfcc)
            labels.append(label)
    
    return features, labels


# ==============================================================================
# FUNZIONE PRINCIPALE
# ==============================================================================

def main():
    """
    Funzione principale che coordina tutto il processo.
    
    FLUSSO:
    1. Verifica le cartelle
    2. Carica i file audio
    3. Estrae le MFCC
    4. Crea le matrici X e y
    5. Salva i risultati
    """
    
    # Banner iniziale
    print("=" * 80)
    print("🎵  EXTRACT FEATURES - MFCC Extraction per Audio AntiCheat")
    print("=" * 80)
    
    # ──────────────────────────────────────────────────────────────────────────
    # STEP 1: Verifica Ambiente
    # ──────────────────────────────────────────────────────────────────────────
    print("\n📋 STEP 1: Verifica cartelle...")
    check_directories()
    print("   ✓ Tutte le cartelle sono pronte")
    
    # ──────────────────────────────────────────────────────────────────────────
    # STEP 2: Caricamento File
    # ──────────────────────────────────────────────────────────────────────────
    print("\n📋 STEP 2: Caricamento file audio...")
    
    # Carica file originali
    original_files = load_audio_files(ORIGINAL_DIR)
    print(f"   ✓ Trovati {len(original_files)} file in original/")
    
    # Carica file obfuscati
    obfuscated_files = load_audio_files(OBFUSCATED_DIR)
    print(f"   ✓ Trovati {len(obfuscated_files)} file in obfuscated/")
    
    # Verifica che ci siano file
    if len(original_files) == 0 or len(obfuscated_files) == 0:
        print("\n❌ ERRORE: Devi avere almeno un file in ogni cartella!")
        print("   Aggiungi file .wav nelle cartelle dataset/original e dataset/obfuscated")
        sys.exit(1)
    
    total_files = len(original_files) + len(obfuscated_files)
    print(f"\n   📊 Totale file da processare: {total_files}")
    
    # ──────────────────────────────────────────────────────────────────────────
    # STEP 3: Estrazione MFCC
    # ──────────────────────────────────────────────────────────────────────────
    print("\n📋 STEP 3: Estrazione MFCC...")
    print(f"   Parametri: n_mfcc={N_MFCC}, sr={SAMPLE_RATE}Hz")
    
    # Processa dataset originali (label = 0)
    original_features, original_labels = process_dataset(
        original_files, 
        LABEL_ORIGINAL,
        "original"
    )
    
    # Processa dataset obfuscati (label = 1)
    obfuscated_features, obfuscated_labels = process_dataset(
        obfuscated_files,
        LABEL_OBFUSCATED,
        "obfuscated"
    )
    
    # ──────────────────────────────────────────────────────────────────────────
    # STEP 4: Creazione Matrici
    # ──────────────────────────────────────────────────────────────────────────
    print("\n📋 STEP 4: Creazione matrici X e y...")
    
    # Combina tutte le feature in una singola lista
    all_features = original_features + obfuscated_features
    all_labels = original_labels + obfuscated_labels
    
    # Converte le liste in array NumPy
    # X: matrice di shape (n_samples, n_features)
    # y: vettore di shape (n_samples,)
    X = np.array(all_features)
    y = np.array(all_labels)
    
    print(f"   ✓ X shape: {X.shape}  (samples × features)")
    print(f"   ✓ y shape: {y.shape}  (samples)")
    print(f"\n   📊 Distribuzione classi:")
    print(f"      - Original (0):   {np.sum(y == 0)} sample")
    print(f"      - Obfuscated (1): {np.sum(y == 1)} sample")
    
    # ──────────────────────────────────────────────────────────────────────────
    # STEP 5: Salvataggio
    # ──────────────────────────────────────────────────────────────────────────
    print("\n📋 STEP 5: Salvataggio feature...")
    
    # Path dei file output
    X_path = os.path.join(OUTPUT_DIR, "X.npy")
    y_path = os.path.join(OUTPUT_DIR, "y.npy")
    
    # Salva gli array in formato NumPy
    # .npy è efficiente e mantiene il tipo di dato
    np.save(X_path, X)
    np.save(y_path, y)
    
    print(f"   ✓ Salvato: {X_path}")
    print(f"   ✓ Salvato: {y_path}")
    
    # ──────────────────────────────────────────────────────────────────────────
    # COMPLETATO
    # ──────────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("✅ ESTRAZIONE COMPLETATA CON SUCCESSO!")
    print("=" * 80)
    print("\n📝 Prossimi step:")
    print("   1. Verifica che i file X.npy e y.npy esistano nella cartella features/")
    print("   2. Procedi con train_classifier.py per addestrare il modello")
    print("\n💡 Tip: Puoi caricare i dati con:")
    print("   X = np.load('features/X.npy')")
    print("   y = np.load('features/y.npy')")
    print()


# ==============================================================================
# ENTRY POINT
# ==============================================================================

if __name__ == "__main__":
    """
    Questo blocco viene eseguito solo quando lo script è lanciato direttamente.
    
    Se questo file viene importato da un altro script, main() non viene chiamata.
    """
    try:
        main()
    except KeyboardInterrupt:
        # Se l'utente preme Ctrl+C, esce in modo pulito
        print("\n\n⚠️  Processo interrotto dall'utente.")
        print("   I file potrebbero essere incompleti.")
        sys.exit(0)
    except Exception as e:
        # Se c'è un errore non gestito, mostralo
        print(f"\n\n❌ ERRORE CRITICO: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

