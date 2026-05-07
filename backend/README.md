# Backend — rPPG Pipeline + FastAPI

## Quick start

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Visit http://localhost:8000/docs for the interactive API docs.

## Endpoints

- `GET /` — health check
- `POST /scan` — run pipeline on uploaded video, return biomarkers
- `POST /scan/mock` — return mock biomarkers (no video needed)

## Mock mode

By default the backend returns mock biomarker data. This lets the frontend
and Groups 3+4 develop without waiting for the real pipeline.

Set `VITALSCAN_USE_MOCK=false` to run the actual rPPG pipeline:

```bash
VITALSCAN_USE_MOCK=false uvicorn main:app
```

## Running the evaluation (Task 4)

```bash
# After downloading SCAMPS dataset
python -m rppg.evaluation --dataset /path/to/scamps --max-videos 50
```

Outputs an `eval_results.csv` and prints the MAE/RMSE summary table.

## File structure

```
backend/
├── main.py               FastAPI app
├── requirements.txt      Python deps
├── Dockerfile
└── rppg/
    ├── face_detection.py    Task 1
    ├── pos_algorithm.py     Task 2
    ├── hrv.py               Task 3
    ├── pipeline.py          Tasks 1+2+3 wired together
    ├── evaluation.py        Task 4
    └── mock.py              Mock data generator
```

## Task ownership notes

The pipeline is structurally complete but each individual task module is a
natural unit of work for one team member to own, refine, and validate:

- `face_detection.py`: tweak ROI landmark indices, handle motion robustness
- `pos_algorithm.py`: tune POS window size, FFT zero-padding, filter order
- `hrv.py`: refine peak detection prominence, validate stress sigmoid
- `evaluation.py`: implement the SCAMPS loader for your downloaded copy

## Dataset reminders

- **SCAMPS** (synthetic, 2,800 videos) — instant download, used for Task 4
- **UBFC-rPPG** (42 real subjects) — email request, takes 2-5 days
- **rPPG-Toolbox** — needed for Task 5 stretch (deep learning comparison)
- **MCD-rPPG** — Hugging Face, contains real biomarkers for BP grounding
