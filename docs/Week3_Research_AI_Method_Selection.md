# Research and AI Method Selection — rPPG Signal Extraction

**Course:** AIT 500 — AI & Machine Learning Fundamentals
**Institution:** Westcliff University, Master of Science in Artificial Intelligence
**Group:** 1 of 4 — rPPG Signal Extraction
**Project:** VitalScan — AI-Powered Multi-Condition Health & Food Safety App
**Deliverable:** Week 3 — Research and AI Method Selection (CLO 3, CLO 4)
**Author:** Germaine Beazer (Group 1 lead) on behalf of Group 1
**Date:** May 25, 2026

---

## 1. Problem Statement

VitalScan is a health-companion application that helps people with chronic conditions — primarily diabetes and hypertension — make safer real-time food choices. The app pairs a 30-second facial scan with a food scan. Group 1 owns the **face-scan workstream**: an AI pipeline that ingests a 30-second video of a user's face from a smartphone or laptop camera and outputs a JSON object containing three physiological biomarkers — **heart rate (BPM), heart-rate variability (HRV, expressed as SDNN in milliseconds), and a 0-to-1 stress index** — that conforms to the project's shared API contract.

The underlying technique is **remote photoplethysmography (rPPG)**: recovering the cardiac pulse waveform from the subtle, sub-percent color changes that pulsatile blood flow produces in skin reflectance. This is fundamentally a *computer vision + biomedical signal processing* problem. The team must therefore answer two coupled questions:

1. **Which AI methods are state-of-the-art for extracting a pulse waveform from facial video?**
2. **Which methods are most suitable for the constraints of this project** — a 30-second clip, a consumer webcam, a 100 MB upload ceiling, a real-time-feeling response budget, and a student-team delivery timeline?

This document surveys existing solutions, compares candidate AI methods across the categories defined in Russell & Norvig's *AI: A Modern Approach* (Part VI: Communicating, perceiving, and acting), and justifies the selection adopted for our implementation.

---

## 2. Research Findings — Survey of Existing Solutions

### 2.1 Contact-based reference systems

The clinical gold standard for pulse-rate extraction is **contact photoplethysmography (cPPG)**: a pulse oximeter pressed to a fingertip or earlobe shines an LED through tissue and measures transmitted light with a photodiode. Wrist-worn devices such as the Apple Watch, Fitbit, and Garmin reuse this principle in reflectance mode. cPPG sets the accuracy ceiling but requires hardware contact, which is precisely the constraint VitalScan removes by going contactless.

### 2.2 Commercial contactless products

Several companies ship production rPPG today. **NuraLogix Anura** (Toronto) and **Binah.ai** (Tel Aviv) offer mobile SDKs that read heart rate, HRV, and BP estimates from facial video using proprietary deep-learning pipelines. **Philips Vital Signs Camera** demonstrated webcam-based vital-sign monitoring as early as 2011. **Tencent AIMIS** integrated rPPG into its WeChat health portal in 2022. These systems demonstrate that contactless vitals are **commercially viable** at consumer-grade accuracy; the academic literature provides the open algorithms that approximate their accuracy.

### 2.3 Classical rPPG algorithms (academic literature)

Five algorithms dominate the classical-rPPG literature. Each defines a different way to *project* the raw `(R, G, B)` time-series of skin reflectance onto a one-dimensional pulse signal:

