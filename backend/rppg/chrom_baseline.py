"""
CHROM Baseline Algorithm (de Haan & Jeanne, 2013)
=================================================

Baseline rPPG extractor for comparison against POS in the Task 4 evaluation.

CHROM ("chrominance-based") was the canonical pre-POS classical algorithm
and is the standard baseline cited in nearly every rPPG paper. It uses a
fixed linear combination of RGB channels chosen to suppress specular
reflection while preserving the pulse.

Reference:
  de Haan, G., & Jeanne, V. (2013). "Robust pulse rate from chrominance-based
  rPPG." IEEE Transactions on Biomedical Engineering, 60(10), 2878-2886.

Pipeline mirrors POS: RGB time-series → CHROM projection → bandpass → FFT peak.
The only difference is the projection matrix.
"""

from typing import Tuple

import numpy as np

from .pos_algorithm import butter_bandpass, estimate_heart_rate_fft


def chrom_algorithm(rgb_signal: np.ndarray) -> np.ndarray:
    """
    Apply the CHROM algorithm to extract a pulse signal from an RGB time-series.

    Per de Haan & Jeanne 2013:
        Xs = 3*Rn - 2*Gn
        Ys = 1.5*Rn + Gn - 1.5*Bn
        alpha = std(Xs_bp) / std(Ys_bp)
        S = Xs_bp - alpha * Ys_bp

    Args:
        rgb_signal: shape (n_frames, 3), per-frame mean RGB.

    Returns:
        1D pulse signal of length n_frames.
    """
    if rgb_signal.shape[0] < 2:
        raise ValueError("CHROM needs at least 2 frames")

    mean_rgb = np.mean(rgb_signal, axis=0)
    if np.any(mean_rgb == 0):
        raise ValueError("CHROM cannot normalize — zero-mean channel in RGB signal")

    normalized = rgb_signal / mean_rgb
    r, g, b = normalized[:, 0], normalized[:, 1], normalized[:, 2]

    xs = 3.0 * r - 2.0 * g
    ys = 1.5 * r + g - 1.5 * b

    return xs, ys


def extract_heart_rate_chrom(
    rgb_signal: np.ndarray, fps: float
) -> Tuple[float, np.ndarray]:
    """
    Full CHROM pipeline: RGB time-series → heart rate.

    Returns:
        heart_rate_bpm: estimated heart rate
        filtered_pulse: bandpass-filtered chrominance pulse (compatible with hrv.py)
    """
    xs, ys = chrom_algorithm(rgb_signal)
    xs_bp = butter_bandpass(xs, fps)
    ys_bp = butter_bandpass(ys, fps)

    alpha = np.std(xs_bp) / (np.std(ys_bp) + 1e-9)
    pulse = xs_bp - alpha * ys_bp

    heart_rate_bpm, _, _, _ = estimate_heart_rate_fft(pulse, fps)
    return heart_rate_bpm, pulse
