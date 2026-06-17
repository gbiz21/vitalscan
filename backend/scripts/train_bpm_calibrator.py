"""
Train a heart-rate calibration model on top of the classical rPPG pipeline.

Group 1's core extraction (MediaPipe ROI -> POS/CHROM -> bandpass -> FFT peak)
is physics-based and has no learnable weights. This script adds the one genuinely
*trained* component in the project: a supervised regressor that takes the raw
POS/CHROM outputs as features and learns to predict the ground-truth BPM,
correcting the pipeline's systematic error.

Input  : data/compare_pos_chrom_ubfc.csv  (42 UBFC subjects: gt, pos, chrom)
Output : data/eval_ubfc_calibrated.csv     (per-subject corrected predictions)
         docs/wk6_calibration_metrics.json (metrics for the Week 6 report)

Evaluation is leave-one-out cross-validation (LOOCV) -- with only 42 samples a
single split is too noisy, so every subject is predicted while held out of
training. A fixed 70/30 split is also reported for the train/test narrative.

Run: backend/venv312/bin/python backend/scripts/train_bpm_calibrator.py
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression, Ridge, HuberRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import LeaveOneOut, train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error

SEED = 42
REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "data" / "compare_pos_chrom_ubfc.csv"
OUT_CSV = REPO / "data" / "eval_ubfc_calibrated.csv"
OUT_JSON = REPO / "docs" / "wk6_calibration_metrics.json"


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Feature engineering from the two classical estimators.

    `abs_diff` is the key quality signal: when POS and CHROM agree the estimate
    is usually trustworthy; large disagreement flags a noisy video (e.g. subject32,
    where POS=96 is wrong but CHROM=116 is right).
    """
    feats = pd.DataFrame()
    feats["pos_bpm"] = df["pos_bpm"]
    feats["chrom_bpm"] = df["chrom_bpm"]
    feats["mean_bpm"] = (df["pos_bpm"] + df["chrom_bpm"]) / 2.0
    feats["abs_diff"] = (df["pos_bpm"] - df["chrom_bpm"]).abs()
    return feats


def error_distribution(abs_err: np.ndarray) -> dict:
    n = len(abs_err)
    return {
        f"within_{t}_bpm": {
            "count": int((abs_err <= t).sum()),
            "pct": round(100.0 * (abs_err <= t).sum() / n, 1),
        }
        for t in (1, 3, 5, 10, 15)
    }


def metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    abs_err = np.abs(y_pred - y_true)
    return {
        "mae": round(float(mean_absolute_error(y_true, y_pred)), 3),
        "rmse": round(float(np.sqrt(mean_squared_error(y_true, y_pred))), 3),
        "median_abs_err": round(float(np.median(abs_err)), 3),
        "max_abs_err": round(float(abs_err.max()), 3),
        "distribution": error_distribution(abs_err),
    }