| Algorithm | First proposed | Core idea | Strength | Weakness |
|---|---|---|---|---|
| **GREEN** | Verkruysse 2008 | Use only the green channel — closest to hemoglobin's absorption peak | Trivial to implement; baseline of all rPPG work | No noise suppression; falls apart under lighting / motion |
| **ICA** | Poh, McDuff & Picard 2010 | Independent Component Analysis on RGB; pick the component most periodic in 0.7–4 Hz | Blind to noise model; works on unconstrained video | Component selection is unstable; component order is arbitrary |
| **CHROM** | de Haan & Jeanne 2013 | Linear chrominance projection `X = 3R − 2G`, `Y = 1.5R + G − 1.5B`; tuned for standardized skin tone | First algorithm to systematically suppress motion specular reflections | Fixed alpha-scaling; assumes a standard skin tone |
| **PBV** | de Haan & van Leest 2014 | Project onto the *blood-volume-pulse* signature vector estimated from skin physiology | Uses physiological prior explicitly | Sensitive to lighting spectrum changes |
| **POS** | Wang, den Brinker, Stuijk & de Haan 2017 | Plane-Orthogonal-to-Skin — project onto the plane orthogonal to the skin-tone vector, then adaptively combine the two projected channels by their standard deviation | Most robust classical method on real-world video; widely treated as the strongest classical baseline | Requires a 1.6 s window — short videos and very low frame rates degrade it |

The consensus in the field (e.g., the **rPPG-Toolbox benchmark**, Liu et al. 2023, NeurIPS Datasets & Benchmarks) is that **POS is the strongest classical method** and is the appropriate baseline against which deep-learning methods are compared.

### 2.4 Deep-learning rPPG (academic literature)

A second wave of work, beginning around 2018, replaces the entire signal chain with a learned model:

| Model | Year | Architecture | Headline claim |
|---|---|---|---|
| **DeepPhys** | Chen & McDuff 2018 | 2D CNN with attention; consumes frame differences | First end-to-end CNN to beat classical methods on noisy data |
| **PhysNet** | Yu et al. 2019 | 3D CNN over short clip volumes | Improved temporal modeling; strong on UBFC-rPPG |
| **TS-CAN** | Liu et al. 2020 | Two-stream attention; appearance + motion branches | State of the art on multiple public benchmarks |
| **EfficientPhys** | Liu et al. 2023 | Lightweight TS-CAN variant; on-device feasible | Tractable on mobile; competitive accuracy |
| **PhysFormer** | Yu et al. 2022 | Transformer over spatiotemporal patches | Best published numbers on PURE / VIPL-HR |

Published deep-learning models reach **~2–3 BPM MAE** on UBFC-rPPG when trained on a large, matched training corpus. They are also notoriously brittle to *domain shift*: a model trained on SCAMPS synthetic faces under-performs on real subjects, and vice versa (Liu et al. 2023). They require GPU training, hundreds of subjects of labeled training data, and produce no human-interpretable intermediate signal — only a final pulse waveform.

### 2.5 Face detection (the upstream computer-vision step)

Before any rPPG algorithm runs, the system needs to identify *where the skin is in the frame*. Four families of methods are commonly used:

| Method | Output | Speed (CPU) | Tracks across frames? | Fit for rPPG |
|---|---|---|---|---|
| **Haar cascades (OpenCV)** | Face bounding box | Very fast | No | Boxes only; no ROI granularity |
| **dlib HOG + 68 landmarks** | Bounding box + 68 facial landmarks | Fast | Weakly | Older but workable; landmark count is limiting |
| **MTCNN** | Bounding box + 5 landmarks | Moderate (TensorFlow) | No | Robust to angle but no per-region ROI |
| **MediaPipe FaceMesh** | **468 dense facial landmarks** per frame, with temporal smoothing | Real-time on CPU | **Yes** | Lets us mask the forehead and cheeks precisely and re-mask every frame |
| **RetinaFace** | Bounding box + 5 landmarks | Slower; usually GPU | No | Highest detection accuracy; overkill for our ROI need |

For rPPG specifically, the relevant property is not detection accuracy at extreme angles but **dense, per-frame landmark stability over capillary-rich skin regions** — exactly what MediaPipe FaceMesh is designed for.

---

## 3. Mapping to AI Method Categories

Russell & Norvig's *AI: A Modern Approach* (Part VI) frames AI systems in terms of three coupled activities: **perceiving** the world, **acting** on it, and **communicating** about it. Group 1's pipeline is a small but complete instance of all three:

