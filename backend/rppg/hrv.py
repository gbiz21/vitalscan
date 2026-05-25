"""
Task 3 — HRV and Stress Index Extraction
========================================

Takes the filtered pulse waveform from Task 2 and computes:
  - SDNN (Standard Deviation of Normal-to-Normal intervals): the HRV metric
  - Stress index: derived from the LF/HF power ratio

Background: HRV (heart rate variability) measures the small variations in
time between consecutive heartbeats. Counterintuitively, HIGH variability
is HEALTHY — it indicates good autonomic nervous system function and the
body responding well to its environment. Low HRV correlates with stress,
fatigue, and disease.

The two key frequency bands of HRV:
  - LF (Low Frequency, 0.04-0.15 Hz): mix of sympathetic + parasympathetic
  - HF (High Frequency, 0.15-0.40 Hz): mostly parasympathetic (rest/digest)

LF/HF ratio elevated = stress dominant; ratio low = relaxed.
"""

from typing import List, Tuple

import numpy as np
from scipy.signal import find_peaks, welch


def detect_pulse_peaks(
    pulse_signal: np.ndarray, fps: float, min_bpm: float = 42.0
) -> np.ndarray:
    """
    Detect individual heartbeat peaks in the filtered pulse waveform.

    Each peak corresponds to one heartbeat; the time between consecutive
    peaks is the inter-beat interval (IBI).
    """
    # Minimum samples between peaks: based on max plausible HR
    max_bpm = 240.0
    min_distance = int(fps * 60.0 / max_bpm)

    # Peak prominence threshold: a fraction of signal std (handles different scales)
    prominence = 0.3 * np.std(pulse_signal)

    peaks, _ = find_peaks(pulse_signal, distance=min_distance, prominence=prominence)
    return peaks


def compute_ibi(peak_indices: np.ndarray, fps: float) -> np.ndarray:
    """
    Convert peak indices to inter-beat intervals (IBIs) in milliseconds.

    IBI[i] = time between peak[i] and peak[i+1]
    """
    if len(peak_indices) < 2:
        raise ValueError("Need at least 2 peaks to compute IBIs")

    ibi_samples = np.diff(peak_indices)
    ibi_ms = (ibi_samples / fps) * 1000.0
    return ibi_ms


def compute_sdnn(ibi_ms: np.ndarray) -> float:
    """
    SDNN — Standard Deviation of Normal-to-Normal intervals.

    The most widely used time-domain HRV metric. Values:
      - 50+ ms: healthy adult at rest
      - 30-50 ms: typical
      - <30 ms: low HRV, possibly stressed/fatigued
    """
    if len(ibi_ms) < 2:
        return 0.0
    return float(np.std(ibi_ms, ddof=1))


def compute_stress_index(
    ibi_ms: np.ndarray,
    lf_band: Tuple[float, float] = (0.04, 0.15),
    hf_band: Tuple[float, float] = (0.15, 0.40),
) -> float:
    """
    Stress index based on LF/HF power ratio, normalized to 0.0-1.0.

    Higher ratio = more sympathetic dominance = more stress.
    We map LF/HF to 0-1 via a sigmoid centered on ratio=1.0 (balanced).
    """
    if len(ibi_ms) < 8:
        # Not enough beats for reliable frequency analysis
        return 0.5

    # Resample IBIs to a regular time grid for spectral analysis
    # (IBIs are naturally irregularly sampled — once per heartbeat)
    ibi_seconds = ibi_ms / 1000.0
    t_cumulative = np.cumsum(ibi_seconds)
    fs_resample = 4.0  # 4 Hz is standard for HRV spectral analysis
    t_uniform = np.arange(0, t_cumulative[-1], 1.0 / fs_resample)
    ibi_uniform = np.interp(t_uniform, t_cumulative, ibi_ms)

    # Welch's method for power spectral density
    freqs, psd = welch(ibi_uniform, fs=fs_resample, nperseg=min(256, len(ibi_uniform)))

    lf_mask = (freqs >= lf_band[0]) & (freqs < lf_band[1])
    hf_mask = (freqs >= hf_band[0]) & (freqs < hf_band[1])

    # np.trapezoid is numpy 2.0+; we pin numpy<2 for mediapipe, so use np.trapz.
    lf_power = np.trapz(psd[lf_mask], freqs[lf_mask]) if np.any(lf_mask) else 0.0
    hf_power = np.trapz(psd[hf_mask], freqs[hf_mask]) if np.any(hf_mask) else 1e-9

    lf_hf_ratio = lf_power / max(hf_power, 1e-9)

    # Sigmoid normalization: ratio 1.0 -> 0.5, ratio 4.0 -> ~0.88, ratio 0.25 -> ~0.12
    stress = 1.0 / (1.0 + np.exp(-(np.log(lf_hf_ratio + 1e-9))))
    return float(np.clip(stress, 0.0, 1.0))


def _hrv_confidence(n_peaks: int, ibi_ms: np.ndarray, *, target_beats: int = 20) -> float:
    """Confidence in the SDNN / stress estimate, in [0, 1].

    Two factors stacked:
      1. Beat count — SDNN is a sample standard deviation, so more beats
         tighten the estimate. `target_beats` is the full-confidence
         threshold (20 ≈ 40 BPM over 30 s; 25 for stress because LF/HF
         spectral analysis needs more samples than time-domain SDNN).
      2. IBI plausibility — if the coefficient of variation of the IBI
         series exceeds 0.30, we're likely missing or extra-counting
         beats. The penalty grows linearly past that, floored at 0.2 so
         we still return *something* rather than collapse to zero.
    """
    if n_peaks < 4 or len(ibi_ms) < 2:
        return 0.0
    base = min(1.0, n_peaks / float(target_beats))

    mean_ibi = float(np.mean(ibi_ms))
    if mean_ibi <= 1e-9:
        return 0.0
    cv = float(np.std(ibi_ms)) / mean_ibi
    if cv > 0.30:
        penalty = max(0.2, 1.0 - (cv - 0.30) * 2.0)
        base *= penalty
    return float(np.clip(base, 0.0, 1.0))


def compute_hrv_metrics(
    pulse_signal: np.ndarray, fps: float
) -> Tuple[float, float, int, float, float]:
    """
    Full Task 3 pipeline: pulse waveform -> HRV metrics + per-metric confidence.

    Returns:
        sdnn_ms:           SDNN in ms (hrv_sdnn field in API contract)
        stress_index:      0.0–1.0 (stress_index field in API contract)
        n_peaks:           number of beats detected (diagnostic)
        hrv_confidence:    0–1, scales with beat count + IBI plausibility
        stress_confidence: 0–1, stricter beat threshold than HRV because
                           the LF/HF spectral analysis needs more samples
    """
    peaks = detect_pulse_peaks(pulse_signal, fps)
    n = len(peaks)

    if n < 4:
        # Not enough heartbeats detected — safe defaults with zero confidence
        return 0.0, 0.5, n, 0.0, 0.0

    ibi_ms = compute_ibi(peaks, fps)
    sdnn = compute_sdnn(ibi_ms)
    stress = compute_stress_index(ibi_ms)

    hrv_conf = _hrv_confidence(n, ibi_ms, target_beats=20)
    stress_conf = _hrv_confidence(n, ibi_ms, target_beats=25)

    return round(sdnn, 1), round(stress, 2), n, round(hrv_conf, 2), round(stress_conf, 2)
