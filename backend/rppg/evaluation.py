"""
Task 4 — Accuracy Evaluation
============================

Validates the pipeline against a dataset with ground truth heart rates.
Reports Mean Absolute Error (MAE) and Root Mean Square Error (RMSE) for
heart rate predictions, plus a comparison table.

Usage:
    python -m rppg.evaluation --dataset /path/to/scamps_videos_example
    python -m rppg.evaluation --dataset /path/to/scamps_videos_example --max-videos 5

The grading rubric requires MAE < 10 BPM on SCAMPS for full marks,
and MAE < 5 BPM earns stretch credit.

Two dataset layouts are supported:
  - SCAMPS (Microsoft): directory of .mat (HDF5 v7.3) files, each with
    Xsub (3, H, W, T) RGB frames and d_ppg (T, 1) ground-truth PPG.
  - Generic mp4+npy: directory of *.mp4 paired with same-named *.npy
    PPG arrays (used by some smaller in-house datasets).
"""

import argparse
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple

import cv2
import h5py
import numpy as np
import pandas as pd

from .pipeline import run_pipeline

SCAMPS_FPS = 30.0


@dataclass
class VideoSample:
    """One video + its ground truth heart rate."""
    video_path: str
    ground_truth_bpm: float
    sample_id: str = ""


@dataclass
class PredictionResult:
    sample_id: str
    ground_truth_bpm: float
    predicted_bpm: float
    error_bpm: float


def _scamps_mat_to_video(mat_path: Path, out_path: Path, fps: float = SCAMPS_FPS) -> int:
    """Write Xsub frames from a SCAMPS .mat file out to an .mp4. Returns frame count."""
    with h5py.File(mat_path, "r") as f:
        xsub = f["Xsub"][:]  # (3, H, W, T), float in [0, 1]
    # SCAMPS stores frames as (channels, H, W, frames). cv2 wants (H, W, channels) BGR.
    frames = np.transpose(xsub, (3, 1, 2, 0))            # (T, H, W, 3) RGB
    frames = (np.clip(frames, 0, 1) * 255).astype(np.uint8)
    frames_bgr = frames[..., ::-1]                        # RGB -> BGR

    h, w = frames_bgr.shape[1], frames_bgr.shape[2]
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(out_path), fourcc, fps, (w, h))
    if not writer.isOpened():
        raise RuntimeError(f"cv2.VideoWriter failed to open {out_path}")
    for frame in frames_bgr:
        writer.write(frame)
    writer.release()
    return len(frames_bgr)


def _scamps_ground_truth_bpm(mat_path: Path, fps: float = SCAMPS_FPS) -> float:
    """Compute ground-truth HR from the SCAMPS d_ppg waveform via FFT."""
    with h5py.File(mat_path, "r") as f:
        ppg = f["d_ppg"][:].squeeze()
    return _ppg_to_bpm(ppg, fps)


def _ppg_to_bpm(ppg: np.ndarray, fps: float) -> float:
    """FFT-based dominant frequency of a PPG waveform, in BPM."""
    from scipy.signal import detrend
    sig = detrend(np.asarray(ppg, dtype=float))
    if len(sig) < int(fps * 5):
        raise ValueError("PPG signal too short for reliable FFT")
    n_pad = max(8192, len(sig) * 4)
    fft = np.fft.rfft(sig, n=n_pad)
    freqs = np.fft.rfftfreq(n_pad, d=1.0 / fps)
    mask = (freqs >= 0.7) & (freqs <= 4.0)            # 42-240 BPM
    peak = freqs[mask][np.argmax(np.abs(fft[mask]))]
    return float(peak * 60.0)


def load_scamps_videos(scamps_root: Path, max_videos: int = 50,
                       tmp_dir: Path | None = None) -> List[VideoSample]:
    """Load SCAMPS .mat files and stage them as temporary .mp4 + ground truth."""
    if tmp_dir is None:
        tmp_dir = Path(tempfile.mkdtemp(prefix="scamps_videos_"))
    tmp_dir.mkdir(parents=True, exist_ok=True)

    mat_files = sorted(scamps_root.glob("*.mat"))[:max_videos]
    samples: List[VideoSample] = []

    for mat_path in mat_files:
        try:
            video_path = tmp_dir / (mat_path.stem + ".mp4")
            n_frames = _scamps_mat_to_video(mat_path, video_path)
            gt_bpm = _scamps_ground_truth_bpm(mat_path)
            samples.append(
                VideoSample(
                    video_path=str(video_path),
                    ground_truth_bpm=gt_bpm,
                    sample_id=mat_path.stem,
                )
            )
            print(f"  staged {mat_path.name}: {n_frames} frames, GT={gt_bpm:.1f} BPM")
        except Exception as e:
            print(f"  skipped {mat_path.name}: {e}", file=sys.stderr)
    return samples


