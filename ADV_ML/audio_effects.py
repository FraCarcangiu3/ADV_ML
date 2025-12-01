"""
audio_effects.py
Modulo Python per replicare gli effetti audio del client C++ in modo offline.

Questo modulo contiene funzioni pure che lavorano su array NumPy per applicare
le stesse perturbazioni audio implementate nel client C++ (audio_runtime_obf.cpp).

Effetti supportati:
- Pitch shift (in cents, usando librosa)
- White noise (SNR in dB)
- Pink noise (SNR in dB, filtro 1/f approssimato)
- EQ tilt (high-shelf filter)
- High-pass filter (Butterworth 2° ordine)
- Low-pass filter (Butterworth 2° ordine)

Autore: Francesco Carcangiu
Data: 2024-11-21
"""

import numpy as np
from scipy import signal as scipy_signal
from typing import Literal

# ========================================================================
# Helper: Calcolo RMS
# ========================================================================

def calculate_rms(samples: np.ndarray) -> float:
    """
    Calcola RMS (Root Mean Square) del segnale.
    
    Replica la logica del client C++:
        RMS = sqrt(sum(samples^2) / count)
    
    Args:
        samples: Array numpy 1D o 2D (se 2D, calcola RMS su tutti i valori)
    
    Returns:
        Valore RMS
    """
    if samples.size == 0:
        return 0.0
    
    # Flatten se multi-dimensionale
    flat = samples.flatten()
    return np.sqrt(np.mean(flat ** 2))


# ========================================================================
# Pitch Shift
# ========================================================================

def apply_pitch_shift(signal: np.ndarray, sr: int, cents: float) -> np.ndarray:
    """
    Applica pitch shift usando librosa (equivalente a SoundTouch nel client C++).
    
    Nel client C++:
        - Usa SoundTouch library
        - Converte cents in semitoni: semitones = cents / 100.0
        - Applica pitch shift preservando durata
    
    Args:
        signal: Array numpy audio [frames, channels] o [frames]
        sr: Sample rate in Hz
        cents: Pitch shift in cents (100 cents = 1 semitono)
                Range tipico: [-200, -75] ∪ [75, 200] (dead zone ±75 esclusa)
    
    Returns:
        Segnale con pitch shift applicato (stessa shape di input)
    """
    if cents == 0:
        return signal.copy()
    
    try:
        import librosa
    except ImportError:
        raise ImportError(
            "librosa è necessario per pitch shift. Installa con: pip install librosa"
        )
    
    # Converti cents in semitoni (come nel client C++)
    semitones = cents / 100.0
    
    # Gestisci mono vs multi-canale
    if signal.ndim == 1:
        # Mono: applica direttamente
        shifted = librosa.effects.pitch_shift(
            y=signal,
            sr=sr,
            n_steps=semitones,
            bins_per_octave=12  # Standard: 12 semitoni per ottava
        )
        return shifted
    else:
        # Multi-canale: applica a ogni canale separatamente
        channels = signal.shape[1] if signal.ndim == 2 else 1
        if signal.ndim == 2:
            original_length = signal.shape[0]
            shifted_channels = []
            for ch in range(channels):
                shifted_ch = librosa.effects.pitch_shift(
                    y=signal[:, ch],
                    sr=sr,
                    n_steps=semitones,
                    bins_per_octave=12
                )
                shifted_channels.append(shifted_ch)
            
            # Allinea ogni canale alla lunghezza originale (non usare min_len!)
            # Questo evita di troncare tutti i canali alla lunghezza del più corto
            aligned_channels = []
            for ch in range(channels):
                ch_data = shifted_channels[ch]
                if len(ch_data) < original_length:
                    # Zero-pad se più corto
                    pad = np.zeros(original_length - len(ch_data))
                    ch_data = np.concatenate([ch_data, pad])
                elif len(ch_data) > original_length:
                    # Tronca se più lungo
                    ch_data = ch_data[:original_length]
                aligned_channels.append(ch_data)
            
            # Costruisci array finale
            shifted = np.array(aligned_channels).T
            
            return shifted
    return signal.copy()


# ========================================================================
# White Noise
# ========================================================================

