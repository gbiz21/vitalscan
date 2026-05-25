"""
Full rPPG pipeline integration.

Wires Tasks 1, 2, and 3 together into a single function the API endpoint
can call with a video file path.

Each biomarker is returned as a {value, confidence, unit} object — the
contract Group 1 agreed on with the professor on the 2026-05-25 review.
Confidence is in [0, 1]: higher = more trust the downstream consumer
(Group 3 risk analysis) should place in the value.

Note on blood pressure: classical rPPG cannot directly measure blood
pressure without calibration against a cuff measurement. We return a
mocked BP value with confidence = 0.0 so downstream consumers can
distinguish it from real measurements.
"""

from dataclasses import dataclass

from .face_detection import FaceROIExtractor
from .hrv import compute_hrv_metrics
from .pos_algorithm import extract_heart_rate
from .mock import generate_mock_biomarkers


# Confidence reported for the mocked blood-pressure value. We could set
# this to 0.0 to make it dead-obvious it isn't measured, but Group 3
# downstream wants *some* signal — so we report a small floor (0.10) and
# tag the field with a `note` that flags the placeholder.
BLOOD_PRESSURE_CONFIDENCE_FLOOR = 0.10
BLOOD_PRESSURE_NOTE = (
    "Classical rPPG cannot derive BP without a cuff calibration reference — "
    "value is a clinically plausible placeholder, not a measurement."
)


@dataclass
class BiomarkerResult:
    """Matches the {value, confidence} contract agreed with the professor on 2026-05-25."""
    heart_rate: int
    heart_rate_confidence: float

    hrv_sdnn: float
    hrv_confidence: float

    stress_index: float
    stress_confidence: float

    blood_pressure_systolic: int
    blood_pressure_diastolic: int
    blood_pressure_confidence: float = BLOOD_PRESSURE_CONFIDENCE_FLOOR

    def to_contract_dict(self) -> dict:
        return {
            "biomarkers": {
                "heart_rate": {
                    "value": self.heart_rate,
                    "confidence": self.heart_rate_confidence,
                    "unit": "bpm",
                },
                "hrv_sdnn": {
                    "value": self.hrv_sdnn,
                    "confidence": self.hrv_confidence,
                    "unit": "ms",
                },
                "stress_index": {
                    "value": self.stress_index,
                    "confidence": self.stress_confidence,
                    "unit": "score",  # 0–1
                },
                "blood_pressure": {
                    "value": {
                        "systolic": self.blood_pressure_systolic,
                        "diastolic": self.blood_pressure_diastolic,
                    },
                    "confidence": self.blood_pressure_confidence,
                    "unit": "mmHg",
                    "note": BLOOD_PRESSURE_NOTE,
                },
            }
        }


def run_pipeline(video_path: str) -> BiomarkerResult:
    """
    Full Group 1 pipeline: video file -> biomarkers + per-biomarker confidence.

    Stages:
        1. Face detection + ROI extraction (Task 1)
        2. POS algorithm + bandpass + FFT (Task 2 — returns HR confidence)
        3. HRV + stress index (Task 3 — returns HRV/stress confidence)
        4. Blood pressure placeholder (mocked, flagged with low confidence)

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

    # Stage 2: POS + bandpass + FFT -> heart rate + filtered pulse + HR confidence
    heart_rate_bpm, hr_confidence, filtered_pulse = extract_heart_rate(rgb_series, fps)

    # Stage 3: peak detection -> IBI -> SDNN + stress (each with its own confidence)
    sdnn_ms, stress_index, _n_peaks, hrv_conf, stress_conf = compute_hrv_metrics(
        filtered_pulse, fps
    )

    # Stage 4: Blood pressure — placeholder, can't derive from classical rPPG
    mock_bp = generate_mock_biomarkers()["biomarkers"]["blood_pressure"]["value"]

    return BiomarkerResult(
        heart_rate=int(round(heart_rate_bpm)),
        heart_rate_confidence=round(hr_confidence, 2),

        hrv_sdnn=float(sdnn_ms),
        hrv_confidence=round(hrv_conf, 2),

        stress_index=float(stress_index),
        stress_confidence=round(stress_conf, 2),

        blood_pressure_systolic=mock_bp["systolic"],
        blood_pressure_diastolic=mock_bp["diastolic"],
    )
