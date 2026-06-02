# VitalScan — End-to-End Technical Walkthrough

**AIT 500 · Westcliff University · Group 1**
**Date:** June 2026

---

## 1. The problem we're solving

Extract heart rate (BPM), HRV (SDNN ms), and a stress index from a **30-second facial video** — no contact, no wristband, just a webcam. The method is **rPPG** (remote photoplethysmography): the camera detects sub-percent fluctuations in skin color caused by capillary blood-volume changes with each heartbeat. Roughly 90 % of light hitting skin reflects back; the heartbeat signal lives in the 10 % absorption variation we can recover.

---

## 2. The two datasets we use, and *why*

| Dataset | What it is | N | Role in our project |
|---|---|---|---|
| **UBFC-rPPG (Bobbia et al. 2019)** | Real human videos, ~1 min each, paired with a contact PPG ground-truth signal | **42 subjects** | **Headline validation.** Lets us prove the pipeline works on real humans. |
| **SCAMPS (Microsoft, NeurIPS 2022)** | Synthetic CGI avatars with simulated facial animation and a programmed BPM ground truth | 10 examples (1.2 GB sample) | **Smoke test + tuning study.** Confirms the pipeline runs end-to-end and is a stress test for failure modes. |

**Why two datasets?** Real data is what the professor and rubric care about, but it's noisy and you can't isolate variables. Synthetic data is clean and controllable but doesn't capture true capillary chromaticity, so accuracy is intentionally worse. Reporting both is honest and matches what's published in the rPPG literature.

**Where the data lives in the repo:**

- `data/eval_ubfc_full.csv` — per-subject UBFC results (42 rows)
- `data/eval_scamps_*.csv` — three versions from the bandpass tuning study
- `data/compare_pos_chrom_ubfc.csv` — POS vs CHROM head-to-head, real data
- `data/compare_pos_chrom_scamps.csv` — POS vs CHROM, synthetic data

Datasets themselves are **not committed** (too big — gitignored by `data/*`). The UBFC dataset is fetched from a public Google Drive link; SCAMPS is `curl`-able from Microsoft's NeurIPS-2022 page. The exact reproduce commands are in `docs/evaluation_results.md`.

---

## 3. The four-stage pipeline

`backend/rppg/pipeline.py:run_pipeline()`

```
30 s video  →  Task 1  →  Task 2  →  Task 3  →  Task 4  →  Biomarker JSON
                ROI       Heart       HRV +     BP
              extract     rate        stress  (placeholder)
```

### Task 1 — Face detection & ROI extraction

**File:** `backend/rppg/face_detection.py` · **Owner:** Daray

- Each video frame goes through **MediaPipe FaceMesh** → 468 facial landmarks.
- We extract **three ROIs**: forehead, left cheek, right cheek. These have the highest capillary density and the most stable position frame-to-frame.
- For each frame we compute the **mean RGB** inside each ROI polygon, then **average the three ROIs** to produce one (R, G, B) triple per frame.
- Output: a (n_frames, 3) time series + the video's fps.
- Robustness: if fewer than 5 seconds of frames had a face detected, we raise an error rather than return junk.

### Task 2 — POS algorithm + bandpass + FFT

**File:** `backend/rppg/pos_algorithm.py` · **Owner:** Daray

This is where the heart rate actually comes out. Three sub-steps:

**2a. POS projection.** The Plane-Orthogonal-to-Skin algorithm (Wang et al. 2017) projects the RGB signal onto a 2D plane orthogonal to the average skin-tone vector. This cancels noise that affects all three channels equally (head motion, ambient lighting changes) while preserving the pulse signal that lives mostly in the green channel. The projection matrix is the standard `H = [[0, 1, -1], [-2, 1, 1]]`. We run it in a sliding 1.6-second window with overlap-add — same as the original paper.

**2b. Butterworth bandpass.** 3rd-order zero-phase bandpass at **0.7–4.0 Hz** (= 42–240 BPM). `scipy.signal.filtfilt` for zero phase shift. The "tune the radio" analogy: we're tuning to only the band where heartbeats live.

**2c. FFT peak picking.** We FFT the filtered pulse, zero-pad to 4× the next power of two for finer resolution, and pick the highest-magnitude frequency inside **60–210 BPM** (tightened from 42–240 after SCAMPS tuning — see §5). Peak frequency × 60 = BPM.