def add_white_noise(signal: np.ndarray, snr_db: float, seed: int | None = None, only_on_signal: bool = True, threshold: float = 1e-4) -> np.ndarray:
    """
    Aggiunge white noise con SNR target (dB).
    
    Replica la logica del client C++:
        1. Calcola RMS del segnale
        2. Calcola RMS target del rumore: RMS_noise = RMS_signal / (10^(SNR/20))
        3. Genera rumore uniforme [-1, 1] con RMS teorico ≈ 1/√3 ≈ 0.577
        4. Scala il rumore per ottenere SNR corretto
        5. Aggiungi rumore al segnale con clipping
    
    Args:
        signal: Array numpy audio [frames, channels] o [frames]
        snr_db: Target SNR in dB (es. 35.0, 40.0, 45.0)
        seed: Seed per RNG (None = random, utile per riproducibilità)
        only_on_signal: Se True, applica rumore SOLO dove c'è segnale (non sul silenzio)
                        Questo simula il comportamento reale: il rumore viene aggiunto
                        solo durante lo sparo, non nel silenzio
        threshold: Soglia per considerare un sample come "silenzio" (default: 1e-4)
    
    Returns:
        Segnale con white noise aggiunto (stessa shape di input)
    """
    if snr_db <= 0:
        return signal.copy()
    
    # Calcola RMS del segnale
    rms_signal = calculate_rms(signal)
    if rms_signal < 1e-6:
        return signal.copy()  # Segnale troppo debole
    
    # Calcola RMS target del rumore: SNR = 20 * log10(RMS_signal / RMS_noise)
    # Quindi: RMS_noise = RMS_signal / (10^(SNR/20))
    target_rms_noise = rms_signal / (10.0 ** (snr_db / 20.0))
    
    # RMS teorico di rumore uniforme [-1, 1] = 1/√3 ≈ 0.577
    rms_uniform_noise = 1.0 / np.sqrt(3.0)
    
    # Ampiezza del rumore per ottenere RMS target
    noise_amplitude = target_rms_noise / rms_uniform_noise
    
    # Genera white noise uniforme [-1, 1]
    rng = np.random.RandomState(seed) if seed is not None else np.random
    noise_shape = signal.shape
    white_noise = rng.uniform(-1.0, 1.0, size=noise_shape) * noise_amplitude
    
    # Se only_on_signal=True, applica rumore SOLO dove c'è segnale
    if only_on_signal:
        # Crea maschera: True dove c'è segnale, False dove c'è silenzio
        signal_mask = np.abs(signal) > threshold
        # Azzera il rumore dove c'è silenzio
        white_noise = white_noise * signal_mask
    
    # Aggiungi rumore
    result = signal + white_noise
    
    # Clipping (come nel client C++)
    result = np.clip(result, -1.0, 1.0)
    
    return result


# ========================================================================
# Pink Noise
# ========================================================================

