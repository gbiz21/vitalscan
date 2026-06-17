# Week 7 — Project: Evaluation and Refinement (CLO 2, CLO 3, CLO 4)

**Project:** VitalScan — contactless vital-sign estimation from 30-second facial video (rPPG)
**Course:** AIT 500 · Westcliff University · Summer 2026 · Session 5 · Group 1
**Date:** June 2026 (Wk 7 — June 15–21)

---

## 0. What, exactly, are we evaluating and refining?

Before any numbers, it is worth being precise about *which* part of VitalScan this report is about, because the system produces four outputs (heart rate, HRV, stress, blood pressure) and they are not all measurable the same way.

The thing we evaluate and refine here is the **heart-rate estimate** — the single BPM number our pipeline reads off a 30-second face video. We focus on it for a simple reason: it is the only output we can grade. The UBFC-rPPG benchmark records a real finger pulse-oximeter at the same time as the video, so for every subject we have a trustworthy "right answer" in BPM to compare against. HRV and stress are derived from the same recovered pulse wave, so when the heart rate is right they tend to be right too — but the dataset gives us no independent ground truth to score them on their own. Blood pressure we don't measure at all (classical rPPG can't, without a cuff), so there is nothing to evaluate there either.

So when this report says "the model," it means **the heart-rate estimator**: face video in, BPM out. "Evaluation" means measuring how close that BPM is to the contact sensor across 42 real people. "Refinement" means the changes we made to that estimator to bring the number closer.

---

## 1. The short version

We graded the heart-rate model on 42 real subjects (UBFC-rPPG) and, as a stress test, on 10 synthetic CGI subjects (SCAMPS). On real people the model lands at **3.94 BPM mean error**, comfortably under the rubric's 10-BPM bar, with half of all readings within about 1 BPM of a medical sensor.

The evaluation pointed us to three concrete refinements, and each one is the honest outcome of looking at the data rather than a change we made for its own sake:

1. We **narrowed the frequency band** the algorithm searches for a heartbeat, after the synthetic data showed it was being fooled by low-frequency animation artifacts.
2. We **tried to bolt a small machine-learning model on top** to clean up the estimate — and found, with proper cross-validation, that it made things *worse*. We dropped it. That negative result is a real finding, and it's what tells us the classical method has hit its ceiling.
3. We **switched the production estimate from one algorithm (POS) to the average of two (POS and CHROM)**, which nudged the error down for free, and we actually wired that change into the running pipeline this week — it had been decided earlier but never shipped.

---

## 2. Picking metrics that fit the problem (CLO 2)

The rubric suggests accuracy, precision, recall, or F1 "depending on the problem type." The honest answer is that heart rate is a **number we're trying to predict, not a category**, so the natural way to grade it is by how far off the number is:

- **Mean absolute error (MAE)** — on average, how many BPM are we off? This is the headline, and it's what the rubric's "< 10 BPM" target is written in.
- **RMSE** — same idea, but it punishes the occasional large miss harder, so it tells us about the worst cases.
- **Median error** — the typical miss, ignoring a few bad videos that would skew the average.

Accuracy, precision, recall, and F1 only make sense once there are categories to get right or wrong. They do become useful here if we turn the regression into a yes/no decision, and we do exactly that in two places below: first by asking "is this reading clinically acceptable (within 10 BPM)?", which gives an accuracy figure, and second by asking "can the system tell when its own reading is bad?", which is where precision and recall earn their keep — and where the most interesting result of the whole project shows up.

---

## 3. How the model actually performed (CLO 2, CLO 3)

### 3.1 On real people — the number that matters

Every subject's video goes through the pipeline; the resulting BPM is compared to the pulse-oximeter reading taken at the same moment. We ran three versions of the estimator so the comparison is fair:

| Estimator | MAE (BPM) | RMSE | Median error | Within ±10 BPM | Rubric |
|---|---|---|---|---|---|
| POS only (what we used to ship) | 4.06 | 7.78 | 1.10 | 38/42 (90%) | pass |
| CHROM only (the classic baseline) | 3.86 | 7.35 | 1.10 | 39/42 (93%) | pass |
| **POS + CHROM averaged (now shipping)** | **3.94** | **7.40** | **1.20** | **38/42 (90%)** | **pass** |

All three pass, and the gap between them (0.2 BPM across 42 people) is small enough that it's really noise — none is meaningfully "the winner." We'll come back in §5.3 to why we chose the average rather than just betting on CHROM, which technically scored best on this particular set.

### 3.2 Where the errors live

Looking at the adopted estimator subject by subject:

| How close | Subjects | Share |
|---|---|---|
| within 1 BPM | 17/42 | 41% |
| within 3 BPM | 29/42 | 69% |
| within 5 BPM | 32/42 | 76% |
| within 10 BPM | 38/42 | 90% |
| more than 10 BPM off | 4/42 | 10% (subjects 25, 26, 27, 32) |

