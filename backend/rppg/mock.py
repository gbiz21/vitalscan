"""
Mock biomarker data generator for Phase 1/2 development.

Lets the frontend and Groups 3+4 develop against realistic data before the
real rPPG pipeline is finished. Returns slightly-randomized values around
clinically plausible means so each "scan" feels different.
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

    return {
        "biomarkers": {
            "heart_rate": heart_rate,
            "hrv_sdnn": hrv_sdnn,
            "stress_index": stress_index,
            "blood_pressure": {
                "systolic": systolic,
                "diastolic": diastolic,
            },
        }
    }