def add_pink_noise(signal: np.ndarray, snr_db: float, seed: int | None = None, only_on_signal: bool = True, threshold: float = 1e-4) -> np.ndarray:
    """
    Aggiunge pink noise (1/f filtered white noise) con SNR target (dB).
    
    Replica la logica del client C++:
        1. Genera white noise uniforme
        2. Applica filtro IIR semplice per approssimare 1/f:
           y[n] = 0.99 * y[n-1] + (1 - 0.99) * x[n]
        3. Normalizza per mantenere stessa RMS del white originale
        4. Scala per ottenere SNR target
        5. Aggiungi al segnale con clipping
    
    Args:
        signal: Array numpy audio [frames, channels] o [frames]
        snr_db: Target SNR in dB
        seed: Seed per RNG (None = random)
        only_on_signal: Se True, applica rumore SOLO dove c'è segnale (non sul silenzio)
                        Questo simula il comportamento reale: il rumore viene aggiunto
                        solo durante lo sparo, non nel silenzio
        threshold: Soglia per considerare un sample come "silenzio" (default: 1e-4)
    
    Returns:
        Segnale con pink noise aggiunto (stessa shape di input)
    """
    if snr_db <= 0:
        return signal.copy()
    
    # Calcola RMS del segnale
    rms_signal = calculate_rms(signal)
    if rms_signal < 1e-6:
        return signal.copy()
    
    # Calcola ampiezza target del rumore
    target_rms_noise = rms_signal / (10.0 ** (snr_db / 20.0))
    
    # Genera white noise
    rng = np.random.RandomState(seed) if seed is not None else np.random
    noise_shape = signal.shape
    white_noise = rng.uniform(-1.0, 1.0, size=noise_shape)
    
    # Applica filtro 1/f semplice (come nel client C++)
    # y[n] = alpha * y[n-1] + (1 - alpha) * x[n]
    alpha = 0.99
    pink_noise = np.zeros_like(white_noise)
    
    if white_noise.ndim == 1:
        # Mono
        y_prev = 0.0
        for i in range(len(white_noise)):
            y_prev = alpha * y_prev + (1.0 - alpha) * white_noise[i]
            pink_noise[i] = y_prev
    else:
        # Multi-canale: applica filtro per ogni canale
        for ch in range(white_noise.shape[1]):
            y_prev = 0.0
            for i in range(white_noise.shape[0]):
                y_prev = alpha * y_prev + (1.0 - alpha) * white_noise[i, ch]
                pink_noise[i, ch] = y_prev
    
    # Normalizza pink per avere stessa RMS del white originale
    rms_pink = calculate_rms(pink_noise)
    if rms_pink > 1e-6:
        scale = target_rms_noise / rms_pink
        pink_noise = pink_noise * scale
    
    # Se only_on_signal=True, applica rumore SOLO dove c'è segnale
    if only_on_signal:
        # Crea maschera: True dove c'è segnale, False dove c'è silenzio
        signal_mask = np.abs(signal) > threshold
        # Azzera il rumore dove c'è silenzio
        pink_noise = pink_noise * signal_mask
    
    # Aggiungi al segnale
    result = signal + pink_noise
    
    # Clipping
    result = np.clip(result, -1.0, 1.0)
    
    return result


# ========================================================================
# EQ Tilt (High-Shelf Filter)
# ========================================================================

def apply_eq_tilt(signal: np.ndarray, sr: int, tilt_db: float) -> np.ndarray:
    """
    Applica EQ tilt usando high-shelf filter @ 2kHz (come nel client C++).
    
    Nel client C++:
        - Shelf frequency = 2000 Hz
        - Gain factor A = 10^(tilt_db / 40.0)
        - Usa filtro biquad high-shelf
    
    Args:
        signal: Array numpy audio [frames, channels] o [frames]
        sr: Sample rate in Hz
        tilt_db: Tilt in dB (positivo = brighten, negativo = darken)
                 Range tipico: [-6, -3] (cut) o [3, 6] (boost)
    
    Returns:
        Segnale con EQ tilt applicato (stessa shape di input)
    """
    if abs(tilt_db) < 0.1:
        return signal.copy()
    
    # Shelf frequency = 2000 Hz (come nel client C++)
    shelf_freq = 2000.0
    
    # Gain factor (come nel client C++)
    A = 10.0 ** (tilt_db / 40.0)
    
    # Calcola coefficienti biquad high-shelf
    # Replica la formula del client C++
    omega = 2.0 * np.pi * shelf_freq / sr
    cos_w = np.cos(omega)
    sin_w = np.sin(omega)
    Q = 0.707  # Butterworth
    alpha = sin_w / (2.0 * Q)
    
    a0 = (A + 1.0) - (A - 1.0) * cos_w + 2.0 * np.sqrt(A) * alpha
    b0 = A * ((A + 1.0) + (A - 1.0) * cos_w + 2.0 * np.sqrt(A) * alpha)
    b1 = -2.0 * A * ((A - 1.0) + (A + 1.0) * cos_w)
    b2 = A * ((A + 1.0) + (A - 1.0) * cos_w - 2.0 * np.sqrt(A) * alpha)
    a1 = 2.0 * ((A - 1.0) - (A + 1.0) * cos_w)
    a2 = (A + 1.0) - (A - 1.0) * cos_w - 2.0 * np.sqrt(A) * alpha
    
    # Normalizza coefficienti (a0 = 1)
    b0 /= a0
    b1 /= a0
    b2 /= a0
    a1 /= a0
    a2 /= a0
    
    # Applica filtro biquad
    sos = scipy_signal.tf2sos([b0, b1, b2], [1.0, a1, a2])
    
    if signal.ndim == 1:
        # Mono
        filtered = scipy_signal.sosfilt(sos, signal)
    else:
        # Multi-canale: applica a ogni canale
        filtered = np.zeros_like(signal)
        for ch in range(signal.shape[1]):
            filtered[:, ch] = scipy_signal.sosfilt(sos, signal[:, ch])
    
    return filtered


