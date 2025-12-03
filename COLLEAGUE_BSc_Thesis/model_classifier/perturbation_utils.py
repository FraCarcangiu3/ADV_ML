#!/usr/bin/env python3
"""
perturbation_utils.py

Funzioni di utilità per applicare perturbazioni audio ai waveform.
Wrapper per ADV_ML/audio_effects.py con preset calibrati per weapon/usp.

Autore: Francesco Carcangiu
"""

import sys
from pathlib import Path
from typing import Dict

import numpy as np

# Aggiungi ADV_ML al path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "ADV_ML"))

try:
    import audio_effects
except ImportError:
    raise ImportError(
        "Non riesco a importare ADV_ML/audio_effects.py. "
        "Verifica che ADV_ML/ sia nella root del progetto."
    )


# ============================================================================
# PRESET DI PERTURBAZIONE (calibrati per weapon/usp dal client C++)
# ============================================================================

PERTURB_PRESETS = {
    # Pitch shift (cents)
    "pitch_P1_pos": {"type": "pitch", "cents": +100.0},
    "pitch_P2_pos": {"type": "pitch", "cents": +150.0},
    "pitch_P3_pos": {"type": "pitch", "cents": +200.0},
    "pitch_P1_neg": {"type": "pitch", "cents": -100.0},
    "pitch_P2_neg": {"type": "pitch", "cents": -150.0},
    "pitch_P3_neg": {"type": "pitch", "cents": -200.0},
    
    # White noise (SNR in dB)
    "white_W1": {"type": "white_noise", "snr_db": 42.0},  # light
    "white_W2": {"type": "white_noise", "snr_db": 40.0},  # medium
    "white_W3": {"type": "white_noise", "snr_db": 38.0},  # strong
    
    # Pink noise (SNR in dB)
    "pink_K1": {"type": "pink_noise", "snr_db": 22.0},  # light
    "pink_K2": {"type": "pink_noise", "snr_db": 20.0},  # medium
    "pink_K3": {"type": "pink_noise", "snr_db": 18.0},  # strong
    
    # EQ tilt (dB)
    "eq_boost_light": {"type": "eq_tilt", "tilt_db": +3.0},
    "eq_boost_medium": {"type": "eq_tilt", "tilt_db": +4.5},
    "eq_boost_strong": {"type": "eq_tilt", "tilt_db": +6.0},
    "eq_cut_light": {"type": "eq_tilt", "tilt_db": -3.0},
    "eq_cut_medium": {"type": "eq_tilt", "tilt_db": -6.0},
    "eq_cut_strong": {"type": "eq_tilt", "tilt_db": -9.0},
    
    # High-pass filter (Hz)
    "hp_150": {"type": "highpass", "cutoff_hz": 150},
    "hp_200": {"type": "highpass", "cutoff_hz": 200},
    "hp_250": {"type": "highpass", "cutoff_hz": 250},
    
    # Low-pass filter (Hz)
    "lp_8000": {"type": "lowpass", "cutoff_hz": 8000},
    "lp_10000": {"type": "lowpass", "cutoff_hz": 10000},
    "lp_12000": {"type": "lowpass", "cutoff_hz": 12000},
    
    # ========================================================================
    # NUOVI EFFETTI SPAZIALI (per disturbare IPD/ILD)
    # ========================================================================
    
    # Spatial delay — micro-delay tra canali (disturba IPD)
    "spatial_delay_light": {"type": "spatial_delay", "max_samples": 2},    # ~0.02ms @ 96kHz
    "spatial_delay_medium": {"type": "spatial_delay", "max_samples": 5},   # ~0.05ms @ 96kHz
    "spatial_delay_strong": {"type": "spatial_delay", "max_samples": 10},  # ~0.1ms @ 96kHz
    
    # Channel gain jitter — variazioni di gain per canale (disturba ILD)
    "gain_jitter_light": {"type": "gain_jitter", "max_db": 0.5},   # Molto sottile
    "gain_jitter_medium": {"type": "gain_jitter", "max_db": 1.0},  # Sottile
    "gain_jitter_strong": {"type": "gain_jitter", "max_db": 1.5},  # Percettibile
    
    # Multi-channel white noise — rumore indipendente per canale
    "multi_white_light": {"type": "multi_noise", "noise_subtype": "white", "snr_db": 42.0},
    "multi_white_medium": {"type": "multi_noise", "noise_subtype": "white", "snr_db": 40.0},
    "multi_white_strong": {"type": "multi_noise", "noise_subtype": "white", "snr_db": 38.0},
    
    # Multi-channel pink noise — rumore indipendente per canale
    "multi_pink_light": {"type": "multi_noise", "noise_subtype": "pink", "snr_db": 22.0},
    "multi_pink_medium": {"type": "multi_noise", "noise_subtype": "pink", "snr_db": 20.0},
    "multi_pink_strong": {"type": "multi_noise", "noise_subtype": "pink", "snr_db": 18.0},
}