def load_generic_videos(root: Path, max_videos: int = 50) -> List[VideoSample]:
    """Generic loader for in-house datasets: *.mp4 paired with same-name *.npy PPG."""
    samples: List[VideoSample] = []
    for video_path in sorted(root.glob("*.mp4"))[:max_videos]:
        gt_file = video_path.with_suffix(".npy")
        if not gt_file.exists():
            print(f"  skipped {video_path.name}: no ground truth .npy")
            continue
        ppg = np.load(gt_file)
        samples.append(
            VideoSample(
                video_path=str(video_path),
                ground_truth_bpm=_ppg_to_bpm(ppg, fps=SCAMPS_FPS),
                sample_id=video_path.stem,
            )
        )
    return samples


def load_dataset(root: Path, max_videos: int = 50) -> List[VideoSample]:
    """Auto-detect SCAMPS (.mat) vs generic (.mp4 + .npy) layout."""
    if any(root.glob("*.mat")):
        print(f"Detected SCAMPS .mat layout under {root}")
        return load_scamps_videos(root, max_videos=max_videos)
    if any(root.glob("*.mp4")):
        print(f"Detected generic .mp4 + .npy layout under {root}")
        return load_generic_videos(root, max_videos=max_videos)
    raise FileNotFoundError(f"No .mat or .mp4 files in {root}")


def evaluate(samples: Iterable[VideoSample]) -> List[PredictionResult]:
    """Run the pipeline on every sample and collect results."""
    results: List[PredictionResult] = []
    for i, sample in enumerate(samples, 1):
        try:
            biomarkers = run_pipeline(sample.video_path)
            predicted = float(biomarkers.heart_rate)
            error = predicted - sample.ground_truth_bpm
            results.append(
                PredictionResult(
                    sample_id=sample.sample_id,
                    ground_truth_bpm=sample.ground_truth_bpm,
                    predicted_bpm=predicted,
                    error_bpm=error,
                )
            )
            print(f"[{i}] {sample.sample_id}: "
                  f"GT={sample.ground_truth_bpm:.1f}, "
                  f"Pred={predicted:.1f}, "
                  f"Err={error:+.1f}")
        except Exception as e:
            print(f"[{i}] {sample.sample_id}: FAILED — {e}", file=sys.stderr)
    return results


def compute_metrics(results: List[PredictionResult]) -> Tuple[float, float]:
    """Compute MAE and RMSE in BPM."""
    if not results:
        return float("nan"), float("nan")
    errors = np.array([r.error_bpm for r in results])
    mae = float(np.mean(np.abs(errors)))
    rmse = float(np.sqrt(np.mean(errors ** 2)))
    return mae, rmse


def save_results_csv(results: List[PredictionResult], output_path: Path) -> None:
    df = pd.DataFrame([vars(r) for r in results])
    df.to_csv(output_path, index=False)
    print(f"Results saved to {output_path}")


def print_summary_table(mae: float, rmse: float, n_samples: int) -> None:
    print("\n" + "=" * 56)
    print(f"{'Algorithm':<20} {'MAE (BPM)':<15} {'RMSE (BPM)':<15}")
    print("-" * 56)
    print(f"{'POS (ours)':<20} {mae:<15.2f} {rmse:<15.2f}")
    print("=" * 56)
    print(f"{n_samples} videos evaluated")
    print(f"\nGrading targets:")
    print(f"  MAE < 10 BPM -> full marks    ({'PASS' if mae < 10 else 'FAIL'})")
    print(f"  MAE < 5  BPM -> stretch credit ({'PASS' if mae < 5  else 'FAIL'})")


def main():
    parser = argparse.ArgumentParser(description="Evaluate rPPG pipeline")
    parser.add_argument("--dataset", type=Path, required=True, help="Path to dataset root")
    parser.add_argument("--max-videos", type=int, default=50, help="Max videos to evaluate")
    parser.add_argument("--output", type=Path, default=Path("eval_results.csv"))
    args = parser.parse_args()

    print(f"Loading samples from {args.dataset}...")
    samples = load_dataset(args.dataset, max_videos=args.max_videos)
    print(f"Loaded {len(samples)} samples\n")
    if not samples:
        print("No samples found - check the dataset path and file structure.")
        sys.exit(1)

    results = evaluate(samples)
    mae, rmse = compute_metrics(results)
    save_results_csv(results, args.output)
    print_summary_table(mae, rmse, len(results))


if __name__ == "__main__":
    main()