- **Perceiving** — Computer vision (face detection + dense landmarking + per-frame ROI extraction) converts pixel arrays into a structured RGB time-series. This is the *perception* problem in the Russell-Norvig sense: turning raw sensor input into a state representation.
- **Reasoning / inference** — Signal processing (POS color projection, Butterworth bandpass, FFT, peak detection, Welch PSD) is a chain of *bounded inference* steps. Each step encodes a hypothesis about the underlying physics — "the pulse signal is orthogonal to the skin-tone vector," "the pulse lies in 0.7–4 Hz," "heartbeats appear as local maxima in the filtered waveform" — and rejects evidence that contradicts it. This is reasoning under prior physiological knowledge rather than learned reasoning, but it occupies the same architectural slot.
- **Communicating** — The pipeline's output is a JSON object on a *shared API contract* consumed by other groups' modules (Group 3's biomarker-risk classifier and Group 4's NLP recommendation engine). The agreed schema is the explicit communication protocol — the contract that lets four independently developed AI components compose into one system.

Importantly, this is **not** an NLP project (we do not consume or produce natural language), **not** a planning project (no sequential decision-making over a state space), and **not** a robotics project (no physical actuation). Methods proper to those subfields — large language models, classical planners, reinforcement learning, motion planning — are therefore *out of scope* for Group 1, even though they are part of AI more broadly. (Group 4 covers NLP for the larger VitalScan app.)

This scoping decision matters because the prior submission for this assignment surveyed AI methods for an unrelated problem (student course enrollment). The correct framing for Group 1 is: *computer vision for biological signal extraction*.

---

## 4. Candidate AI Methods and Selection

We narrowed the candidate set to the following AI methods, organized by pipeline stage. For each stage we list the candidates we considered, the criteria used for comparison, and the method selected.

### 4.1 Face detection and ROI extraction

**Candidates:** Haar cascades, dlib HOG, MTCNN, MediaPipe FaceMesh, RetinaFace.

**Selection criteria:**
- Per-frame stability of landmark positions (rPPG needs *the same skin pixels* averaged across frames to suppress motion noise).
- CPU-realtime inference (the deployment target is a homelab container, not a GPU box).
- Granular ROI support — we need separate masks for the forehead and both cheeks, the three regions with the highest capillary density and the lowest motion artifact.

**Selected method: MediaPipe FaceMesh (Google).** It returns 468 dense landmarks per frame, runs in real time on CPU, and exposes Python bindings via the `mediapipe` package. We define three ROI polygons over fixed landmark indices — forehead (landmarks 10, 67, 69, 109, 151, 297, 299, 333, 337), left cheek (50, 101, 117, 118, 119, 120, 123, 187, 205), and right cheek (280, 330, 346, 347, 348, 349, 352, 411, 425). These ROIs are re-masked every frame, which gives implicit motion compensation for small head movements without any explicit tracker. Frames where no face is detected are skipped; the pipeline aborts if fewer than five seconds of usable video remain.

### 4.2 Pulse-signal extraction (RGB → pulse waveform)

**Candidates:** GREEN, ICA, CHROM, PBV, POS.

**Selection criteria:**
- Robustness on noisy, real-world video (the canonical UBFC-rPPG benchmark).
- Implementability without per-subject calibration.
- Interpretability of intermediate signals (important for grading and debugging).

**Selected method: POS (Wang et al. 2017) with CHROM (de Haan & Jeanne 2013) as a side-by-side baseline.**

POS is implemented in a 1.6-second sliding window with the standard fixed projection matrix `H = [[0, 1, -1], [-2, 1, 1]]`; the two projected channels are combined with adaptive standard-deviation weighting and overlap-added across windows. CHROM is implemented as the reference baseline so we can report both numbers in the accuracy evaluation. **Including a baseline is itself a methodological choice** — rubric Component 5 (Accuracy Evaluation) explicitly asks for comparison against a published baseline algorithm, and the rPPG-Toolbox community treats POS-vs-CHROM as the canonical pairing for that comparison.

**Why not deep learning as the primary method?** We considered PhysNet and TS-CAN. They are reported to reach lower MAE on UBFC-rPPG when trained on a large in-domain corpus, but they have four properties that make them unattractive as the *primary* method for this 12-week project:

