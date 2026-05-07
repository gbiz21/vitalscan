"""
VitalScan Group 1 — FastAPI server

Exposes the /scan endpoint that the frontend (and Groups 3/4) consume.

Endpoints:
  GET  /              health check
  POST /scan          run rPPG pipeline on uploaded video, return biomarkers
  POST /scan/mock     return mock biomarkers without running the pipeline
                      (useful for frontend dev and Groups 3+4 integration)
"""

import os
import shutil
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from rppg import generate_mock_biomarkers, run_pipeline

app = FastAPI(
    title="VitalScan rPPG API",
    description="Group 1 — extracts biomarkers from facial video via rPPG",
    version="0.1.0",
)

# CORS for local dev — tighten for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Toggle between real pipeline and mock data via env var
USE_MOCK = os.getenv("VITALSCAN_USE_MOCK", "true").lower() == "true"

ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov", ".avi", ".mkv"}
MAX_VIDEO_SIZE_MB = 100


@app.get("/")
def health_check():
    return {
        "service": "vitalscan-group1",
        "status": "ok",
        "mode": "mock" if USE_MOCK else "pipeline",
    }


@app.post("/scan")
async def scan(video: UploadFile = File(...)):
    """
    Run the rPPG pipeline on an uploaded video and return biomarkers.

    The frontend posts a 30-second facial video here. Returns JSON matching
    the shared API contract from the project brief.

    If VITALSCAN_USE_MOCK=true (default), returns mock data without running
    the pipeline — useful while the team is still building Tasks 1-3 or
    when running on hardware without GPU/MediaPipe support.
    """
    # Validate the upload
    if not video.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    extension = Path(video.filename).suffix.lower()
    if extension not in ALLOWED_VIDEO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported video format: {extension}. "
                   f"Allowed: {sorted(ALLOWED_VIDEO_EXTENSIONS)}",
        )

    # Mock mode — skip the heavy pipeline
    if USE_MOCK:
        return generate_mock_biomarkers()

    # Real pipeline mode — save the upload to a temp file, then process it
    with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as tmp:
        tmp_path = Path(tmp.name)
        try:
            shutil.copyfileobj(video.file, tmp)
            tmp.close()

            # Reject videos larger than the limit
            if tmp_path.stat().st_size > MAX_VIDEO_SIZE_MB * 1024 * 1024:
                raise HTTPException(
                    status_code=413,
                    detail=f"Video too large (max {MAX_VIDEO_SIZE_MB}MB)",
                )

            result = run_pipeline(str(tmp_path))
            return result.to_contract_dict()

        except (IOError, ValueError) as e:
            raise HTTPException(status_code=422, detail=str(e))
        finally:
            tmp_path.unlink(missing_ok=True)


@app.post("/scan/mock")
def scan_mock():
    """Always-mock endpoint, regardless of VITALSCAN_USE_MOCK setting."""
    return generate_mock_biomarkers()