# ========================================================================
# High-Pass Filter (Butterworth 2° ordine)
# ========================================================================

def apply_highpass(signal: np.ndarray, sr: int, cutoff_hz: float) -> np.ndarray:
    """
    Applica high-pass filter Butterworth 2° ordine.
    
    Replica la logica del client C++:
        - Butterworth 2° ordine
        - Q = 0.707
        - Usa filtro biquad
    
    Args:
        signal: Array numpy audio [frames, channels] o [frames]
        sr: Sample rate in Hz
        cutoff_hz: Frequenza di taglio in Hz (range tipico: 100-500 Hz)
    
    Returns:
        Segnale filtrato (stessa shape di input)
    """
    if cutoff_hz <= 0 or cutoff_hz >= sr / 2:
        return signal.copy()
    
    # Calcola coefficienti Butterworth HP (come nel client C++)
    Q = 0.707  # Butterworth
    omega = 2.0 * np.pi * cutoff_hz / sr
    cos_w = np.cos(omega)
    sin_w = np.sin(omega)
    alpha = sin_w / (2.0 * Q)
    
    a0 = 1.0 + alpha
    
    # Coefficienti HP
    b0 = (1.0 + cos_w) / (2.0 * a0)
    b1 = -(1.0 + cos_w) / a0
    b2 = (1.0 + cos_w) / (2.0 * a0)
    a1 = (-2.0 * cos_w) / a0
    a2 = (1.0 - alpha) / a0
    
    # Applica filtro biquad
    sos = scipy_signal.tf2sos([b0, b1, b2], [1.0, a1, a2])
    
    if signal.ndim == 1:
        filtered = scipy_signal.sosfilt(sos, signal)
    else:
        filtered = np.zeros_like(signal)
        for ch in range(signal.shape[1]):
            filtered[:, ch] = scipy_signal.sosfilt(sos, signal[:, ch])
    
    return filtered


# ========================================================================
# Low-Pass Filter (Butterworth 2° ordine)
# ========================================================================

def apply_lowpass(signal: np.ndarray, sr: int, cutoff_hz: float) -> np.ndarray:
    """
    Applica low-pass filter Butterworth 2° ordine.
    
    Replica la logica del client C++:
        - Butterworth 2° ordine
        - Q = 0.707
        - Usa filtro biquad
    
    Args:
        signal: Array numpy audio [frames, channels] o [frames]
        sr: Sample rate in Hz
        cutoff_hz: Frequenza di taglio in Hz (range tipico: 8000-16000 Hz)
    
    Returns:
        Segnale filtrato (stessa shape di input)
    """
    if cutoff_hz <= 0 or cutoff_hz >= sr / 2:
        return signal.copy()
    
    # Calcola coefficienti Butterworth LP (come nel client C++)
    Q = 0.707  # Butterworth
    omega = 2.0 * np.pi * cutoff_hz / sr
    cos_w = np.cos(omega)
    sin_w = np.sin(omega)
    alpha = sin_w / (2.0 * Q)
    
    a0 = 1.0 + alpha
    
    # Coefficienti LP
    b0 = (1.0 - cos_w) / (2.0 * a0)
    b1 = (1.0 - cos_w) / a0
    b2 = (1.0 - cos_w) / (2.0 * a0)
    a1 = (-2.0 * cos_w) / a0
    a2 = (1.0 - alpha) / a0
    
    # Applica filtro biquad
    sos = scipy_signal.tf2sos([b0, b1, b2], [1.0, a1, a2])
    
    if signal.ndim == 1:
        filtered = scipy_signal.sosfilt(sos, signal)
    else:
        filtered = np.zeros_like(signal)
        for ch in range(signal.shape[1]):
            filtered[:, ch] = scipy_signal.sosfilt(sos, signal[:, ch])
    
    return filtered


# ========================================================================
# Funzioni di Randomizzazione (replica logica client C++)
# ========================================================================