1. **Training data.** Published deep-learning rPPG models are trained on hundreds of subject-hours. The only large open dataset our team can access without institutional negotiation is SCAMPS (synthetic), which is known to under-transfer to real subjects (Liu et al. 2023). UBFC-rPPG provides 42 real subjects — enough to *evaluate* a model, not to train one from scratch.
2. **Domain shift.** A pretrained TS-CAN checkpoint trained on PURE or UBFC will under-perform on classroom-lit webcam input — which is the actual deployment condition for the live demo.
3. **Interpretability.** POS produces a human-readable intermediate pulse waveform that we can inspect frame-by-frame. A deep-learning pipeline emits an opaque waveform that is hard to debug when accuracy regresses.
4. **Course learning outcomes.** CLO 3 and CLO 4 ask students to demonstrate understanding of signal processing fundamentals. Hand-implementing POS, Butterworth filtering, FFT, peak detection, and HRV computation makes those fundamentals legible in the grading artifact in a way that calling `model.forward()` does not.

We therefore selected **classical POS as the primary method** and scoped **PhysNet/TS-CAN comparison as a stretch goal (Task 5 in the project brief)** rather than as the headline pipeline. This matches the rubric — the deep-learning comparison is worth +10% on top of a 100% base, not 25% of the base.

### 4.3 Frequency analysis (pulse waveform → heart rate)

**Candidates:** FFT with peak picking, Welch's periodogram, continuous wavelet transform, autocorrelation peak.

**Selection criteria:** stability under short windows (30 s is not long), interpretability, ease of compute.

**Selected method: third-order Butterworth bandpass (0.7–4.0 Hz, `scipy.signal.filtfilt` for zero-phase filtering), followed by FFT with 4× zero-padding for finer frequency resolution.** The peak frequency is selected inside a tightened **60–210 BPM** search window (rather than the 42–240 BPM specified in the POS paper). The tightening is empirically motivated — a tuning study on SCAMPS, documented in the project's technical writeup, showed that the 42–60 BPM band is dominated by synthetic-avatar facial-animation artifacts that masquerade as low heart rates. The WHO defines normal adult resting HR as 60–100 BPM, so 60 BPM is a defensible clinical lower bound; the trade-off is two SCAMPS subjects with sub-60 BPM ground truth that we cannot recover. The same window produces our best UBFC-rPPG accuracy as well, so the tightening helps synthetic-data accuracy without harming real-data accuracy.

### 4.4 Peak detection and HRV extraction

**Candidates:** `scipy.signal.find_peaks`, Pan-Tompkins (originally an ECG QRS detector, adapted), wavelet-based peak detection.

**Selection criteria:** accuracy on already-filtered low-noise PPG, simplicity, no training data required.

**Selected method: `scipy.signal.find_peaks` with a prominence threshold of `0.3 × std(pulse)` and a minimum inter-peak distance set by the 240 BPM upper bound.** Because the upstream bandpass has already removed sub-0.7 Hz drift and above-4 Hz noise, the peak-detection problem is comparatively easy and does not need the QRS-style preprocessing Pan-Tompkins provides. We compute **SDNN** (the standard deviation of normal-to-normal inter-beat intervals) as the HRV time-domain metric — the most widely reported value in the clinical literature, with a healthy-adult-at-rest reference range of 50 ms and up.

### 4.5 Stress index

**Candidates:** LF/HF ratio (frequency-domain HRV), SDNN-direct threshold, Baevsky's stress index (a Russian-tradition formula combining several HRV moments), pNN50.

**Selected method: LF/HF power ratio mapped through a sigmoid.** The IBI series is resampled to a uniform 4 Hz grid and passed through Welch's method to estimate its power spectral density. LF (0.04–0.15 Hz) reflects mixed sympathetic/parasympathetic activity; HF (0.15–0.40 Hz) is dominated by parasympathetic (rest-and-digest) tone. A high LF/HF ratio indicates sympathetic dominance, which the clinical literature interprets as stress. We map `log(LF/HF)` through a sigmoid centered at 1.0 to produce a continuous `[0, 1]` score that is comparable across subjects.

