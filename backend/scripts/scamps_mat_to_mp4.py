"""Convert SCAMPS .mat synthetic-avatar clips into playable .mp4 files.

SCAMPS stores clips as MATLAB v7.3 (HDF5 under the hood) with the video
frames in an 'Xsub' tensor shaped (channels, height, width, frames). To make
them double-clickable in Finder / QuickTime / VLC, we transpose to
(frames, height, width, channels), scale float[0,1] to uint8, and write an
H.264 .mp4 next to the source.

Run:
    backend/venv312/bin/python backend/scripts/scamps_mat_to_mp4.py
        # converts every .mat in data/scamps_videos_example/

Optional args: any number of .mat paths to convert just those files.
"""
import sys
from pathlib import Path

import cv2
import h5py
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT / "data" / "scamps_videos_example"
OUT_DIR = ROOT / "data" / "scamps_videos_example_mp4"
FPS = 30  # SCAMPS clips are 30 fps (McDuff et al. 2022)


def convert_one(mat_path: Path, out_dir: Path) -> Path:
    out_path = out_dir / (mat_path.stem + ".mp4")

    with h5py.File(str(mat_path), "r") as f:
        if "Xsub" not in f:
            raise KeyError(f"{mat_path.name}: no 'Xsub' key (keys = {list(f.keys())})")
        arr = f["Xsub"][()]  # (3, H, W, T) — float64 in [0, 1]

    # SCAMPS stores as (channels, H, W, frames) — transpose to (frames, H, W, channels)
    frames = np.transpose(arr, (3, 1, 2, 0))
    n, h, w, c = frames.shape
    assert c == 3, f"expected 3 channels, got {c}"

    # Float [0,1] -> uint8 [0,255], and RGB -> BGR for OpenCV
    frames_u8 = (np.clip(frames, 0, 1) * 255).astype(np.uint8)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(out_path), fourcc, FPS, (w, h))
    if not writer.isOpened():
        raise RuntimeError(f"OpenCV could not open writer for {out_path}")

    for f_idx in range(n):
        bgr = cv2.cvtColor(frames_u8[f_idx], cv2.COLOR_RGB2BGR)
        # SCAMPS Xsub axes land in (W, H) order after our transpose, so each
        # frame plays sideways in QuickTime. Rotate 90° CW to put the head up.
        bgr = cv2.rotate(bgr, cv2.ROTATE_90_CLOCKWISE)
        writer.write(bgr)
    writer.release()

    return out_path


def main(argv):
    out_dir = OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    if len(argv) > 1:
        mat_paths = [Path(p) for p in argv[1:]]
    else:
        mat_paths = sorted(SRC_DIR.glob("*.mat"))

    if not mat_paths:
        print(f"No .mat files found in {SRC_DIR}")
        return

    print(f"Converting {len(mat_paths)} file(s) → {out_dir}/")
    for mat in mat_paths:
        try:
            out = convert_one(mat, out_dir)
            size_mb = out.stat().st_size / (1024 * 1024)
            print(f"  ✓ {mat.name:20s} → {out.name:20s} ({size_mb:.1f} MB)")
        except Exception as e:
            print(f"  ✗ {mat.name}: {e}")


if __name__ == "__main__":
    main(sys.argv)