def sample_pitch_from_range(
    min_cents: float,
    max_cents: float,
    mode: Literal["uniform", "gaussian"] = "uniform",
    seed: int | None = None
) -> float:
    """
    Genera pitch shift casuale con distribuzione uniforme (replica client C++).
    
    Nel client C++ (Step 3):
        - Range: [-200..-75] ∪ [75..200] (escluso dead zone ±75)
        - Distribuzione: UNIFORME per massima variabilità (anti-ML)
        - 50% probabilità negativo, 50% positivo
    
    Args:
        min_cents: Minimo pitch (es. -200)
        max_cents: Massimo pitch (es. 200)
        mode: Tipo di distribuzione ("uniform" replica il client)
        seed: Seed per RNG
    
    Returns:
        Pitch shift in cents
    """
    if min_cents == 0 and max_cents == 0:
        return 0.0
    if min_cents == max_cents:
        return min_cents
    
    rng = np.random.RandomState(seed) if seed is not None else np.random
    
    # Dead zone: escludi [-75, 75] (come nel client C++)
    DEAD_ZONE = 75
    
    if mode == "uniform":
        # 50% probabilità negativo, 50% positivo
        if rng.random() < 0.5:
            # Negativo: uniforme in [min_cents, -DEAD_ZONE]
            return rng.uniform(min_cents, -DEAD_ZONE)
        else:
            # Positivo: uniforme in [DEAD_ZONE, max_cents]
            return rng.uniform(DEAD_ZONE, max_cents)
    else:
        # Gaussian (non usato nel client, ma utile per test)
        mean = (min_cents + max_cents) / 2.0
        std = (max_cents - min_cents) / 6.0  # 3-sigma range
        return np.clip(rng.normal(mean, std), min_cents, max_cents)


def sample_snr_from_range(
    min_snr: float,
    max_snr: float,
    seed: int | None = None
) -> float:
    """
    Genera SNR casuale con distribuzione uniforme (replica client C++).
    
    Nel client C++:
        - Distribuzione: UNIFORME nel range [min, max]
        - Ogni valore equiprobabile
    
    Args:
        min_snr: Minimo SNR (dB)
        max_snr: Massimo SNR (dB)
        seed: Seed per RNG
    
    Returns:
        SNR in dB
    """
    if min_snr == 0.0 and max_snr == 0.0:
        return 0.0
    if min_snr == max_snr:
        return min_snr
    
    rng = np.random.RandomState(seed) if seed is not None else np.random
    return rng.uniform(min_snr, max_snr)


def sample_eq_tilt_from_range(
    boost_min: float,
    boost_max: float,
    cut_min: float,
    cut_max: float,
    mode: Literal["boost", "cut", "random"] = "random",
    seed: int | None = None
) -> float:
    """
    Genera EQ tilt casuale (replica client C++).
    
    Nel client C++:
        - Se mode="random": 50% boost, 50% cut
        - Se mode="boost": uniforme in [boost_min, boost_max]
        - Se mode="cut": uniforme in [cut_min, cut_max] (valori negativi)
    
    Args:
        boost_min: Minimo boost (dB, positivo)
        boost_max: Massimo boost (dB, positivo)
        cut_min: Minimo cut (dB, negativo)
        cut_max: Massimo cut (dB, negativo)
        mode: Modalità ("random", "boost", "cut")
        seed: Seed per RNG
    
    Returns:
        EQ tilt in dB
    """
    rng = np.random.RandomState(seed) if seed is not None else np.random
    
    if mode == "random":
        # 50% boost, 50% cut (come nel client C++)
        if rng.random() < 0.5:
            return rng.uniform(boost_min, boost_max)
        else:
            return rng.uniform(cut_min, cut_max)
    elif mode == "boost":
        return rng.uniform(boost_min, boost_max)
    elif mode == "cut":
        return rng.uniform(cut_min, cut_max)
    else:
        return 0.0


def sample_filter_cutoff_from_range(
    min_hz: float,
    max_hz: float,
    seed: int | None = None
) -> float:
    """
    Genera frequenza di taglio casuale con distribuzione uniforme.
    
    Args:
        min_hz: Minimo cutoff (Hz)
        max_hz: Massimo cutoff (Hz)
        seed: Seed per RNG
    
    Returns:
        Frequenza di taglio in Hz
    """
    if min_hz == 0.0 and max_hz == 0.0:
        return 0.0
    if min_hz == max_hz:
        return min_hz
    
    rng = np.random.RandomState(seed) if seed is not None else np.random
    return rng.uniform(min_hz, max_hz)

