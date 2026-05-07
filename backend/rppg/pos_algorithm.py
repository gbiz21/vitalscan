"""
Task 2 — POS Algorithm + Bandpass + FFT for Heart Rate
======================================================

Takes the RGB time-series from Task 1 and extracts the heart rate.

The "tune the radio" analogy from class:
  - The RGB time-series contains the heart-rate signal mixed with noise
    (lighting, head motion, skin color drift)
  - Bandpass filter = tuning the dial to only frequencies where heartbeats
    live (0.7-4.0 Hz, equivalent to 42-240 BPM)
  - FFT = reading what station is playing (the dominant frequency = HR)

The POS (Plane Orthogonal to Skin) algorithm is a classical technique that
projects the RGB signal onto a plane orthogonal to the skin-tone vector,
suppressing motion and lighting artifacts that affect all three channels
equally while preserving the pulse signal.

Reference: Wang et al. (2017) "Algorithmic Principles of Remote PPG"
"""

from typing import Tuple

import numpy as np
from scipy.signal import butter, filtfilt


def pos_algorithm(rgb_signal: np.ndarray, fps: float, window_seconds: float = 1.6) -> np.ndarray:
    """
    Apply the POS algorithm to extract a pulse signal from RGB time-series.

    Args:
        rgb_signal: shape (n_frames, 3), the per-frame mean RGB
        fps: video frame rate
        window_seconds: sliding window length (1.6s is the original POS paper value)

    Returns:
        pulse_signal: 1D array of the recovered pulse waveform
    """
    n = rgb_signal.shape[0]
    window_size = int(window_seconds * fps)

    if n < window_size:
        raise ValueError(f"Need at least {window_size} frames for POS, got {n}")

    pulse = np.zeros(n)

    # The POS projection matrix: maps RGB -> 2D plane orthogonal to skin tone
    # H = [[0, 1, -1], [-2, 1, 1]] is the standard POS projection
    projection = np.array([[0, 1, -1], [-2, 1, 1]])

    for t in range(window_size, n):
        # Take the most recent window of frames
        window = rgb_signal[t - window_size : t]

        # Temporal normalization: divide each channel by its own mean
        # (removes the DC component that varies slowly with lighting)
        mean_rgb = np.mean(window, axis=0)
        if np.any(mean_rgb == 0):
            continue
        normalized = window / mean_rgb

        # Project onto the 2D POS plane
        # Shape: (window_size, 3) @ (3, 2) -> (window_size, 2)
        s = normalized @ projection.T

        # Combine the two projected channels with adaptive scaling
        std_ratio = np.std(s[:, 0]) / (np.std(s[:, 1]) + 1e-9)
        h = s[:, 0] + std_ratio * s[:, 1]

        # Subtract mean and accumulate (overlap-add)
        h = h - np.mean(h)
        pulse[t - window_size : t] += h

    return pulse


def butter_bandpass(
    signal: np.ndarray,
    fps: float,
    low_hz: float = 0.7,
    high_hz: float = 4.0,
    order: int = 3,
) -> np.ndarray:
    """
    Butterworth bandpass filter in the heart rate band.

    0.7 Hz = 42 BPM (lower bound of normal HR)
    4.0 Hz = 240 BPM (upper bound, accommodates exercise)
    """
    nyquist = fps / 2.0
    low = low_hz / nyquist
    high = high_hz / nyquist
    b, a = butter(order, [low, high], btype="band")
    # filtfilt = zero-phase filtering (forward + backward pass), avoids time shift
    return filtfilt(b, a, signal)


def estimate_heart_rate_fft(
    pulse_signal: np.ndarray,
    fps: float,
    low_bpm: float = 60.0,
    high_bpm: float = 210.0,
) -> Tuple[float, np.ndarray, np.ndarray]:
    # Tightened from 42-240 BPM after SCAMPS evaluation showed synthetic
    # facial animation dominates the FFT in the 42-60 BPM band. The 60-210
    # range covers WHO-defined normal adult resting HR through vigorous
    # exercise. See docs/evaluation_results.md for the tuning study.
    """
    Find the dominant frequency in the valid HR band via FFT.

    Returns:
        heart_rate_bpm: estimated heart rate in BPM
        freqs: frequency axis (for plotting / debugging)
        magnitudes: FFT magnitude spectrum
    """
    n = len(pulse_signal)
    # Zero-pad to next power of 2 for finer frequency resolution
    n_padded = 2 ** int(np.ceil(np.log2(n))) * 4

    fft_vals = np.fft.rfft(pulse_signal, n=n_padded)
    freqs = np.fft.rfftfreq(n_padded, d=1.0 / fps)
    magnitudes = np.abs(fft_vals)

    # Restrict the search to the valid HR band
    low_hz = low_bpm / 60.0
    high_hz = high_bpm / 60.0
    valid = (freqs >= low_hz) & (freqs <= high_hz)

    if not np.any(valid):
        raise ValueError("No frequencies found in valid HR band")

    valid_indices = np.where(valid)[0]
    peak_idx = valid_indices[np.argmax(magnitudes[valid_indices])]
    peak_freq_hz = freqs[peak_idx]
    heart_rate_bpm = peak_freq_hz * 60.0

    return heart_rate_bpm, freqs, magnitudes


def extract_heart_rate(rgb_signal: np.ndarray, fps: float) -> Tuple[float, np.ndarray]:
    """
    Full Task 2 pipeline: RGB time-series -> heart rate.

    Returns:
        heart_rate_bpm: estimated heart rate
        filtered_pulse: the bandpass-filtered pulse waveform (used by Task 3)
    """
    pulse = pos_algorithm(rgb_signal, fps)
    filtered = butter_bandpass(pulse, fps)
    heart_rate_bpm, _, _ = estimate_heart_rate_fft(filtered, fps)
    return heart_rate_bpm, filtered