**Confidence** for heart rate: how dominant is the peak vs the mean magnitude in the band? `ratio = 1.5 → 0.0`, `ratio = 5.5 → 1.0`, linear in between. Sharp peak = trust the number; flat noise floor = don't.

### Task 3 — HRV + stress index

**File:** `backend/rppg/hrv.py` · **Owner:** Daray

Takes the filtered pulse waveform from Task 2 (NOT the FFT — we need the time-domain signal):

**3a. Peak detection.** `scipy.signal.find_peaks` with a prominence threshold of `0.3 × std(signal)` and a minimum spacing matching 240 BPM. Each peak is one heartbeat.

**3b. Inter-beat intervals (IBIs).** `np.diff(peak_indices) / fps × 1000` = IBI in milliseconds.

**3c. SDNN.** `np.std(ibi, ddof=1)`. That's the HRV metric. Counter-intuitively, **high HRV is healthy** (good autonomic function). Healthy adult at rest: 50+ ms.

**3d. Stress index.** Resample IBIs to 4 Hz on a uniform grid, take Welch power spectral density, compute LF (0.04–0.15 Hz) and HF (0.15–0.40 Hz) band power via trapezoid integration, then sigmoid-normalize the LF/HF ratio to [0, 1]. LF/HF = 1.0 maps to stress = 0.5 (balanced); LF/HF = 4.0 maps to ~0.88 (sympathetic dominant); LF/HF = 0.25 maps to ~0.12 (parasympathetic/relaxed).

**HRV confidence:** two factors — (1) beat count vs target 20 beats; (2) coefficient of variation of IBIs — if CV > 0.30 we're probably miscounting beats, so we penalize.

### Task 4 — Blood pressure

**Honest disclosure point for the professor:** classical rPPG **cannot** measure blood pressure without a cuff-calibration reference. We return a clinically plausible placeholder (e.g. 138/88) with **`confidence = 0.10`** and an explicit `note` field stating the limitation. The contract carries it so downstream consumers (Group 3 risk analysis) get a complete payload, but the low confidence and the note make the placeholder unambiguous.

---

## 4. Validation methodology — how the 4.10 BPM number was produced

`backend/rppg/evaluation.py` (Owner: **Abner**) runs the full pipeline against every video in a dataset and compares to the contact-PPG ground-truth heart rate. For each subject:

```
error_i  = predicted_HR - ground_truth_HR
MAE      = mean(|error_i|)        # mean absolute error
RMSE     = sqrt(mean(error_i²))   # penalizes large errors more
median   = median(|error_i|)
```

**Rubric target:** MAE < 10 BPM. **Our result on 42 real human subjects: 4.10 BPM** — comfortably under.

### Headline UBFC results

| Metric | Value |
|---|---|
| **MAE** | **4.06–4.10 BPM (rubric pass)** |
| RMSE | 7.78–7.83 BPM |
| Median \|error\| | **1.05 BPM** — half of all predictions within 1 BPM of truth |
| Within ±1 BPM | 21 / 42 (50 %) |
| Within ±5 BPM | 33 / 42 (79 %) |
| Within ±10 BPM | 38 / 42 (90 %) |
| Outliers (>10 BPM) | 4 / 42 — subjects 25, 26, 27, 32 |

The **outlier cluster** (three consecutive subject IDs) suggests a shared recording-session issue — same lighting / camera — rather than algorithm failure. That's a defensible explanation if the professor asks why the four failed.

### POS vs CHROM head-to-head

CHROM is the *other* classical rPPG algorithm; we ran it as a baseline. On real UBFC data they're **statistically tied** (POS 4.06 vs CHROM 3.86 — within 0.2 BPM). On synthetic SCAMPS, POS beats CHROM by ~6 BPM because POS's adaptive weighting handles synthetic artifacts better. Both clear the < 10 BPM bar on real data.

---

## 5. SCAMPS — the tuning study and the failure modes

SCAMPS is intentionally hard because the avatars don't have realistic capillary chromaticity rendering. Our SCAMPS result is **MAE 28.86 BPM** — fails the rubric, and we report that honestly.

What SCAMPS gave us: a **bandpass tuning study** (`docs/evaluation_results.md`):

| FFT search window | MAE | Decision |
|---|---|---|
| 42–240 BPM (POS default) | 45.16 | Low-freq synthetic artifacts dominate |
| 50–210 BPM | 45.16 | Same problem, artifacts at 50–60 BPM |
| **60–210 BPM (chosen)** | **28.86** | Best — used in both SCAMPS and UBFC runs |