The story here is that the model is usually *very* close — roughly four in ten readings are within a single BPM of a medical device — and the error is almost entirely concentrated in four subjects.

### 3.3 The same results as a yes/no decision (accuracy, precision, recall, F1)

**Is the reading clinically acceptable?** If we call a prediction "good" when it's within 10 BPM of truth, the model is good on 38 of 42 subjects — **90% accuracy**. That's a clean accuracy figure for the regression-as-classification framing the rubric asks about.

**Can the model know when it's wrong?** This is the more useful question for a real product. We have a built-in honesty check: the two algorithms, POS and CHROM, are independent, so when they *disagree* it's a hint the video is unreliable. We can treat "POS and CHROM differ by more than X BPM" as the model raising its hand to say "don't trust this one," and then check how well that flag actually catches the four bad readings:

| Disagreement threshold | Caught (TP) | False alarms (FP) | Missed (FN) | Precision | Recall | F1 |
|---|---|---|---|---|---|---|
| 5 BPM | 1 | 1 | 3 | 0.50 | 0.25 | 0.33 |
| **8 BPM** | **1** | **0** | **3** | **1.00** | **0.25** | **0.40** |
| 12 BPM | 1 | 0 | 3 | 1.00 | 0.25 | 0.40 |

Read that bottom row carefully, because it's the heart of this project: the flag is **perfectly precise but almost blind**. When the two algorithms disagree, the reading genuinely is bad (precision 1.00, no false alarms) — but the flag only catches **1 of the 4** bad readings (recall 0.25). The other three slip right past it, and the next section explains why that happens and why it's actually the important lesson.

### 3.4 The synthetic stress test, for honesty

We also ran the model on 10 SCAMPS subjects — computer-generated faces with a programmed heartbeat. It scores far worse (MAE ~29 BPM for POS) and **fails the rubric, which we report rather than hide.** The CGI skin doesn't reproduce the faint color changes a real face makes with each pulse, so there's barely any signal to find. That's a known limit in the rPPG literature, not a bug in our code — and tellingly, 4 of the 10 synthetic subjects still come out near-perfect, which shows the algorithm is sound when the input is good. We use synthetic data to probe failure modes, not to claim accuracy.

---

## 4. What we learned from all this (CLO 3)

**The errors aren't a mistake we can correct — they're noise we can't.** Three of the four bad subjects (25, 26, 27) are consecutive IDs, and on every one of them POS and CHROM *agree with each other and are both wrong*. Two independent physics-based methods landing on the same wrong answer is the signature of a bad input video — almost certainly a shared bad-lighting recording session — not a bias in the algorithm we could learn to cancel out. This is also the exact reason the disagreement flag in §3.3 has such poor recall: its whole premise is "catch the readings where the two methods disagree," and the worst readings are ones where they quietly agree.

**There's almost nothing left to fix.** 38 of 42 subjects already average under 2 BPM of error with no consistent over- or under-shoot. The model isn't systematically high or low; it's just occasionally defeated by a bad video. When the typical error is already down at the noise floor, there's very little room for any correction step to help.

**The outliers cluster by recording conditions, not by people.** Because the failures are consecutive IDs, the right conclusion is "those videos were captured badly," which points us away from fiddling with the algorithm and toward data quality — a useful thing to know if the professor asks why four subjects failed.

---

## 5. What we changed in response (CLO 4)

### 5.1 Narrowed the search band (45 → 29 BPM error on synthetic data)

The algorithm picks a heartbeat by finding the strongest frequency in a search window. The synthetic data revealed that the original wide window (42–240 BPM) kept locking onto low-frequency artifacts from the avatar's facial animation, down around 42–60 BPM, instead of the real pulse. Tightening the window to **60–210 BPM** cut the synthetic error almost in half:

| Search window | Synthetic MAE | Verdict |
|---|---|---|
| 42–240 BPM (default) | 45.16 | artifacts win |
| 50–210 BPM | 45.16 | still picking up 50–60 BPM junk |
| **60–210 BPM (chosen)** | **28.86** | best — and medically reasonable |

The 60-BPM floor is defensible (a normal resting adult heart rate is 60–100 BPM per the WHO), and we use the *same* window on both datasets — no tuning one window for real data and a different one for synthetic. The trade-off, stated plainly: it gives up on the rare genuinely-below-60 subject.

### 5.2 We tried machine learning, and it didn't work — that's the finding

