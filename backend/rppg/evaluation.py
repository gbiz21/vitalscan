"""
Task 4 — Accuracy Evaluation
============================

Validates the pipeline against a dataset with ground truth heart rates.
Reports Mean Absolute Error (MAE) and Root Mean Square Error (RMSE) for
heart rate predictions, plus a comparison table.

Usage:
    python -m rppg.evaluation --dataset /path/to/scamps --max-videos 50

The grading rubric requires MAE < 10 BPM on SCAMPS for full marks,
and MAE < 5 BPM earns stretch credit.

This module is a framework — the actual SCAMPS data loading depends on
how your team chooses to organize the downloaded dataset. The placeholder
`load_scamps_videos()` function shows the expected interface.
"""

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple

import numpy as np
import pandas as pd

from .pipeline import run_pipeline


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


def load_scamps_videos(scamps_root: Path, max_videos: int = 50) -> List[VideoSample]:
    """
    Load SCAMPS video samples with ground truth heart rates.

    SCAMPS provides synthetic videos with paired ground truth PPG signals.
    The ground truth heart rate is derived from the PPG file that comes
    with each video. Adjust this loader to match your downloaded structure.

    Expected SCAMPS file layout (after extraction):
        scamps_root/
            video_001.mp4
            video_001.npy        # ground truth PPG signal
            ...

    Or whatever convention your downloaded copy uses — this is a placeholder.
    """
    samples: List[VideoSample] = []
    video_files = sorted(scamps_root.glob("*.mp4"))[:max_videos]

    for video_path in video_files:
        gt_file = video_path.with_suffix(".npy")
        if not gt_file.exists():
            print(f"⚠ Skipping {video_path.name} — no ground truth file")
            continue

        # Load the ground truth PPG signal and estimate its dominant frequency
        ppg = np.load(gt_file)
        # Assume 30 fps for SCAMPS (adjust if your version differs)
        gt_bpm = estimate_gt_bpm(ppg, fps=30.0)

        samples.append(
            VideoSample(
                video_path=str(video_path),
                ground_truth_bpm=gt_bpm,
                sample_id=video_path.stem,
            )
        )

    return samples


def estimate_gt_bpm(ppg_signal: np.ndarray, fps: float) -> float:
    """Get the ground-truth heart rate from a clean reference PPG signal."""
    from .pos_algorithm import butter_bandpass, estimate_heart_rate_fft

    filtered = butter_bandpass(ppg_signal, fps)
    bpm, _, _ = estimate_heart_rate_fft(filtered, fps)
    return bpm


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
    print(f"📁 Results saved to {output_path}")


def print_summary_table(mae: float, rmse: float, n_samples: int) -> None:
    print("\n" + "=" * 56)
    print(f"{'Algorithm':<20} {'MAE (BPM)':<15} {'RMSE (BPM)':<15}")
    print("-" * 56)
    print(f"{'POS (ours)':<20} {mae:<15.2f} {rmse:<15.2f}")
    print("=" * 56)
    print(f"{n_samples} videos evaluated")
    print(f"\nGrading targets:")
    print(f"  MAE < 10 BPM → full marks   ({'✅' if mae < 10 else '❌'})")
    print(f"  MAE < 5 BPM  → stretch credit ({'✅' if mae < 5 else '❌'})")


def main():
    parser = argparse.ArgumentParser(description="Evaluate rPPG pipeline against SCAMPS")
    parser.add_argument("--dataset", type=Path, required=True, help="Path to SCAMPS root")
    parser.add_argument("--max-videos", type=int, default=50, help="Max videos to evaluate")
    parser.add_argument("--output", type=Path, default=Path("eval_results.csv"))
    args = parser.parse_args()

    print(f"Loading SCAMPS samples from {args.dataset}...")
    samples = load_scamps_videos(args.dataset, max_videos=args.max_videos)
    print(f"Loaded {len(samples)} samples\n")

    if not samples:
        print("No samples found — check the dataset path and file structure.")
        sys.exit(1)

    results = evaluate(samples)
    mae, rmse = compute_metrics(results)
    save_results_csv(results, args.output)
    print_summary_table(mae, rmse, len(results))


if __name__ == "__main__":
    main()
