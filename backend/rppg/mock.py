"""
Mock biomarker data generator for Phase 1/2 development.

Emits the same `{value, confidence, unit}` per-biomarker shape the real
rPPG pipeline returns (agreed with the professor on 2026-05-25), so the
frontend, Groups 3 + 4, and demo mode all see one contract.
"""

import random


def generate_mock_biomarkers() -> dict:
    """Return a biomarker dict matching the shared API contract."""
    # Heart rate: normal resting 60-100 bpm, with mild stress bias
    heart_rate = random.randint(68, 88)

    # HRV SDNN: 30-60 ms is typical for healthy adults at rest
    hrv_sdnn = random.randint(35, 55)

    # Stress index: 0.0-1.0, biased slightly elevated for demo drama
    stress_index = round(random.uniform(0.4, 0.75), 2)

    # Blood pressure: bias toward Stage 1 hypertension for the demo
    systolic = random.randint(125, 145)
    diastolic = random.randint(80, 92)

    # Mock confidences chosen to look like "good but not perfect" measurements
    # so the UI's confidence-pill renders meaningfully during demos.
    return {
        "biomarkers": {
            "heart_rate": {
                "value": heart_rate,
                "confidence": round(random.uniform(0.78, 0.94), 2),
                "unit": "bpm",
            },
            "hrv_sdnn": {
                "value": hrv_sdnn,
                "confidence": round(random.uniform(0.70, 0.88), 2),
                "unit": "ms",
            },
            "stress_index": {
                "value": stress_index,
                "confidence": round(random.uniform(0.65, 0.85), 2),
                "unit": "score",
            },
            "blood_pressure": {
                "value": {
                    "systolic": systolic,
                    "diastolic": diastolic,
                },
                "confidence": 0.10,
                "unit": "mmHg",
                "note": (
                    "Classical rPPG cannot derive BP without a cuff calibration "
                    "reference — value is a clinically plausible placeholder."
                ),
            },
        }
    }
