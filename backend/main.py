"""
VitalScan Group 1 — FastAPI server

Endpoints:
  GET  /              health check
  POST /scan          run rPPG pipeline on uploaded video, persist + return biomarkers
  POST /scan/mock     mock biomarkers (no video required) — frontend dev path
  GET  /biometrics    list every scan ever performed, newest first, one entry per scan
                      (Groups 3+4 hit this — filter client-side by the `person` field)
"""

import os
import shutil
import tempfile
from pathlib import Path

import json as _json

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from rppg import generate_mock_biomarkers
from rppg import scan_history


class PrettyJSONResponse(JSONResponse):
    """Indented JSON so curl + browser hits are human-readable.

    Adds ~5 bytes per line of whitespace — negligible. Any JSON parser
    (Python `json.loads`, JavaScript `JSON.parse`, Postman, etc.) treats
    pretty vs minified as identical input.
    """
    def render(self, content) -> bytes:
        return _json.dumps(content, indent=2, ensure_ascii=False).encode("utf-8")


app = FastAPI(
    title="VitalScan rPPG API",
    description="Group 1 — extracts biomarkers from facial video via rPPG",
    version="0.1.0",
    default_response_class=PrettyJSONResponse,
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
@app.get("/health")
def health_check():
    return {
        "service": "vitalscan-group1",
        "status": "ok",
        "mode": "mock" if USE_MOCK else "pipeline",
    }


@app.post("/scan")
async def scan(
    video: UploadFile = File(...),
    person: str | None = Form(default=None),
):
    """
    Run the rPPG pipeline on an uploaded video and return biomarkers.

    The frontend posts a 30-second facial video here. Returns JSON matching
    the shared API contract from the project brief, plus a generated
    `scan_id` and `timestamp` so Groups 3+4 can retrieve the same result
    later via GET /scans/{scan_id}.

    Optional `person` form field lets the requester tag their scan
    (e.g. "Daray test #3") — never required, never persisted as PII.

    If VITALSCAN_USE_MOCK=true (default), returns mock data without running
    the pipeline.
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

    # Mock mode — skip the heavy pipeline but still persist + return a scan_id
    if USE_MOCK:
        biomarkers_payload = generate_mock_biomarkers()
        entry = scan_history.append_scan(
            biomarkers_payload["biomarkers"],
            mode="mock",
            video_size_bytes=0,
            person=person,
        )
        return {
            "scan_id": entry["scan_id"],
            "timestamp": entry["timestamp"],
            "mode": "mock",
            "person": person,
            **biomarkers_payload,        # keeps {"biomarkers": {...}}
        }

    # Real pipeline mode — save the upload to a temp file, then process it
    with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as tmp:
        tmp_path = Path(tmp.name)
        try:
            shutil.copyfileobj(video.file, tmp)
            tmp.close()

            # Reject videos larger than the limit
            video_size = tmp_path.stat().st_size
            if video_size > MAX_VIDEO_SIZE_MB * 1024 * 1024:
                raise HTTPException(
                    status_code=413,
                    detail=f"Video too large (max {MAX_VIDEO_SIZE_MB}MB)",
                )

            # Imported lazily so mock mode does not require cv2 / mediapipe.
            from rppg.pipeline import run_pipeline

            result = run_pipeline(str(tmp_path))
            biomarkers_payload = result.to_contract_dict()
            entry = scan_history.append_scan(
                biomarkers_payload["biomarkers"],
                mode="pipeline",
                video_size_bytes=video_size,
                person=person,
            )
            return {
                "scan_id": entry["scan_id"],
                "timestamp": entry["timestamp"],
                "mode": "pipeline",
                "person": person,
                **biomarkers_payload,
            }

        except (IOError, ValueError) as e:
            raise HTTPException(status_code=422, detail=str(e))
        finally:
            tmp_path.unlink(missing_ok=True)


@app.post("/scan/mock")
def scan_mock_post():
    """Always-mock POST endpoint — preserved for the frontend dev path."""
    return generate_mock_biomarkers()


@app.get("/biometrics")
def list_biometrics(limit: int = 200, person: str | None = None):
    """The one endpoint Groups 3+4 hit — every scan, newest first.

    Each entry is one scan, in this shape:

        {
          "scan_id":         "scan_xxxxxxxxxxxx",
          "timestamp":       "2026-05-20T15:30:12+00:00",
          "mode":            "pipeline" | "mock",
          "person":          "Daray"  (or null if no name given on POST),
          "biomarkers": {
            "heart_rate":    72,
            "hrv_sdnn":      45,
            "stress_index":  0.6,
            "blood_pressure": { "systolic": 138, "diastolic": 88 }
          }
        }

    Optional query params:
      ?person={name}  — filter to one person (server-side convenience)
      ?limit={N}      — cap the number of entries returned (default 200)
    """
    scans = scan_history.list_scans(limit=max(1, min(limit, 500)))
    if person is not None:
        scans = [s for s in scans if (s.get("person") or "").lower() == person.lower()]
    return {"count": len(scans), "scans": scans}
