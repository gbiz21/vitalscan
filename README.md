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

## Build phases

| Phase | Status | What it does                                          |
|-------|--------|-------------------------------------------------------|
| 1     | ✅     | React UI with mock biomarker data                     |
| 2     | ✅     | FastAPI backend with mock `/scan` endpoint            |
| 3     | 🟡     | Real rPPG pipeline (algorithms in place, needs data)  |
| 4     | ✅     | Docker + Cloudflare Tunnel deployment (live)          |
| 5     | ✅     | Browser webcam capture                                |

**Phase 3 status:** the algorithm code (face detection, POS, HRV) is written
and structurally complete. To finish the assignment, the team needs to:
1. Run it against SCAMPS videos and compute MAE
2. Email the UBFC-rPPG dataset authors for access
3. Tune any constants based on accuracy results

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

## Group 1 task ownership (suggested)

| Task              | File                       | Owner |
|-------------------|----------------------------|-------|
| 1. Face + ROI     | `backend/rppg/face_detection.py` | TBD   |
| 2. POS + heart rate | `backend/rppg/pos_algorithm.py` | TBD   |
| 3. HRV + stress   | `backend/rppg/hrv.py`      | TBD   |
| 4. Evaluation     | `backend/rppg/evaluation.py` | TBD   |
| API + frontend    | `backend/main.py` + `frontend/` | Germaine |

## License

Academic project — Westcliff AIT 500.
