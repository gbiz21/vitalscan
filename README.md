# VitalScan — Group 1 (rPPG Signal Extraction)

AIT 500 Course Project · Westcliff University · Group 1

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
| 4     | ✅     | Docker + Traefik deployment                           |
| 5     | ✅     | Browser webcam capture                                |

**Phase 3 status:** the algorithm code (face detection, POS, HRV) is written
and structurally complete. To finish the assignment, the team needs to:
1. Run it against SCAMPS videos and compute MAE
2. Email the UBFC-rPPG dataset authors for access
3. Tune any constants based on accuracy results

## Quick start (local dev)

```bash
# Terminal 1 — backend
cd backend
python -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — the dashboard will pull biomarker data from
http://localhost:8000/scan.

By default the backend returns mock data. To run the real pipeline, send
a video file to `/scan` (the frontend webcam capture does this automatically).

## Quick start (Docker, for homelab deploy)

```bash
docker compose up -d
```

The `docker-compose.yml` includes Traefik labels — adjust the `Host()` rule
to your homelab domain.

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
└── docker-compose.yml     Both services + Traefik labels
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
