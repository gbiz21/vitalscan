"""
Task 1 — Face Detection and ROI Extraction
==========================================

Uses MediaPipe FaceMesh to detect facial landmarks per frame, then extracts
the regions of interest (ROI) — forehead and both cheeks — which produce the
strongest rPPG signal because they have:
  - High capillary density (good signal source)
  - Relatively flat surface (less specular reflection noise)
  - Stable position relative to other features (tracking robustness)

Output is a time-series of mean RGB values per frame, which feeds into the
POS algorithm in Task 2.

Educational note: skin reflects about 90% of incoming light; the heartbeat
signal we want is in the remaining 10% absorption variation. So we are
measuring a tiny fluctuation on top of a much larger constant.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple

import cv2
import mediapipe as mp
import numpy as np

# MediaPipe FaceMesh landmark indices for forehead and cheek regions.
# These are the standard indices documented in the MediaPipe Face Mesh model.
FOREHEAD_LANDMARKS = [10, 67, 69, 109, 151, 337, 297, 299, 333]
LEFT_CHEEK_LANDMARKS = [50, 101, 117, 118, 119, 120, 123, 187, 205]
RIGHT_CHEEK_LANDMARKS = [280, 330, 346, 347, 348, 349, 352, 411, 425]


@dataclass
class ROIFrameData:
    """Per-frame extracted RGB means for each ROI."""
    forehead_rgb: Tuple[float, float, float]
    left_cheek_rgb: Tuple[float, float, float]
    right_cheek_rgb: Tuple[float, float, float]
    face_detected: bool


def extract_roi_polygon(
    frame: np.ndarray,
    landmarks,
    landmark_indices: List[int],
) -> Optional[np.ndarray]:
    """Extract the masked ROI region from a frame using polygon landmarks."""
    h, w = frame.shape[:2]
    points = np.array(
        [
            [int(landmarks[idx].x * w), int(landmarks[idx].y * h)]
            for idx in landmark_indices
        ],
        dtype=np.int32,
    )

    # Build a binary mask of the polygon, then average pixels inside it
    mask = np.zeros((h, w), dtype=np.uint8)
    cv2.fillPoly(mask, [points], 255)

    if mask.sum() == 0:
        return None

    return cv2.mean(frame, mask=mask)[:3]  # (B, G, R) means


class FaceROIExtractor:
    """
    Wraps MediaPipe FaceMesh to produce a per-frame ROI RGB time-series.

    Usage:
        extractor = FaceROIExtractor()
        rgb_series = extractor.process_video("path/to/video.mp4")
        # rgb_series shape: (n_frames, 3) — mean R, G, B over combined ROI
    """

    def __init__(self, refine_landmarks: bool = False):
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=refine_landmarks,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

    def process_frame(self, frame_bgr: np.ndarray) -> ROIFrameData:
        """Extract ROI RGB means from a single BGR frame."""
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(frame_rgb)

        if not results.multi_face_landmarks:
            return ROIFrameData(
                forehead_rgb=(0.0, 0.0, 0.0),
                left_cheek_rgb=(0.0, 0.0, 0.0),
                right_cheek_rgb=(0.0, 0.0, 0.0),
                face_detected=False,
            )

        landmarks = results.multi_face_landmarks[0].landmark

        forehead = extract_roi_polygon(frame_rgb, landmarks, FOREHEAD_LANDMARKS)
        left = extract_roi_polygon(frame_rgb, landmarks, LEFT_CHEEK_LANDMARKS)
        right = extract_roi_polygon(frame_rgb, landmarks, RIGHT_CHEEK_LANDMARKS)

        return ROIFrameData(
            forehead_rgb=forehead or (0.0, 0.0, 0.0),
            left_cheek_rgb=left or (0.0, 0.0, 0.0),
            right_cheek_rgb=right or (0.0, 0.0, 0.0),
            face_detected=True,
        )

    def process_video(self, video_path: str) -> Tuple[np.ndarray, float]:
        """
        Run extraction on a full video file.

        Returns:
            rgb_series: shape (n_frames, 3), the combined ROI mean RGB per frame
            fps: video frame rate (needed by the POS algorithm)
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise IOError(f"Cannot open video: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        rgb_per_frame: List[np.ndarray] = []

        while True:
            ok, frame = cap.read()
            if not ok:
                break

            roi = self.process_frame(frame)
            if roi.face_detected:
                # Combine three ROIs by simple averaging — gives a stronger
                # signal than any single region alone
                combined = np.mean(
                    [roi.forehead_rgb, roi.left_cheek_rgb, roi.right_cheek_rgb],
                    axis=0,
                )
                rgb_per_frame.append(combined)

        cap.release()

        if len(rgb_per_frame) < int(fps * 5):
            raise ValueError(
                f"Only {len(rgb_per_frame)} frames had a detected face — "
                f"need at least 5 seconds of usable video."
            )

        return np.array(rgb_per_frame), fps

    def close(self):
        self.face_mesh.close()
