# VitalScan — Group 1 (rPPG Signal Extraction)

AIT 500 Course Project · Westcliff University · Group 1

**Live:** https://vitalscan.bkre8tive.com — published via a named Cloudflare Tunnel from the homelab.

This repo contains the full Group 1 deliverable: a Python rPPG pipeline that
extracts heart rate, HRV, and stress index from a 30-second facial video,
exposed as a FastAPI `/scan` endpoint, and consumed by a React dashboard.

## Architecture

```
┌─────────────────┐     POST /scan      ┌────────────────────┐
│ React frontend  │  ─────────────────▶ │  FastAPI backend   │
│ (Vite, TS, TW)  │                     │                    │
│ port 5173       │  ◀───────────────── │  rPPG pipeline:    │
└─────────────────┘   biomarker JSON    │   • face detection │
                                        │   • POS algorithm  │
                                        │   • HRV / stress   │
                                        │  port 8000         │
                                        └────────────────────┘
```

The biomarker JSON matches the shared API contract from the project brief:

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

## AIT 500 deliverables

| # | Deliverable (per project brief) | Where to find it | Status |
|---|---|---|---|
| 1 | Working demo — notebook that takes a 30 s video → biomarker JSON | [`demo.ipynb`](demo.ipynb) | ✅ |
| 2 | Accuracy report — MAE / RMSE table vs. baseline | [`docs/evaluation_results.md`](docs/evaluation_results.md) · raw CSVs in [`data/compare_pos_chrom_*.csv`](data/) | ✅ |
| 3 | Technical writeup — end-to-end signal-chain explanation | [`docs/VitalScan_End_to_End_Walkthrough.docx`](docs/VitalScan_End_to_End_Walkthrough.docx) (source: [`.md`](docs/VitalScan_End_to_End_Walkthrough.md)) | ✅ |
| 4 | REST API `/scan` POST endpoint | [`backend/main.py`](backend/main.py) · live at https://vitalscan.bkre8tive.com | ✅ |
| 5 | _Stretch_ — deep-learning comparison vs classical | future work — scaffolding in place, not executed | — |

Architecture figures referenced from the writeup:
- [`docs/figures/figure1-signal-chain.svg`](docs/figures/figure1-signal-chain.svg) — rPPG pipeline (Tasks 1–3)
- [`docs/figures/figure2-architecture.svg`](docs/figures/figure2-architecture.svg) — deployment / data flow

**Headline accuracy** (POS, our algorithm): **UBFC-rPPG MAE = 4.06 BPM on 42 real human subjects** — median absolute error 1.05 BPM, 90 % of subjects within ±10 BPM. CHROM baseline scores 3.86 BPM MAE on the same set (statistically tied). Both classical algorithms clear the rubric's < 10 BPM target.

## Build phases

| Phase | Status | What it does                                          |
|-------|--------|-------------------------------------------------------|
| 1     | ✅     | React UI with mock biomarker data                     |
| 2     | ✅     | FastAPI backend with mock `/scan` endpoint            |
| 3     | ✅     | Real rPPG pipeline (POS + CHROM, evaluated on UBFC + SCAMPS) |
| 4     | ✅     | Docker + Cloudflare Tunnel deployment (live)          |
| 5     | ✅     | Browser webcam capture                                |

## Quick start (local dev)

> **Python version:** the backend pins mediapipe 0.10.x which requires Python
> 3.12 (no 3.13 wheel is published yet). On macOS:
> `brew install python@3.12` then use `python3.12 -m venv venv`.

```bash
# Terminal 1 — backend
cd backend
python3.12 -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend
npm install
npm run dev
```

The dashboard exposes three ways to feed the pipeline:
- **Rescan** — refreshes mock data (no video needed)
- **Scan live** — opens your webcam for a 30-second capture
- **Upload video** — pick any `.mp4`/`.webm`/`.mov`/`.avi`/`.mkv` file from disk

By default the backend returns mock data (`VITALSCAN_USE_MOCK=true`). To run
the real rPPG pipeline on uploaded/recorded video, set `VITALSCAN_USE_MOCK=false`
when starting uvicorn.

## Quick start (Docker, for homelab deploy)

Production: **https://vitalscan.bkre8tive.com** — published via a named
Cloudflare Tunnel from the homelab. No public IP, no port forwarding,
TLS terminated at the Cloudflare edge. Full step-by-step in [DEPLOY.md](DEPLOY.md).

```bash
# On the homelab host, after rsync of the repo + scp of the tunnel
# credentials JSON to deploy/cloudflared/:
docker compose up -d --build
docker compose logs -f cloudflared    # watch for "Registered tunnel connection"
```

The `docker-compose.yml` runs three services (backend, frontend, cloudflared)
on an internal bridge network. The `cloudflared` service mounts
`deploy/cloudflared/config.yml` (tunnel UUID + ingress rule) and the
matching credentials JSON (gitignored, copied separately).

## Project structure

```
vitalscan/
├── frontend/              React + Vite + TypeScript + Tailwind
│   ├── src/
│   │   ├── components/    UI components (Dashboard, BodyFigure, etc.)
│   │   ├── types/api.ts   Shared API contract types
│   │   ├── lib/           API client and status helpers
│   │   └── hooks/         useScan hook
│   └── Dockerfile
├── backend/               FastAPI + rPPG pipeline
│   ├── main.py            FastAPI app, /scan endpoint
│   ├── rppg/
│   │   ├── face_detection.py   Task 1 — MediaPipe FaceMesh + ROI
│   │   ├── pos_algorithm.py    Task 2 — POS + bandpass + FFT
│   │   ├── hrv.py              Task 3 — peak detection + SDNN
│   │   ├── pipeline.py         Full integration
│   │   ├── evaluation.py       Task 4 — MAE/RMSE on SCAMPS
│   │   └── mock.py             Mock data generator
│   └── Dockerfile
├── deploy/
│   └── cloudflared/
│       ├── config.yml          Tunnel UUID + ingress rule (committed)
│       └── <UUID>.json         TunnelSecret credentials (gitignored)
├── docker-compose.yml          backend + frontend + cloudflared
└── DEPLOY.md                   Three-command homelab deploy
```

## Group 1 team & task ownership

| Task                | File / artifact                          | Owner    |
|---------------------|------------------------------------------|----------|
| 1. Face + ROI       | `backend/rppg/face_detection.py`         | Daray    |
| 2. POS + heart rate | `backend/rppg/pos_algorithm.py`          | Daray    |
| 3. HRV + stress     | `backend/rppg/hrv.py`                    | Daray    |
| 4. Evaluation       | `backend/rppg/evaluation.py`             | Abner    |
| Dataset retrieval   | UBFC-rPPG · SCAMPS examples              | Jason    |
| API + frontend      | `backend/main.py` + `frontend/`          | Germaine |
| Deployment          | `docker-compose.yml` + Cloudflare Tunnel | Germaine |

## License

Academic project — Westcliff AIT 500.