def loocv_predict(model_factory, X: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Out-of-fold prediction for every sample via leave-one-out CV."""
    preds = np.zeros_like(y, dtype=float)
    loo = LeaveOneOut()
    for train_idx, test_idx in loo.split(X):
        model = model_factory()
        model.fit(X[train_idx], y[train_idx])
        preds[test_idx] = model.predict(X[test_idx])
    return preds


def main() -> None:
    df = pd.read_csv(DATA)
    X = build_features(df)
    y = df["gt_bpm"].to_numpy()
    Xv = X.to_numpy()
    n = len(y)

    # ---- Baselines: raw POS, and the no-learning POS/CHROM average ----
    baseline = metrics(y, df["pos_bpm"].to_numpy())
    baseline_mean = metrics(y, ((df["pos_bpm"] + df["chrom_bpm"]) / 2.0).to_numpy())

    # ---- Candidate models ----
    factories = {
        "linear_regression": lambda: LinearRegression(),
        "ridge_alpha_1.0": lambda: Ridge(alpha=1.0, random_state=SEED),
        "huber_robust": lambda: HuberRegressor(epsilon=1.35, max_iter=2000),
        "random_forest": lambda: RandomForestRegressor(
            n_estimators=200, max_depth=3, random_state=SEED
        ),
    }

    # ---- LOOCV (the honest metric for 42 samples) ----
    loocv = {}
    oof_preds = {}
    for name, factory in factories.items():
        preds = loocv_predict(factory, Xv, y)
        oof_preds[name] = preds
        loocv[name] = metrics(y, preds)

    # ---- Fixed 70/30 train/test split (for the report's train/test narrative) ----
    X_tr, X_te, y_tr, y_te = train_test_split(
        Xv, y, test_size=0.30, random_state=SEED
    )
    split = {}
    for name, factory in factories.items():
        model = factory()
        model.fit(X_tr, y_tr)
        split[name] = {
            "n_train": int(len(y_tr)),
            "n_test": int(len(y_te)),
            "train": metrics(y_tr, model.predict(X_tr)),
            "test": metrics(y_te, model.predict(X_te)),
        }

    # ---- Pick the best model by LOOCV MAE; refit on all data for coefficients ----
    best_name = min(loocv, key=lambda k: loocv[k]["mae"])
    best = factories[best_name]()
    best.fit(Xv, y)
    coefs = None
    if hasattr(best, "coef_"):
        coefs = {
            "intercept": round(float(best.intercept_), 4),
            **{c: round(float(w), 4) for c, w in zip(X.columns, best.coef_)},
        }
    elif hasattr(best, "feature_importances_"):
        coefs = {
            c: round(float(w), 4)
            for c, w in zip(X.columns, best.feature_importances_)
        }

    # ---- Persist per-subject corrected predictions (best model, OOF) ----
    out = df[["sample_id", "gt_bpm", "pos_bpm", "chrom_bpm"]].copy()
    out["calibrated_bpm"] = np.round(oof_preds[best_name], 2)
    out["pos_abs_err"] = np.round(np.abs(df["pos_bpm"] - y), 2)
    out["calibrated_abs_err"] = np.round(np.abs(oof_preds[best_name] - y), 2)
    out.to_csv(OUT_CSV, index=False)

    report = {
        "dataset": "UBFC-rPPG",
        "n_subjects": n,
        "seed": SEED,
        "features": list(X.columns),
        "baseline_pos": baseline,
        "baseline_poschrom_avg": baseline_mean,
        "loocv": loocv,
        "train_test_split": split,
        "best_model": best_name,
        "best_model_coefficients": coefs,
        "improvement_mae": {
            "baseline": baseline["mae"],
            "calibrated_loocv": loocv[best_name]["mae"],
            "delta": round(baseline["mae"] - loocv[best_name]["mae"], 3),
            "pct": round(
                100.0 * (baseline["mae"] - loocv[best_name]["mae"]) / baseline["mae"], 1
            ),
        },
    }
    OUT_JSON.write_text(json.dumps(report, indent=2))

    # ---- Console summary ----
    print("=" * 64)
    print(f"HEART-RATE CALIBRATION MODEL  ·  UBFC-rPPG  ·  N={n}")
    print("=" * 64)
    print(f"\nBaseline (raw POS, no model):       MAE {baseline['mae']:.2f}  "
          f"RMSE {baseline['rmse']:.2f}  median {baseline['median_abs_err']:.2f}")
    print(f"Baseline (POS/CHROM avg, no model): MAE {baseline_mean['mae']:.2f}  "
          f"RMSE {baseline_mean['rmse']:.2f}  median {baseline_mean['median_abs_err']:.2f}")
    print("\nLOOCV (out-of-fold) MAE by model:")
    for name, m in sorted(loocv.items(), key=lambda kv: kv[1]["mae"]):
        flag = "  <- best" if name == best_name else ""
        print(f"  {name:22s}  MAE {m['mae']:6.2f}  RMSE {m['rmse']:6.2f}{flag}")
    imp = report["improvement_mae"]
    print(f"\nBest model: {best_name}")
    print(f"Improvement: {imp['baseline']:.2f} -> {imp['calibrated_loocv']:.2f} BPM "
          f"({imp['delta']:+.2f}, {imp['pct']:+.1f}%)")
    if coefs:
        print(f"Coefficients: {coefs}")
    print(f"\n70/30 split test MAE ({best_name}): "
          f"{split[best_name]['test']['mae']:.2f} "
          f"(train {split[best_name]['train']['mae']:.2f})")
    print(f"\nWrote: {OUT_CSV.relative_to(REPO)}")
    print(f"Wrote: {OUT_JSON.relative_to(REPO)}")


if __name__ == "__main__":
    main()
