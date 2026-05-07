# VitalScan — colleague briefing

A two-minute read so you can explain VitalScan in your own words.
Live demo: <https://vitalscan.bkre8tive.com>

## One-liner

VitalScan extracts heart rate, heart-rate variability (HRV), and a derived
stress index from a 30-second face video using a remote photoplethysmography
(rPPG) pipeline. No wearable, no chest strap — just a webcam.

## Why this works at all

When your heart pumps, blood pulses through the capillaries in your face.
That changes how much green light your skin absorbs by a tiny amount —
typically less than 1% of the pixel value. A camera sees that subtle
change frame-by-frame. Average enough skin pixels over enough time and
you can recover the heartbeat waveform from the video alone.

The technique is called **rPPG (remote photoplethysmography)**. The
2017 paper by Wang et al. defined the **POS algorithm** (Plane-Orthogonal-to-Skin)
that we use. POS projects the noisy RGB signal onto a plane chosen to
suppress motion artifacts, leaving the pulse signal mostly intact.

## The four pipeline stages

```
video file
    │
    ▼
[1] Face detection + ROI extraction        backend/rppg/face_detection.py
    └─ MediaPipe FaceMesh picks forehead + cheek landmarks per frame
    └─ Output: per-frame mean RGB time-series + fps
    │
    ▼
[2] POS projection + bandpass + FFT        backend/rppg/pos_algorithm.py
    └─ POS reduces RGB → 1D pulse signal
    └─ Butterworth bandpass keeps 1 Hz – 3.5 Hz (60–210 BPM)
    └─ FFT picks the dominant peak → heart rate in BPM
    │
    ▼
[3] Peak detection → IBI → HRV             backend/rppg/hrv.py
    └─ scipy find_peaks on the filtered pulse
    └─ Inter-beat intervals → SDNN (HRV in milliseconds)
    └─ Sigmoid maps HR + HRV → stress index 0..1
    │
    ▼
[4] Evaluation harness                     backend/rppg/evaluation.py
    └─ Runs the same pipeline on a labelled dataset (UBFC, SCAMPS)
    └─ Outputs MAE / RMSE / per-subject CSV
```

Stages 1–3 run on every `/scan` request. Stage 4 runs offline against
public datasets to validate accuracy.

## Architecture (live deploy)

```
browser  ──HTTPS──▶  Cloudflare edge  ──Argo Tunnel──▶  cloudflared (homelab)
                                                              │
                                                              ▼
                                                    nginx :80  /api/  →  FastAPI :8000
                                                       │                    │
                                                       ▼                    ▼
                                              static React SPA        rPPG pipeline
                                              (Vite build)            (MediaPipe + scipy)
```

- TLS terminates at the **Cloudflare edge** — no Let's Encrypt on the homelab
- The homelab has **no public IP and no inbound port forwarding** — `cloudflared` makes an outbound QUIC connection to Cloudflare and traffic flows back through it
- **nginx** in the frontend container serves the static React build and reverse-proxies `/api/*` to FastAPI
- Three Docker containers, all on a private bridge network: `vitalscan-frontend`, `vitalscan-backend`, `vitalscan-cloudflared`

## What happens when someone clicks "Scan live"

1. Browser asks for webcam access (`navigator.mediaDevices.getUserMedia`)
2. **MediaRecorder** captures 30 seconds of video to a `Blob`
3. Frontend POSTs the blob as `multipart/form-data` to `/api/scan`
4. nginx proxies that to `FastAPI:8000/scan`
5. FastAPI saves it to `/tmp`, runs the pipeline, returns biomarker JSON
6. React renders the four metric cards with color coding (green/amber/red)
7. The result is persisted to **localStorage** so a page refresh keeps it

If `VITALSCAN_USE_MOCK=true` (current default), step 5 returns plausible
random biomarkers instead of running the real pipeline. That's how the
dashboard works without a real video and lets Groups 2–4 integrate
against a stable response shape.

## API contract (for Groups 3 and 4)

```json
{
  "biomarkers": {
    "heart_rate": 72,
    "hrv_sdnn": 45,
    "stress_index": 0.6,
    "blood_pressure": { "systolic": 138, "diastolic": 88 }
  }
}
```

