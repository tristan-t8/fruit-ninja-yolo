"""
Hand Detector Module
Uses MediaPipe Hands for real-time, high-precision fingertip detection.

Drop-in replacement for the previous YOLO-based HandDetector. The class name,
method signatures, and returned dict shape are unchanged, so app.py and
fruit_slicer.py do not need to change.

Why MediaPipe instead of YOLO here:
  * The old code used `yolov8n-pose.pt`, which is the COCO human-body pose
    model. It detects "person" and outputs 17 body keypoints — no fingers,
    no fingertip. That's the real reason detection felt bad.
  * MediaPipe Hands gives 21 hand landmarks per hand, including the
    index fingertip (landmark 8), runs at 30+ FPS on CPU, and needs no
    custom training or model download.
  * The `device` argument is kept for API compatibility but is ignored —
    MediaPipe does not run on PyTorch/CUDA. Detection is fast enough on
    CPU that this is not a problem for Fruit Ninja gameplay.

Output shape (per detection), matching the previous version:
    {
        'bbox':       [x1, y1, x2, y2],   # tight box around the 21 landmarks
        'confidence': float,              # detection score 0..1
        'class_id':   0 or 1,             # 0 = Right hand, 1 = Left hand
        'class_name': 'Right' | 'Left',
        'center':     [x, y],             # SMOOTHED index fingertip (landmark 8)
        'width':      int,
        'height':     int,
        'keypoints':  [[x, y], ... 21]    # all landmarks in pixel coords
    }
"""

import cv2
import numpy as np
import logging
from typing import List, Dict, Tuple, Optional

try:
    import torch  # only used so the `device` arg from app.py still type-checks
except Exception:
    torch = None

import mediapipe as mp

logger = logging.getLogger(__name__)


# MediaPipe Hands landmark indices (0-20).
# Reference: https://developers.google.com/mediapipe/solutions/vision/hand_landmarker
WRIST = 0
THUMB_TIP = 4
INDEX_TIP = 8
MIDDLE_TIP = 12
RING_TIP = 16
PINKY_TIP = 20

# The landmark reported as the hand "center" for slicing.
# Index fingertip feels the most natural for a Fruit Ninja-style game.
SLICE_POINT = INDEX_TIP