def apply_perturbation_waveform(
    waveform: np.ndarray,
    sr: int,
    preset_name: str
) -> np.ndarray:
    """
    Applica perturbazione audio al waveform prima della feature extraction.
    
    Args:
        waveform: Array numpy [frames, channels] o [channels, frames]
                  Shape tipica: (n_samples, 8) per audio multicanale
        sr: Sample rate in Hz (tipicamente 96000)
        preset_name: Nome preset (es. 'pitch_P2_pos', 'white_W2', 'pink_K2')
    
    Returns:
        Waveform perturbato (stessa shape di input)
    
    Raises:
        ValueError: Se preset_name non è riconosciuto
    """
    if preset_name not in PERTURB_PRESETS:
        raise ValueError(
            f"Preset '{preset_name}' non riconosciuto. "
            f"Preset disponibili: {list(PERTURB_PRESETS.keys())}"
        )
    
    config = PERTURB_PRESETS[preset_name]
    pert_type = config["type"]
    
    # Normalizza shape: assicurati che sia (frames, channels)
    original_shape = waveform.shape
    if waveform.ndim == 1:
        waveform = waveform.reshape(-1, 1)
    elif waveform.ndim == 2 and waveform.shape[0] < waveform.shape[1]:
        # Se è (channels, frames), trasponi
        waveform = waveform.T
    
    # Applica perturbazione
    if pert_type == "pitch":
        cents = config["cents"]
        perturbed = audio_effects.apply_pitch_shift(waveform, sr, cents)
    
    elif pert_type == "white_noise":
        snr_db = config["snr_db"]
        perturbed = audio_effects.add_white_noise(waveform, snr_db)
    
    elif pert_type == "pink_noise":
        snr_db = config["snr_db"]
        perturbed = audio_effects.add_pink_noise(waveform, snr_db)
    
    elif pert_type == "eq_tilt":
        tilt_db = config["tilt_db"]
        perturbed = audio_effects.apply_eq_tilt(waveform, sr, tilt_db)
    
    elif pert_type == "highpass":
        cutoff_hz = config["cutoff_hz"]
        perturbed = audio_effects.apply_highpass(waveform, sr, cutoff_hz)
    
    elif pert_type == "lowpass":
        cutoff_hz = config["cutoff_hz"]
        perturbed = audio_effects.apply_lowpass(waveform, sr, cutoff_hz)
    
    elif pert_type == "spatial_delay":
        max_samples = config["max_samples"]
        perturbed = audio_effects.apply_spatial_delay(waveform, sr, max_samples)
    
    elif pert_type == "gain_jitter":
        max_db = config["max_db"]
        perturbed = audio_effects.apply_channel_gain_jitter(waveform, max_db)
    
    elif pert_type == "multi_noise":
        snr_db = config["snr_db"]
        noise_subtype = config.get("noise_subtype", "white")
        perturbed = audio_effects.apply_multi_channel_noise(waveform, snr_db, noise_subtype)
    
    else:
        raise ValueError(f"Tipo di perturbazione sconosciuto: {pert_type}")
    
    # Ripristina shape originale se necessario
    if original_shape != perturbed.shape:
        if len(original_shape) == 1:
            perturbed = perturbed.flatten()
        elif original_shape[0] < original_shape[1]:
            # Era (channels, frames), ripristina
            perturbed = perturbed.T
    
    return perturbed


def get_preset_config(preset_name: str) -> Dict:
    """
    Restituisce configurazione di un preset.
    
    Args:
        preset_name: Nome preset
    
    Returns:
        Dict con tipo e parametri della perturbazione
    """
    if preset_name not in PERTURB_PRESETS:
        raise ValueError(f"Preset '{preset_name}' non riconosciuto")
    return PERTURB_PRESETS[preset_name].copy()


def list_available_presets() -> list:
    """Restituisce lista di tutti i preset disponibili."""
    return list(PERTURB_PRESETS.keys())

