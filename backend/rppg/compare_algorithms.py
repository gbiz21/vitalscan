"""
POS vs CHROM Comparison Runner
==============================

Runs both POS (ours) and CHROM (baseline) on the same dataset, extracting
the facial ROI once per video so the comparison only differs by algorithm,
not by face-detection variance.

Output: a CSV with columns
    sample_id, gt_bpm, pos_bpm, chrom_bpm, pos_error, chrom_error
plus a printed MAE/RMSE summary for each algorithm — matching the rubric's
"Algorithm | MAE | RMSE" table.

Usage:
    python -m rppg.compare_algorithms --dataset data/ubfc_full/UBFC_DATASET/DATASET_2 \
        --output data/compare_pos_chrom_ubfc.csv
    python -m rppg.compare_algorithms --dataset data/scamps_videos_example \
        --output data/compare_pos_chrom_scamps.csv
"""

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List

import numpy as np
import pandas as pd

from .chrom_baseline import extract_heart_rate_chrom
from .evaluation import VideoSample, compute_metrics, load_dataset
from .face_detection import FaceROIExtractor
from .pos_algorithm import extract_heart_rate as extract_heart_rate_pos


@dataclass
class CompareResult:
    sample_id: str
    gt_bpm: float
    pos_bpm: float
    chrom_bpm: float

    @property
    def pos_error(self) -> float:
        return self.pos_bpm - self.gt_bpm

    @property
    def chrom_error(self) -> float:
        return self.chrom_bpm - self.gt_bpm


def run_both_algorithms(sample: VideoSample) -> CompareResult:
    """Extract RGB once from the video, then run POS and CHROM on it."""
    extractor = FaceROIExtractor()
    try:
        rgb_series, fps = extractor.process_video(sample.video_path)
    finally:
        extractor.close()

    pos_bpm, _ = extract_heart_rate_pos(rgb_series, fps)
    chrom_bpm, _ = extract_heart_rate_chrom(rgb_series, fps)

    return CompareResult(
        sample_id=sample.sample_id,
        gt_bpm=sample.ground_truth_bpm,
        pos_bpm=float(pos_bpm),
        chrom_bpm=float(chrom_bpm),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="POS vs CHROM comparison harness")
    parser.add_argument("--dataset", type=Path, required=True, help="Path to dataset root")
    parser.add_argument("--max-videos", type=int, default=50)
    parser.add_argument("--output", type=Path, default=Path("compare_pos_chrom.csv"))
    args = parser.parse_args()

    print(f"Loading samples from {args.dataset}...")
    samples = load_dataset(args.dataset, max_videos=args.max_videos)
    print(f"Loaded {len(samples)} samples\n")

    results: List[CompareResult] = []
    for i, sample in enumerate(samples, 1):
        try:
            r = run_both_algorithms(sample)
            results.append(r)
            print(
                f"[{i:>3}/{len(samples)}] {r.sample_id}: "
                f"GT={r.gt_bpm:6.1f}  "
                f"POS={r.pos_bpm:6.1f} (err={r.pos_error:+6.1f})  "
                f"CHROM={r.chrom_bpm:6.1f} (err={r.chrom_error:+6.1f})"
            )
        except Exception as exc:
            print(f"[{i:>3}/{len(samples)}] {sample.sample_id}: FAILED — {exc}", file=sys.stderr)

    if not results:
        print("No successful predictions — aborting.", file=sys.stderr)
        sys.exit(1)

    df = pd.DataFrame(
        [
            {
                "sample_id": r.sample_id,
                "gt_bpm": r.gt_bpm,
                "pos_bpm": r.pos_bpm,
                "chrom_bpm": r.chrom_bpm,
                "pos_error": r.pos_error,
                "chrom_error": r.chrom_error,
            }
            for r in results
        ]
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.output, index=False)
    print(f"\nSaved {len(df)} rows to {args.output}")

    pos_errs = np.array([r.pos_error for r in results])
    chrom_errs = np.array([r.chrom_error for r in results])
    pos_mae, pos_rmse = float(np.mean(np.abs(pos_errs))), float(np.sqrt(np.mean(pos_errs ** 2)))
    chrom_mae, chrom_rmse = float(np.mean(np.abs(chrom_errs))), float(np.sqrt(np.mean(chrom_errs ** 2)))

    n = len(results)
    print("\n" + "=" * 60)
    print(f"{'Algorithm':<22}{'MAE (BPM)':>12}{'RMSE (BPM)':>14}{'n':>8}")
    print("-" * 60)
    print(f"{'POS (ours)':<22}{pos_mae:>12.2f}{pos_rmse:>14.2f}{n:>8}")
    print(f"{'CHROM (baseline)':<22}{chrom_mae:>12.2f}{chrom_rmse:>14.2f}{n:>8}")
    print("=" * 60)


if __name__ == "__main__":
    main()
