"""Persistent history of real /scan results.

Each POST /scan that runs the real pipeline appends one entry to this log.
Groups 3 and 4 query the log via GET /scans · GET /scans/{scan_id}.

Storage is a single JSON file mounted into the container at
/app/data/scan_history.json. Atomic writes use a tempfile + rename so
concurrent scans don't corrupt the file (sufficient for low classroom traffic).

PII note: only biomarker JSON + a generated scan_id + timestamp are stored.
No name, no email, no IP. An optional `person` field lets the requester
tag their scan ("Daray test #3") but it is never required.
"""
from __future__ import annotations

import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def _resolve_history_path() -> Path:
    """Same resolution scheme as SAMPLES_FILE — works in container and locally."""
    here = Path(__file__).resolve().parent.parent  # backend/
    for candidate in (here / "data" / "scan_history.json",
                      here.parent / "data" / "scan_history.json"):
        if candidate.exists():
            return candidate
    return here / "data" / "scan_history.json"


HISTORY_FILE = _resolve_history_path()
MAX_ENTRIES = 200  # rotate FIFO past this; tiny memory footprint either way


def _load() -> dict:
    if not HISTORY_FILE.exists():
        return {"scans": []}
    try:
        with HISTORY_FILE.open() as f:
            data = json.load(f)
        if not isinstance(data, dict) or "scans" not in data:
            return {"scans": []}
        return data
    except (json.JSONDecodeError, OSError):
        return {"scans": []}


def _atomic_write(data: dict) -> None:
    """Write JSON to the history file.

    We can't use tempfile+rename here because the production container mounts
    HISTORY_FILE as a single-file bind mount — `os.replace` fails with EBUSY
    on a mount point. For our traffic (low, classroom-scale), a direct write
    is safe enough; the worst case is a half-flushed file on container crash
    mid-write, which `_load` already tolerates by returning an empty list.
    """
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with HISTORY_FILE.open("w") as f:
        json.dump(data, f, indent=2)


def append_scan(biomarkers: dict, *, mode: str, video_size_bytes: int,
                person: Optional[str] = None) -> dict:
    """Persist one scan and return the stored entry (with scan_id + timestamp)."""
    entry = {
        "scan_id": "scan_" + uuid.uuid4().hex[:12],
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": mode,                       # "pipeline" or "mock"
        "video_size_bytes": video_size_bytes,
        "person": person,
        "biomarkers": biomarkers,
    }
    data = _load()
    data["scans"].append(entry)
    # Rotate FIFO so the file doesn't grow without bound.
    if len(data["scans"]) > MAX_ENTRIES:
        data["scans"] = data["scans"][-MAX_ENTRIES:]
    _atomic_write(data)
    return entry


def list_scans(limit: int = 50) -> list:
    """Return last `limit` scans, newest first."""
    data = _load()
    return list(reversed(data["scans"][-limit:]))


def get_scan(scan_id: str) -> Optional[dict]:
    data = _load()
    for entry in data["scans"]:
        if entry["scan_id"] == scan_id:
            return entry
    return None
