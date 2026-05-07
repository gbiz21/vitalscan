"""
rPPG (remote photoplethysmography) pipeline for VitalScan Group 1.

The classical signal processing approach extracts heart rate, HRV, and stress
index from facial video. The intuition: every heartbeat pushes blood through
the capillaries in your skin, slightly changing how light reflects. A camera
can pick up these tiny color changes, and signal processing isolates the
heartbeat frequency from the noise.

Pipeline stages (Tasks 1-3 from the assignment brief):

    video frames
        │
        ▼
    [face_detection]    Task 1 — MediaPipe FaceMesh, ROI = forehead + cheeks
        │  RGB time-series
        ▼
    [pos_algorithm]     Task 2 — POS + Butterworth bandpass + FFT → heart_rate
        │  pulse waveform
        ▼
    [hrv]               Task 3 — peak detection → IBI → SDNN, LF/HF → stress
        │
        ▼
    biomarker JSON (matches shared API contract)

The radio analogy: the heartbeat is broadcasting on a specific frequency
(0.7-4.0 Hz, i.e. 42-240 BPM). Bandpass filter = tuning the dial. FFT =
reading what station is playing.
"""

from .mock import generate_mock_biomarkers

# `pipeline` (and its cv2 / mediapipe deps) is imported lazily by callers so
# that mock mode works without the heavy CV stack installed. Use:
#   from rppg.pipeline import run_pipeline, BiomarkerResult

__all__ = ["generate_mock_biomarkers"]