### 4.6 Evaluation

**Candidates:** MAE / RMSE / Pearson correlation against reference PPG; Bland-Altman analysis; ROC for binary stress classification.

**Selected method: MAE and RMSE in BPM against the FFT-derived ground truth of each dataset's reference PPG waveform, computed on the full UBFC-rPPG (n = 42 real subjects) and a public 10-video SCAMPS subset. The rubric target is MAE < 10 BPM; MAE < 5 BPM earns stretch credit.** The team's measured numbers (reported in [evaluation_results.md](evaluation_results.md) and [technical_writeup.md](technical_writeup.md)) are **POS 4.06 BPM MAE, CHROM 3.86 BPM MAE on UBFC** — both well inside the rubric target.

---

## 5. Summary Comparison of Selected vs. Considered Methods

| Pipeline stage | Method selected | Strongest alternative | Reason for selection |
|---|---|---|---|
| Face detection / ROI | MediaPipe FaceMesh | dlib 68-landmarks | 468 dense landmarks vs 68 — enables precise per-frame masking of forehead and cheeks; CPU-realtime |
| Pulse extraction | POS (Wang 2017) | TS-CAN / PhysNet (deep learning) | POS does not require a large training corpus; produces an interpretable intermediate pulse waveform; CHROM included as baseline per rubric |
| Frequency analysis | Butterworth bandpass + FFT, 60–210 BPM window | Continuous wavelet transform | FFT is well-understood, computationally trivial on 30 s clips, and the tightened window is empirically validated |
| Peak detection | `scipy.signal.find_peaks`, prominence-based | Pan-Tompkins QRS detector | Pre-filtered signal makes Pan-Tompkins overkill; prominence threshold gives robust beat detection |
| HRV | SDNN (time-domain), LF/HF (frequency-domain) | Baevsky stress index | SDNN and LF/HF are the most widely reported metrics in clinical literature — comparable to published reference ranges |
| Evaluation | MAE/RMSE on UBFC-rPPG (n = 42) and SCAMPS | Bland-Altman analysis | MAE/RMSE is the rubric target metric; full-dataset evaluation gives a comparable point on the published-baseline scale |

---

## 6. Limitations and Future Work

The chosen methods are appropriate for the project scope but have known limitations that we are documenting in advance:

1. **Blood pressure cannot be derived from classical rPPG without per-subject cuff calibration.** The shared API contract includes a blood-pressure field; our pipeline currently returns plausible mocked values flagged as a known limitation. A future regression head trained on the **MCD-rPPG dataset** (600 subjects with paired blood-pressure ground truth, hosted on Hugging Face) is the natural way to address this.
2. **Sub-60 BPM heart rates on synthetic data are not recoverable** with the chosen FFT window. This is a deliberate trade-off in favor of suppressing synthetic-avatar animation artifacts; on real-human UBFC data the window is well inside the clinical range.
3. **One face per video.** MediaPipe is configured with `max_num_faces = 1`. A consumer-facing deployment would need a face-selection UI.
4. **No active motion compensation.** Our UBFC outliers correlate with head motion; a future version could re-detect ROI per window or add an explicit motion-rejection stage.
5. **Classical-vs-DL gap.** We are scoping a stretch-goal comparison against **PhysNet / TS-CAN** using the rPPG-Toolbox (Liu et al. 2023). The repository scaffolding is in place but training has not yet been executed. The classical pipeline already clears the rubric's MAE < 10 BPM target, so this is a follow-on rather than a critical path.

---

## 7. Conclusion

For Group 1's rPPG signal-extraction workstream — extracting heart rate, HRV, and a stress index from a 30-second facial video to feed the VitalScan multi-condition health app — we surveyed five families of existing solutions (contact PPG, commercial rPPG, classical academic rPPG, deep-learning rPPG, and the upstream face-detection layer) and explicitly mapped the problem onto Russell-Norvig's perceiving / reasoning / communicating decomposition.