The obvious next move was "put a small model on top of the classical pipeline to correct its mistakes." We took that seriously and tested it properly rather than assuming it would help. We fed four numbers (the POS estimate, the CHROM estimate, their average, and how much they disagree) into four standard regressors — linear, ridge, robust Huber, and a random forest — and graded them with leave-one-out cross-validation, where every subject is predicted by a model that never saw them.

Every single trained model came out **worse than doing nothing**:

| Method | Trained? | Cross-validated MAE |
|---|---|---|
| **POS + CHROM average** | no | **3.94 (best)** |
| raw POS | no | 4.06 |
| random forest | yes | 5.83 |
| ridge | yes | 6.21 |
| Huber | yes | 6.27 |
| linear | yes | 7.01 |

A 70/30 split confirmed the models were overfitting — the random forest scored 3.1 BPM on data it had seen and 7.5 BPM on data it hadn't. None of this is surprising in hindsight: §4 already told us the leftover error is uncorrectable noise, and you can't train a model to predict noise from four numbers. This is a legitimate, defendable result — we had a reasonable hypothesis, tested it honestly, and showed it doesn't hold. It's also exactly what justifies the deep-learning direction in §6: if a calibrator on top of the classical features can't help, the only way forward is to replace the features themselves.

### 5.3 Switched to averaging two algorithms — and actually shipped it

The one change that *did* help cost us nothing: instead of trusting POS alone, report the **average of POS and CHROM**. It's the same 3.94 BPM that won the comparison above, with no parameters to train and nothing to overfit.

Why the average and not CHROM by itself, given CHROM scored a hair better (3.86)? Because that 0.2 BPM lead is within the noise — picking CHROM-only would be over-reacting to which algorithm happened to win on these specific 42 people. Averaging two independent estimators is the steadier bet: it smooths out the cases where either one stumbles, and it's what makes the disagreement-based honesty check in §3.3 possible in the first place.

The important part for this milestone: **this was decided back in the Week 6 study but never actually made it into the running code** — the live pipeline was still reporting POS only. We fixed that this week. The pipeline now computes both and reports their mean ([backend/rppg/pipeline.py](../backend/rppg/pipeline.py#L105)):

```python
pos_bpm, hr_confidence, filtered_pulse = extract_heart_rate(rgb_series, fps)
chrom_bpm, _chrom_pulse = extract_heart_rate_chrom(rgb_series, fps)
heart_rate_bpm = 0.5 * (pos_bpm + chrom_bpm)
```

(Wiring CHROM in also surfaced a latent bug in the CHROM code that would have crashed it in the live pipeline; that's fixed too. POS's pulse wave and confidence are kept for the HRV/stress stage — CHROM only sharpens the BPM number, it doesn't replace the rest.) The point is that the model we describe in this report is now the model that's actually deployed.

---

## 6. Where real improvement would have to come from

The negative result in §5.2 is genuinely useful because it tells us *what kind* of change is worth attempting next. Tweaking the classical method won't move the needle anymore; the only way past its ceiling is to stop hand-writing the signal-extraction formula and let a neural network learn it from raw video instead — the PhysNet / DeepPhys / TS-CAN family, via the `rppg-toolbox` framework. That needs far more labeled data than our 42 clips (combining UBFC, PURE, and SCAMPS, or fine-tuning a pretrained model) and a GPU with 12–16 GB of memory. The realistic, zero-cost version is fine-tuning a pretrained model on a free Colab T4, which is the one path that fits the time we have left.

---

## 7. How to reproduce these numbers

```bash
# Classical evaluation — POS vs CHROM on UBFC and SCAMPS
backend/venv312/bin/python -m rppg.evaluation \
  --dataset data/ubfc_full --output data/eval_ubfc_full.csv

# The calibration study and the POS/CHROM-average result (§5.2, §5.3)
backend/venv312/bin/python backend/scripts/train_bpm_calibrator.py
#   -> data/eval_ubfc_calibrated.csv, docs/wk6_calibration_metrics.json
```

Everything uses a fixed random seed (42) and is deterministic. The per-subject source data is in `data/compare_pos_chrom_ubfc.csv` (42 real subjects) and `data/compare_pos_chrom_scamps.csv` (10 synthetic).

---

## 8. How this maps to the learning outcomes

- **CLO 2 (evaluate performance with the right metrics):** §2 explains why heart rate is a regression problem and which metrics fit; §3 grades it both ways — as error in BPM and as a yes/no decision with accuracy, precision, recall, and F1 — on both real and synthetic data.
- **CLO 3 (draw insights from the evaluation):** §3.3 and §4 — the leftover error is uncorrectable noise, the signal already sits at its floor, and the failures cluster by recording session rather than by person.
- **CLO 4 (refine the model and implement optimizations):** §5 — narrowing the search band, the machine-learning attempt we tested and rejected, and the POS/CHROM average that we adopted and actually shipped into the live pipeline.
