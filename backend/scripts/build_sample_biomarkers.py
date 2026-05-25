"""Pre-compute the static sample biomarker JSON the public GET /samples endpoint serves.

For each UBFC-rPPG subject we already evaluated, take the real POS-predicted
heart rate from `data/compare_pos_chrom_ubfc.csv` and synthesize the rest of
the biomarker JSON in a way that's realistic but reproducible:

  • HRV (SDNN, ms)     — derived from heart rate (lower HR → higher HRV),
                         with a deterministic per-subject jitter so values
                         don't all look identical.
  • stress_index       — derived from HRV (lower HRV → higher stress),
                         clipped to [0, 1].
  • blood_pressure     — plausible mock values that vary per subject,
                         honestly flagged because classical rPPG cannot
                         derive BP without a cuff calibration.

The output file is committed and read at request time by the GET endpoints.

Run with:
    backend/venv312/bin/python backend/scripts/build_sample_biomarkers.py
"""
import json
import math
import random
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
CSV_IN = ROOT / "data" / "compare_pos_chrom_ubfc.csv"
JSON_OUT = ROOT / "data" / "sample_biomarkers.json"


def derive_hrv(heart_rate: float, seed: int) -> float:
    """Map heart rate → plausible SDNN in ms.

    Healthy adults typically: HR ~60 bpm ≈ HRV 60ms · HR ~80 ≈ HRV 45ms ·
    HR ~100 ≈ HRV 30ms. Linear-ish, with deterministic per-subject jitter.
    """
    rng = random.Random(seed)
    base = max(20.0, 90.0 - 0.55 * heart_rate)  # rough inverse trend
    jitter = rng.uniform(-6.0, 6.0)
    return round(base + jitter, 0)


def derive_stress(hrv_sdnn: float, seed: int) -> float:
    """Map SDNN → stress index in [0, 1]. Sigmoid centered at SDNN ≈ 45 ms."""
    rng = random.Random(seed + 1)
    x = (45.0 - hrv_sdnn) / 12.0          # > 0 means below-healthy HRV → stress
    raw = 1.0 / (1.0 + math.exp(-x))      # sigmoid
    jitter = rng.uniform(-0.04, 0.04)
    return round(max(0.0, min(1.0, raw + jitter)), 2)


def mock_blood_pressure(seed: int) -> dict:
    """Per-subject plausible BP — not derivable from rPPG, flagged in docs."""
    rng = random.Random(seed + 2)
    systolic = rng.randint(118, 148)
    diastolic = rng.randint(75, 94)
    return {"systolic": systolic, "diastolic": diastolic}


def build():
    df = pd.read_csv(CSV_IN)
    samples = []
    for _, row in df.iterrows():
        subject_id = str(row["sample_id"])
        heart_rate = int(round(float(row["pos_bpm"])))
        seed = sum(ord(c) for c in subject_id)
        hrv = derive_hrv(heart_rate, seed)
        stress = derive_stress(hrv, seed)
        bp = mock_blood_pressure(seed)
        samples.append({
            "subject_id": subject_id,
            "source": "UBFC-rPPG · POS pipeline (real human subject)",
            "biomarkers": {
                "heart_rate": heart_rate,
                "hrv_sdnn": int(hrv),
                "stress_index": stress,
                "blood_pressure": bp,
            },
        })

    payload = {
        "dataset": "UBFC-rPPG",
        "n_samples": len(samples),
        "schema_version": "1.0",
        "notes": (
            "heart_rate is the real output of our POS pipeline on the UBFC subject's "
            "vid.avi · hrv_sdnn and stress_index are deterministically derived from "
            "heart_rate · blood_pressure is a plausible mock (classical rPPG cannot "
            "derive BP without cuff calibration)."
        ),
        "samples": samples,
    }

    JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json.dumps(payload, indent=2))
    print(f"wrote {JSON_OUT}  ·  {len(samples)} samples")


if __name__ == "__main__":
    build()
