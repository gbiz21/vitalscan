# VitalScan — rPPG Signal Extraction (Group 1)

> **Academic class project for AIT 500 at Westcliff University — Group 1.**
> Built for coursework and demonstration only. **Not a medical device** and not
> for clinical or diagnostic use.

A Python rPPG pipeline that extracts heart rate, HRV, and a stress index from a
30-second facial video, exposed as a FastAPI `/scan` endpoint and consumed by a
React dashboard. Designed to **clone and run locally** — see [Quick start](#quick-start-local-dev) below.

**Live demo (optional):** https://vitalscan.bkre8tive.com

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
| 2 | Accuracy report — MAE / RMSE table vs. baseline | raw CSVs in [`data/compare_pos_chrom_*.csv`](data/) | ✅ |
| 3 | REST API `/scan` POST endpoint | [`backend/main.py`](backend/main.py) · runs locally (see Quick start) | ✅ |
| 4 | _Stretch_ — deep-learning comparison vs classical | future work — scaffolding in place, not executed | — |

> The full written reports, figures, and slide decks are course deliverables
> submitted through the LMS and are intentionally **not** included in this
> public repo (`docs/` is git-ignored) so the repository stays a clean
> clone-and-run project.

**Headline accuracy** (POS, our algorithm): **UBFC-rPPG MAE = 4.06 BPM on 42 real human subjects** — median absolute error 1.05 BPM, 90 % of subjects within ±10 BPM. CHROM baseline scores 3.86 BPM MAE on the same set (statistically tied). Both classical algorithms clear the rubric's < 10 BPM target.

## Build phases

| Phase | Status | What it does                                          |
|-------|--------|-------------------------------------------------------|
| 1     | ✅     | React UI with mock biomarker data                     |
| 2     | ✅     | FastAPI backend with mock `/scan` endpoint            |
| 3     | ✅     | Real rPPG pipeline (POS + CHROM, evaluated on UBFC + SCAMPS) |
| 4     | ✅     | Dockerized — full stack runs locally with one command |
| 5     | ✅     | Browser webcam capture                                |

## Datasets (download separately)

The video datasets are **not** committed (tens of GB — `data/` is git-ignored).
You do **not** need them just to run the app: by default the backend serves
mock data, and you can run a real scan on **any** webcam recording or video
file you upload. Download the research datasets only if you want to reproduce
the accuracy numbers.

| Dataset | Role | Size | Source |
|---|---|---|---|
| **UBFC-rPPG** (Bobbia et al. 2019) | 42 real subjects — headline MAE validation | ~75 GB | Request access on the authors' page: https://sites.google.com/view/ybenezeth/ubfcrppg |
| **SCAMPS** (McDuff et al. 2022) | 10 synthetic CGI subjects — stress test | ~1.2 GB | `curl -L -o scamps.tar.gz https://facesyntheticspubwedata.z6.web.core.windows.net/neurips-2022/scamps_videos_example.tar.gz` |

Place the extracted folders under `data/` (e.g. `data/ubfc_full`, `data/scamps_videos_example`) and reproduce with:

```bash
backend/venv312/bin/python -m rppg.evaluation --dataset data/ubfc_full --output data/eval_ubfc_full.csv
```

The pre-computed result CSVs (`data/compare_pos_chrom_*.csv`, `data/eval_*.csv`) **are** committed, so you can read the numbers without downloading anything.

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

## Quick start (Docker)

Run the whole stack locally with one command:

```bash
docker compose up --build
```

- Dashboard: http://localhost:8080
- API: http://localhost:8000 (e.g. `curl http://localhost:8000/biometrics`)

The frontend (nginx) proxies `/api/*` to the backend. Mock mode is on by
default; set `VITALSCAN_USE_MOCK=false` to run the real rPPG pipeline.

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
└── docker-compose.yml          backend + frontend (local stack)
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
| Local Docker stack  | `docker-compose.yml`                     | Germaine |

## License

Academic project — Westcliff AIT 500.