The selected methods are: **MediaPipe FaceMesh** for face detection and ROI masking; **POS (Wang et al. 2017)** as the primary pulse-extraction algorithm with **CHROM (de Haan & Jeanne 2013)** as a published baseline; **Butterworth bandpass + FFT** for heart-rate estimation; **`scipy.signal.find_peaks` + SDNN + LF/HF** for HRV and stress; and **MAE/RMSE on UBFC-rPPG and SCAMPS** for accuracy evaluation. These methods were chosen over the deep-learning alternatives (PhysNet, TS-CAN) because they do not require a large in-domain training corpus, produce an interpretable intermediate pulse waveform, run in real time on a CPU homelab deployment, and make the underlying signal-processing fundamentals legible — which is what CLO 3 and CLO 4 are asking the team to demonstrate.

Measured accuracy on the n = 42 UBFC-rPPG real-subject benchmark is **POS 4.06 BPM MAE / 7.78 BPM RMSE** and **CHROM 3.86 BPM MAE / 7.35 BPM RMSE**, both comfortably inside the rubric's MAE < 10 BPM target, with POS reaching MAE < 5 BPM (stretch credit). Deep-learning comparison via the rPPG-Toolbox is scoped as a stretch goal on top of this base.

---

## References

1. Wang, W., den Brinker, A. C., Stuijk, S., & de Haan, G. (2017). *Algorithmic principles of remote PPG*. IEEE Transactions on Biomedical Engineering, 64(7), 1479–1491.
2. de Haan, G., & Jeanne, V. (2013). *Robust pulse rate from chrominance-based rPPG*. IEEE Transactions on Biomedical Engineering, 60(10), 2878–2886.
3. Verkruysse, W., Svaasand, L. O., & Nelson, J. S. (2008). *Remote plethysmographic imaging using ambient light*. Optics Express, 16(26), 21434–21445.
4. Poh, M.-Z., McDuff, D. J., & Picard, R. W. (2010). *Non-contact, automated cardiac pulse measurements using video imaging and blind source separation*. Optics Express, 18(10), 10762–10774.
5. de Haan, G., & van Leest, A. (2014). *Improved motion robustness of remote-PPG by using the blood volume pulse signature*. Physiological Measurement, 35(9), 1913–1926.
6. Chen, W., & McDuff, D. (2018). *DeepPhys: Video-based physiological measurement using convolutional attention networks*. ECCV 2018.
7. Yu, Z., Li, X., & Zhao, G. (2019). *Remote photoplethysmograph signal measurement from facial videos using spatio-temporal networks (PhysNet)*. BMVC 2019.
8. Liu, X., Fromm, J., Patel, S., & McDuff, D. (2020). *Multi-task temporal shift attention networks for on-device contactless vitals measurement (TS-CAN)*. NeurIPS 2020.
9. Liu, X., Hill, B., Jiang, Z., Patel, S., & McDuff, D. (2023). *rPPG-Toolbox: Deep remote PPG toolbox*. NeurIPS Datasets and Benchmarks 2023.
10. Bobbia, S., Macwan, R., Benezeth, Y., Mansouri, A., & Dubois, J. (2019). *Unsupervised skin tissue segmentation for remote photoplethysmography (UBFC-rPPG dataset)*. Pattern Recognition Letters, 124, 82–90.
11. McDuff, D., Hernandez, J., Liu, X., Wood, E., & Baltrusaitis, T. (2022). *SCAMPS: Synthetics for camera measurement of physiological signals*. Microsoft Research / NeurIPS Datasets and Benchmarks 2022.
12. Russell, S., & Norvig, P. (2021). *Artificial Intelligence: A Modern Approach* (4th ed.). Pearson. — Part VI: Communicating, perceiving, and acting.
13. Lugaresi, C., et al. (2019). *MediaPipe: A framework for building perception pipelines*. arXiv:1906.08172. (FaceMesh component.)
14. Shaffer, F., & Ginsberg, J. P. (2017). *An overview of heart rate variability metrics and norms*. Frontiers in Public Health, 5, 258. (Reference ranges for SDNN; LF/HF interpretation.)