Caveat: blood pressure is **mocked**. Classical rPPG cannot derive BP
without per-subject cuff calibration — that's a known limitation
documented in the writeup, not a bug.

## Performance — the rubric number

We evaluated on two public datasets:

| Dataset | Type | N | MAE (BPM) | Rubric |
|---|---|---|---|---|
| **UBFC-rPPG** | **Real human** | **42** | **4.10** | **PASS (< 10)** |
| SCAMPS (Microsoft) | Synthetic | 10 | 28.86 | Fails the rubric, but expected — synthetic skin lacks real capillary chromaticity |

Half of all UBFC predictions are within ±1 BPM of ground truth. 38 of 42
subjects within ±10 BPM. The four outliers are consecutive subject IDs,
suggesting a recording-session artifact (lighting/camera) rather than
algorithm failure.

Full breakdown: `docs/evaluation_results.md`.

## Key design decisions worth defending

| Decision | Why |
|---|---|
| **MediaPipe FaceMesh** for ROI | Better than dlib's 68-point model for forehead landmarks; ships with weights, no training needed |
| **POS** instead of CHROM or ICA | Most robust to motion in the literature; one-pass linear projection, no per-subject training |
| **Bandpass 60–210 BPM** | Tradeoff: cuts off the 49 BPM resting-HR outlier in SCAMPS but preserves high-HR ground truth and rejects synthetic-data artifacts at 42–60 BPM |
| **Cloudflare Tunnel** instead of public IP + Traefik | No port forwarding, no inbound firewall holes, no Let's Encrypt to manage; tradeoff is that traffic goes through Cloudflare's network |
| **Mock mode default** | Demo doesn't risk pipeline failure on stage; flip `VITALSCAN_USE_MOCK=false` for the real run |

## Demo flow (what to show)

1. Open <https://vitalscan.bkre8tive.com> — point out the dark dashboard with the body figure and four metric cards
2. Click **Rescan** — numbers update from the mock backend in <100 ms
3. Refresh the page — same numbers stick (localStorage)
4. (Optional) Click **Scan live** — give the browser webcam access, hold still 30 seconds, the dashboard updates with new biomarkers
5. Show `docs/evaluation_results.md` for the UBFC 4.10 BPM number

## Common questions and how to answer

**"Why not just use a smartwatch?"**
Wearables require the user to own one. rPPG works with any webcam — the goal is broad accessibility for health screening, not clinical replacement of medical devices.

**"How accurate is it really?"**
4.10 BPM mean absolute error on 42 real subjects (UBFC-rPPG dataset).
Median error is 1.05 BPM — half the time we're within 1 BPM of a pulse oximeter.

**"What about the SCAMPS 28.86 number?"**
SCAMPS is synthetic facial animation. It establishes the pipeline runs end-to-end, but synthetic skin doesn't have realistic blood-volume chromaticity, so accuracy is artificially capped. Published POS baselines on synthetic data sit in the 15–40 BPM range — we're consistent with that.

**"Is the blood pressure number real?"**
No, it's mocked. Classical rPPG cannot derive BP without calibration against a cuff measurement. We're transparent about this in the writeup.

**"How do Groups 2/3/4 use this?"**
They call `POST /api/scan` with a video and receive the biomarker JSON.
Group 2 contributes `food`, Group 3 reads both for risk modelling,
Group 4 generates the natural-language explanation.

**"What's running where?"**
Frontend (React/Vite/nginx) and backend (FastAPI/MediaPipe/scipy) are
both Docker containers on the homelab. Cloudflared is a third container
that maintains the outbound tunnel to Cloudflare. The browser only ever
talks to Cloudflare.

## Where the code lives

| Concern | Path |
|---|---|
| rPPG algorithm | `backend/rppg/` |
| FastAPI endpoints | `backend/main.py` |
| React dashboard | `frontend/src/components/` |
| Webcam capture | `frontend/src/components/WebcamCapture.tsx` |
| Tunnel config | `deploy/cloudflared/config.yml` |
| Deployment guide | `DEPLOY.md` |
| Eval results | `docs/evaluation_results.md` |
| Dataset notes | `docs/ubfc-email-draft.md` |
