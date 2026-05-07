"""
Full rPPG pipeline integration.

Wires Tasks 1, 2, and 3 together into a single function the API endpoint
can call with a video file path.

Note on blood pressure: classical rPPG cannot directly measure blood pressure
without calibration against a cuff measurement. For this project we either:
  a) Use mock BP values from `mock.py`
  b) Estimate BP from a model trained on MCD-rPPG (Task 5 stretch goal)
  c) Skip BP and let the user provide it manually

The current implementation uses mock BP — flag this clearly in the writeup.
"""

from dataclasses import dataclass, asdict
from typing import Optional

from .face_detection import FaceROIExtractor
from .hrv import compute_hrv_metrics
from .pos_algorithm import extract_heart_rate
from .mock import generate_mock_biomarkers


@dataclass
class BiomarkerResult:
    """Matches the shared API contract from the project brief."""
    heart_rate: int
    hrv_sdnn: int
    stress_index: float
    blood_pressure_systolic: int
    blood_pressure_diastolic: int

    def to_contract_dict(self) -> dict:
        return {
            "biomarkers": {
                "heart_rate": self.heart_rate,
                "hrv_sdnn": self.hrv_sdnn,
                "stress_index": self.stress_index,
                "blood_pressure": {
                    "systolic": self.blood_pressure_systolic,
                    "diastolic": self.blood_pressure_diastolic,
                },
            }
        }


def run_pipeline(video_path: str) -> BiomarkerResult:
    """
    Full Group 1 pipeline: video file -> biomarkers.

    Stages:
        1. Face detection + ROI extraction (Task 1)
        2. POS algorithm + bandpass + FFT (Task 2)
        3. HRV + stress index (Task 3)

    Raises:
        IOError: if the video can't be opened
        ValueError: if the video has insufficient usable frames
    """
    # Stage 1: extract per-frame RGB time-series from facial ROI
    extractor = FaceROIExtractor()
    try:
        rgb_series, fps = extractor.process_video(video_path)
    finally:
        extractor.close()

    # Stage 2: POS + bandpass + FFT -> heart rate + filtered pulse
    heart_rate_bpm, filtered_pulse = extract_heart_rate(rgb_series, fps)

    # Stage 3: peak detection -> IBI -> SDNN + stress
    sdnn_ms, stress_index, _ = compute_hrv_metrics(filtered_pulse, fps)

    # Blood pressure is not derivable from rPPG without calibration —
    # use mock values for now and document this in the writeup
    mock = generate_mock_biomarkers()["biomarkers"]["blood_pressure"]

    return BiomarkerResult(
        heart_rate=int(round(heart_rate_bpm)),
        hrv_sdnn=int(round(sdnn_ms)),
        stress_index=float(stress_index),
        blood_pressure_systolic=mock["systolic"],
        blood_pressure_diastolic=mock["diastolic"],
    )
