# VitalScan (Group 1) — Week 5 Reporting Status: Real vs. Mock

**Date:** 2026-06-01
**Purpose:** A separate, honest accounting of what in our Week 5 demo is *real, validated reporting* versus what is *currently mock*, so the team presents the system accurately and Groups 3–4 know exactly what they're consuming. **This is NOT the presentation deck** — it's the reference behind it.

---

## TL;DR

- **Our accuracy results are REAL.** The rPPG pipeline was validated on **42 real human subjects** (UBFC-rPPG) at **MAE 4.10 BPM** — it passes the rubric (<10 BPM). This is genuine reporting from the actual pipeline.
- **The live demo endpoint is currently MOCK.** The public `GET /api/biometrics` returns `mode:"mock"` payloads (`video_size_bytes: 0`) because the deployed container runs with `VITALSCAN_USE_MOCK=true`.
- **These are two different things.** The pipeline that earned the 4.10 BPM is real; it just isn't the code path serving the public endpoint *yet*. Don't conflate "the live values are mock" with "our results are fake." They aren't.

---

## 1. What is REAL (evidence-backed, defensible)

| Claim | Number | Source |
|---|---|---|
| UBFC-rPPG (real humans), POS — **MAE** | **4.10 BPM** | `data/eval_ubfc_full.csv` (n=42), `docs/evaluation_results.md` |
| UBFC-rPPG, POS — RMSE | 7.83 BPM | same |
| UBFC-rPPG, POS — median \|error\| | 1.05 BPM | same |
| Within 5 BPM | 33/42 (79%) | same |
| Within 10 BPM | 38/42 (90%) | same |
| POS vs CHROM baseline (real data) | tied within ~0.2 BPM | `data/compare_pos_chrom_ubfc.csv` |
| SCAMPS (synthetic), POS — MAE | 28.86 BPM (disclosed synthetic limit; POS beats CHROM by ~6) | `data/eval_scamps*.csv` |

- The real pipeline (MediaPipe FaceMesh ROI → POS → Butterworth bandpass → FFT peak → HRV) **exists and produced these numbers offline.**
- **Headline for the presentation:** *"Validated on 42 real human subjects at 4.10 BPM MAE — under the 10 BPM rubric target."* This replaces the old "≈2.62 BPM (5-sample preliminary)" figure, which was synthetic and is no longer the best/defensible number.

## 2. What is MOCK (right now)

- The deployed public endpoint serves **mock biomarkers** for all 12 stored scans: `mode:"mock"`, `video_size_bytes: 0`.
- **Why:** the container is deployed with `VITALSCAN_USE_MOCK=true` (the default) so the dashboard and the cross-group JSON contract work in the demo environment without requiring video upload / heavy CV dependencies.
- **Implication for Groups 3–4:** the values they read **today** are realistic placeholders that match the real contract *shape* exactly — they are not real rPPG extractions. The contract, endpoint, and integration are real; the payload values are mock.

## 3. Blood pressure — needs a team decision

- The API returns a clinically plausible BP (e.g., `143/86`) at `confidence: 0.1` with a note that classical rPPG cannot derive BP without cuff calibration.
- **Risk:** a realistic stage-2-hypertension-range number can be misread downstream even at low confidence, especially if Group 3 doesn't strictly gate on the `confidence` field.
- **Recommendation:** return `null` for BP (matches the Week 4 report and is the more defensible choice), **or** confirm Group 3 hard-gates on confidence before surfacing any value. Pick one before final submission.

## 4. Honest talking points (say these, avoid the overclaim)

- ✅ "Our pipeline is validated on **42 real human subjects** at **4.10 BPM MAE**, under the 10 BPM rubric."
- ✅ "The integration contract is **live and consumed by Group 3**. The deployed instance currently serves **mock-mode payloads of the identical shape** while we finish wiring the real video path to production."
- ❌ Do **not** say the live `/api/biometrics` values are real measurements — they're mock until `VITALSCAN_USE_MOCK=false` and a real video has been processed.

## 5. To make the live endpoint serve REAL data (optional next step)

1. Deploy/restart the backend container with `VITALSCAN_USE_MOCK=false`.
2. Ensure `cv2` + `mediapipe` are present (Python 3.12, `numpy<2`).
3. `POST` a real ~30s face video to `/scan`.
4. Confirm `GET /api/biometrics` shows `mode:"pipeline"` (not `"mock"`) and `video_size_bytes > 0`.

---

*Maintained by Germaine. Grounded in `docs/evaluation_results.md` and the live API response captured 2026-06-01.*
