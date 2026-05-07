# UBFC-rPPG dataset — notes

**Status:** ✅ Obtained via the public Google Drive link below — the email
request was never needed. Full 42-subject dataset evaluated on 2026-05-06,
producing MAE 4.10 BPM (see `evaluation_results.md`).

This file used to hold the access-request email draft. It now serves as
the reference page: where the data lives, how the loader expects it, and
how to cite it in the writeup.

## Source

Public Google Drive folder (Dataset 2, 42 real-human subjects):
<https://drive.google.com/drive/folders/1o0XU4gTIo46YfwaWjIgbtCncc-oF44Xk?usp=sharing>

Worked from `gbdeveloper21@gmail.com` — no access request required.

## Local layout (Mac)

```
~/05_Projects/vitalscan/data/
├── ubfc_full/        75 GB  — full 42-subject set, used for the headline 4.10 BPM result
└── ubfc/             8.2 GB — earlier subset (smaller subject count)
```

`data/` is gitignored, so neither directory ships in the repo.

## Per-subject directory layout

Each subject is a folder named `subject*` containing:

```
subject<NN>/
├── vid.avi              webcam recording (~1 minute, 30 fps, 640x480)
└── ground_truth.txt     three rows: PPG signal, HR over time, timestamps
```

`ground_truth.txt` format from the UBFC readme:
- Row 1: PPG amplitude waveform
- Row 2: instantaneous heart rate (BPM)
- Row 3: timestamps (seconds)

## Loader

`backend/rppg/evaluation.py::load_ubfc_videos` reads this layout:

- Auto-detected when the dataset root contains any `subject*/vid.avi`
- Computes ground-truth BPM by FFT'ing the PPG waveform (Row 1) at 30 Hz
- Pairs each subject with the matching `vid.avi` for the pipeline run

## Reproduce the headline number

```bash
cd ~/05_Projects/vitalscan/backend
source venv312/bin/activate
python -m rppg.evaluation \
  --dataset ~/05_Projects/vitalscan/data/ubfc_full \
  --output ~/05_Projects/vitalscan/data/eval_ubfc_full.csv
```

Expected: MAE 4.10 BPM, RMSE 7.83 BPM, median |error| 1.05 BPM, 38/42 within ±10 BPM.

## Citation (for the writeup)

> Bobbia, S., Macwan, R., Benezeth, Y., Mansouri, A., & Dubois, J. (2019).
> Unsupervised skin tissue segmentation for remote photoplethysmography.
> *Pattern Recognition Letters*, 124, 82–90.
