# UBFC-rPPG dataset access — request email

**Status:** ⏳ Not sent yet. Try the public Drive link first; only send this if it gates access.

**Public Drive link to try first** (open in `gbdeveloper21@gmail.com`):
<https://drive.google.com/drive/folders/1o0XU4gTIo46YfwaWjIgbtCncc-oF44Xk?usp=sharing>

If it loads, download what you need and you're done. If it shows "Request access" or returns 403, send the email below.

---

## Email draft

**To:**
- yannick.benezeth@u-bourgogne.fr
- richard.macwan@u-bourgogne.fr
- serge.bobbia@u-bourgogne.fr

**Subject:** UBFC-rPPG dataset access request — Westcliff University AIT 500 academic project

---

Dear Dr. Benezeth, Dr. Macwan, and Dr. Bobbia,

I am a graduate student at Westcliff University enrolled in AIT 500 (Applied AI). My team is implementing the POS rPPG algorithm and benchmarking heart-rate accuracy as our course project, and we would like to evaluate against the UBFC-rPPG dataset alongside SCAMPS for a more robust comparison.

Could you confirm access to the dataset (the Google Drive folder linked from your project page) and any usage requirements beyond citing your 2017 *Pattern Recognition Letters* paper? We will of course cite the work in our final writeup.

Thank you for making this dataset available to the research community.

Best regards,
Germaine Beazer
AIT 500 — Westcliff University
gbdeveloper21@gmail.com

---

## After you receive access

1. Download the dataset to `~/05_Projects/vitalscan/data/ubfc/`
2. Each subject is a folder containing `vid.avi` + `ground_truth.txt`
3. Extend `backend/rppg/evaluation.py::load_scamps_videos` to also handle the UBFC layout (or add a new `load_ubfc_videos` function), then:

```bash
python -m rppg.evaluation --dataset ~/05_Projects/vitalscan/data/ubfc
```

## Citation (for your writeup)

> Bobbia, S., Macwan, R., Benezeth, Y., Mansouri, A., & Dubois, J. (2019).
> Unsupervised skin tissue segmentation for remote photoplethysmography.
> *Pattern Recognition Letters*, 124, 82–90.