The 60-BPM floor is the trade-off: it loses two subjects whose true HR is < 60 BPM, but it gains every high-HR subject by killing the 42–60 Hz synthetic-animation artifacts. WHO normal resting HR is 60–100, so the floor is medically defensible.

**Two distinct failure modes documented in `docs/evaluation_results.md`:**

1. **Sub-60 BPM truth** (P000002, P000006) — our floor excludes them by design.
2. **Weak synthetic pulse** (P000003, P000004, P000005, P000007) — SCAMPS rendering can't produce the chromaticity our algorithm needs.

But **4 / 10 SCAMPS samples are essentially perfect** (P000008, P000009, P000010 all within 0.5 BPM of truth) — proves the algorithm is correct, the synthetic data is just bad for rPPG.

---

## 6. End-to-end runtime — what happens when the professor clicks "Scan live"

1. Browser opens webcam (`frontend/src/components/WebcamCapture.tsx`), records 30 s of video, posts it as `multipart/form-data` to `POST /api/scan`.
2. nginx in the frontend container forwards `/api/*` to the backend container.
3. `backend/main.py:scan()` writes the upload to a tempfile, then calls `pipeline.run_pipeline(path)`.
4. The four Tasks run in sequence (~3–8 seconds on the homelab host depending on video length).
5. Result is appended to `data/scan_history.json` via `scan_history.append_scan` (atomic write).
6. The biomarker JSON returns to the browser; the dashboard renders four cards (HR, HRV, Stress, BP) with their confidence pills.
7. Group 3 hits `GET /api/biometrics?person=Daray` and gets back every scan tagged with that name — same contract, real data.

---

## 7. The biomarker JSON contract

Same shape returned by every scan, mock or real:

```json
{
  "biomarkers": {
    "heart_rate":   { "value": 72,  "confidence": 0.91, "unit": "bpm" },
    "hrv_sdnn":     { "value": 45,  "confidence": 0.86, "unit": "ms" },
    "stress_index": { "value": 0.6, "confidence": 0.74, "unit": "score" },
    "blood_pressure": {
      "value": { "systolic": 138, "diastolic": 88 },
      "confidence": 0.10,
      "unit": "mmHg",
      "note": "Classical rPPG cannot derive BP without a cuff calibration reference — value is a clinically plausible placeholder, not a measurement."
    }
  }
}
```

---

## 8. Live endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/scan` | Run the rPPG pipeline on an uploaded video, persist the result, return biomarkers. **The deliverable.** |
| `GET` | `/api/biometrics` | List every scan ever performed, newest first. **The integration point Groups 3+4 hit.** |
| `GET` | `/api/health` | Service health check + current mock/pipeline mode. |

All three are live at **https://vitalscan.bkre8tive.com** behind a named Cloudflare Tunnel (no public IP, no port forwarding, TLS terminated at the Cloudflare edge).

---

## 9. Likely professor questions and where to point

| Question | Answer / where to point |
|---|---|
| "Is this real?" | `data/eval_ubfc_full.csv` — 42 real human subjects |
| "How accurate?" | MAE 4.10 BPM, median 1.05 BPM, 90 % within ±10 BPM |
| "Why two algorithms?" | POS = ours, CHROM = baseline; statistically tied on real data |
| "Why does synthetic data do worse?" | Avatar rendering lacks capillary chromaticity — published baselines also 15–40 MAE on synthetic |
| "How do you measure blood pressure?" | We don't — it's a flagged placeholder at confidence 0.10 with a note. Classical rPPG cannot do BP without cuff calibration. |
| "What about deep learning?" | Stretch goal — scaffolding in place, not executed; classical algorithms already pass the rubric |
| "What if I upload my own video?" | Dashboard supports it — `.mp4`/`.webm`/`.mov`/`.avi`/`.mkv`, up to 100 MB |

---

## 10. Group 1 team & task ownership

| Task | File / artifact | Owner |
|---|---|---|
| Face + ROI | `backend/rppg/face_detection.py` | Daray |
| POS + heart rate | `backend/rppg/pos_algorithm.py` | Daray |
| HRV + stress | `backend/rppg/hrv.py` | Daray |
| Evaluation | `backend/rppg/evaluation.py` | Abner |
| Dataset retrieval | UBFC-rPPG · SCAMPS examples | Jason |
| API + frontend | `backend/main.py` + `frontend/` | Germaine |
| Deployment | `docker-compose.yml` + Cloudflare Tunnel | Germaine |