class HandDetector:
    """Hand detection using MediaPipe Hands."""

    def __init__(
        self,
        model_path: str = None,
        confidence_threshold: float = 0.6,
        device=None,
        img_size: int = 640,
        max_num_hands: int = 2,
        tracking_confidence: float = 0.5,
        model_complexity: int = 1,
        smoothing_alpha: float = 0.5,
    ):
        """
        Args:
            model_path: Ignored. Kept for API compatibility with the YOLO version.
            confidence_threshold: Minimum detection confidence (MediaPipe's
                min_detection_confidence). 0.6 is a good default for a game —
                lower means more false positives, higher means lost tracks.
            device: Ignored. MediaPipe runs on CPU.
            img_size: Ignored. Kept for API compatibility.
            max_num_hands: How many hands to track. 1 is faster, 2 lets the
                player use both hands.
            tracking_confidence: min_tracking_confidence. Once a hand is found,
                this is the threshold for keeping it tracked. 0.5 is fine.
            model_complexity: 0 (fast, less accurate) or 1 (accurate, slightly
                slower). For a game, 1 is worth it.
            smoothing_alpha: Exponential smoothing factor for the fingertip,
                0 = no smoothing, 1 = completely frozen. 0.5 is a good start.
                Lower this if the cursor feels laggy; raise it if it's jittery.
        """
        self.confidence_threshold = float(confidence_threshold)
        self.tracking_confidence = float(tracking_confidence)
        self.max_num_hands = int(max_num_hands)
        self.model_complexity = int(model_complexity)
        self.smoothing_alpha = float(smoothing_alpha)

        # `device` is accepted but unused. Log once so it's not surprising.
        if device is not None and str(device) != "cpu":
            logger.info(
                "MediaPipe runs on CPU; ignoring device=%s. "
                "Performance is still comfortably real-time for this game.",
                device,
            )

        logger.info(
            "Initializing MediaPipe Hands (max_hands=%d, det_conf=%.2f, "
            "track_conf=%.2f, complexity=%d)",
            self.max_num_hands,
            self.confidence_threshold,
            self.tracking_confidence,
            self.model_complexity,
        )

        self._mp_hands = mp.solutions.hands
        self._mp_drawing = mp.solutions.drawing_utils
        self._mp_styles = mp.solutions.drawing_styles

        # video_mode=True (static_image_mode=False) enables frame-to-frame
        # tracking, which is what we want for a live webcam feed.
        self.hands = self._mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=self.max_num_hands,
            model_complexity=self.model_complexity,
            min_detection_confidence=self.confidence_threshold,
            min_tracking_confidence=self.tracking_confidence,
        )

        # Smoothed fingertip per handedness label, so Left and Right hands
        # don't blend into each other across frames.
        self._smoothed_tip: Dict[str, Tuple[float, float]] = {}

        # Compatibility shim: the old code exposed a `names` dict on the
        # underlying model. Keep a similar attribute so any external tooling
        # that peeks at `detector.model.names` still works.
        self.model = _CompatModelShim(names={0: "Right", 1: "Left"})

        logger.info("MediaPipe Hands initialized successfully")

    # ------------------------------------------------------------------
    # Core detection
    # ------------------------------------------------------------------
    def detect(
        self,
        image: np.ndarray,
        conf: Optional[float] = None,
    ) -> List[Dict]:
        """Detect hands in a BGR image and return a list of detection dicts."""
        if image is None or image.size == 0:
            return []

        # MediaPipe expects RGB. OpenCV gives us BGR.
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False  # small perf win — tells MP it can skip a copy

        try:
            results = self.hands.process(rgb)
        except Exception as e:
            logger.error("MediaPipe process() failed: %s", e)
            return []

        if not results.multi_hand_landmarks:
            # No hand this frame — let smoothing decay so stale positions don't linger.
            self._smoothed_tip.clear()
            return []

        h, w = image.shape[:2]
        detections: List[Dict] = []

        # multi_handedness is parallel to multi_hand_landmarks.
        handedness_list = results.multi_handedness or []

        for idx, landmarks in enumerate(results.multi_hand_landmarks):
            # Handedness & its score
            if idx < len(handedness_list):
                classification = handedness_list[idx].classification[0]
                hand_label = classification.label      # 'Left' or 'Right'
                hand_score = float(classification.score)
            else:
                hand_label = "Right"
                hand_score = 1.0

            # Optional runtime threshold override
            min_conf = conf if conf is not None else self.confidence_threshold
            if hand_score < min_conf:
                continue

            # 21 landmarks in pixel coordinates
            pts = np.array(
                [[lm.x * w, lm.y * h] for lm in landmarks.landmark],
                dtype=np.float32,
            )

            # Tight bounding box around the hand
            x1, y1 = np.min(pts, axis=0)
            x2, y2 = np.max(pts, axis=0)
            x1 = max(0, int(x1)); y1 = max(0, int(y1))
            x2 = min(w - 1, int(x2)); y2 = min(h - 1, int(y2))

            # Smoothed slice point (index fingertip by default)
            tip_x, tip_y = float(pts[SLICE_POINT, 0]), float(pts[SLICE_POINT, 1])
            tip_x, tip_y = self._smooth(hand_label, tip_x, tip_y)

            detection = {
                "bbox": [x1, y1, x2, y2],
                "confidence": hand_score,
                "class_id": 0 if hand_label == "Right" else 1,
                "class_name": hand_label,
                "center": [int(round(tip_x)), int(round(tip_y))],
                "width": int(x2 - x1),
                "height": int(y2 - y1),
                "keypoints": [[float(p[0]), float(p[1])] for p in pts],
            }
            detections.append(detection)

        logger.debug("Detected %d hand(s)", len(detections))
        return detections

    def _smooth(self, key: str, x: float, y: float) -> Tuple[float, float]:
        """Exponential smoothing per hand label. Kills the per-frame jitter."""
        alpha = self.smoothing_alpha
        prev = self._smoothed_tip.get(key)
        if prev is None:
            self._smoothed_tip[key] = (x, y)
            return x, y
        sx = alpha * prev[0] + (1.0 - alpha) * x
        sy = alpha * prev[1] + (1.0 - alpha) * y
        self._smoothed_tip[key] = (sx, sy)
        return sx, sy

    # ------------------------------------------------------------------
    # Drawing (same signature as before)
    # ------------------------------------------------------------------
    def draw_detections(
        self,
        image: np.ndarray,
        detections: List[Dict],
        draw_keypoints: bool = True,
        thickness: int = 2,
        color: Tuple[int, int, int] = (0, 255, 0),
    ) -> np.ndarray:
        annotated = image.copy()

        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, thickness)

            # Slice point — drawn big and red so it's obvious this is the
            # point the slicer is using.
            cx, cy = det["center"]
            cv2.circle(annotated, (cx, cy), 8, (0, 0, 255), -1)
            cv2.circle(annotated, (cx, cy), 10, (255, 255, 255), 2)

            label = f"{det['class_name']}: {det['confidence']:.2f}"
            cv2.putText(
                annotated, label, (x1, max(0, y1 - 10)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, thickness,
            )

            if draw_keypoints and "keypoints" in det:
                kps = det["keypoints"]
                # Skeleton connections from MediaPipe
                for a, b in self._mp_hands.HAND_CONNECTIONS:
                    if a < len(kps) and b < len(kps):
                        pa = (int(kps[a][0]), int(kps[a][1]))
                        pb = (int(kps[b][0]), int(kps[b][1]))
                        cv2.line(annotated, pa, pb, (200, 200, 200), 1)
                for i, (x, y) in enumerate(kps):
                    xi, yi = int(x), int(y)
                    # Highlight the tip we're using for slicing
                    if i == SLICE_POINT:
                        continue  # already drawn above, bigger
                    cv2.circle(annotated, (xi, yi), 3, (255, 0, 0), -1)

        return annotated

    # ------------------------------------------------------------------
    # Trajectory & velocity (unchanged public API)
    # ------------------------------------------------------------------
    def get_hand_trajectory(
        self,
        detections_history: List[List[Dict]],
        max_distance: float = 150.0,
    ) -> List[List[Tuple[int, int]]]:
        """Build per-hand trajectories by nearest-center association across frames."""
        trajectories: List[List[Tuple[int, int]]] = []
        if not detections_history or len(detections_history) < 2:
            return trajectories

        current = detections_history[-1]
        for det in current:
            trail: List[Tuple[int, int]] = [tuple(det["center"])]
            for prev_frame in reversed(detections_history[:-1]):
                if not prev_frame:
                    break
                best = None
                best_d = float("inf")
                for prev_det in prev_frame:
                    pc = tuple(prev_det["center"])
                    cc = trail[0]
                    d = float(np.hypot(pc[0] - cc[0], pc[1] - cc[1]))
                    if d < best_d and d < max_distance:
                        best_d = d
                        best = prev_det
                if best is None:
                    break
                trail.insert(0, tuple(best["center"]))
            if len(trail) > 1:
                trajectories.append(trail)
        return trajectories

    def calculate_hand_velocity(
        self,
        trajectory: List[Tuple[int, int]],
        fps: float = 30.0,
    ) -> float:
        """Average pixels/second across the trajectory."""
        if len(trajectory) < 2:
            return 0.0
        p1 = np.array(trajectory[0], dtype=np.float32)
        p2 = np.array(trajectory[-1], dtype=np.float32)
        distance = float(np.linalg.norm(p2 - p1))
        time_seconds = (len(trajectory) - 1) / fps if fps > 0 else 0.0
        return distance / time_seconds if time_seconds > 0 else 0.0

    def is_hand_moving(
        self,
        trajectory: List[Tuple[int, int]],
        velocity_threshold: float = 100.0,
        fps: float = 30.0,
    ) -> bool:
        return self.calculate_hand_velocity(trajectory, fps) > velocity_threshold

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def close(self) -> None:
        try:
            self.hands.close()
        except Exception:
            pass

    def __del__(self):
        self.close()


class _CompatModelShim:
    """Stand-in for `detector.model.names` used by the old YOLO version."""
    def __init__(self, names: Dict[int, str]):
        self.names = names
