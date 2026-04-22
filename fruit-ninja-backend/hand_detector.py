"""
Hand Detector Module
Uses YOLO for real-time hand detection
"""

import cv2
import numpy as np
import torch
import logging
from typing import List, Dict, Tuple, Optional
from ultralytics import YOLO

logger = logging.getLogger(__name__)


class HandDetector:
    """
    Hand detection using YOLO v8
    Detects hand bounding boxes and hand keypoints
    """

    def __init__(
        self,
        model_path: str = "yolov8n-pose.pt",
        confidence_threshold: float = 0.5,
        device: torch.device = None,
        img_size: int = 640
    ):
        """
        Initialize hand detector

        Args:
            model_path: Path to YOLO model or model name
            confidence_threshold: Confidence threshold for detections
            device: PyTorch device (cuda or cpu)
            img_size: Input image size for model
        """
        self.confidence_threshold = confidence_threshold
        self.img_size = img_size
        self.device = device or torch.device('cpu')

        logger.info(f"Loading YOLO model from {model_path}")

        # Load YOLO model
        # Using pose model to detect hand keypoints for better slicing detection
        self.model = YOLO(model_path)
        self.model.to(self.device)

        logger.info(f"YOLO model loaded successfully on {self.device}")

    def detect(
        self,
        image: np.ndarray,
        conf: Optional[float] = None
    ) -> List[Dict]:
        """
        Detect hands in image

        Args:
            image: Input image (BGR format)
            conf: Confidence threshold (uses default if not provided)

        Returns:
            List of detections with bounding boxes and keypoints
        """
        try:
            conf = conf if conf is not None else self.confidence_threshold

            # Run inference
            with torch.no_grad():
                results = self.model(
                    image,
                    conf=conf,
                    imgsz=self.img_size,
                    verbose=False
                )

            # Process results
            detections = []
            for result in results:
                if result.boxes is not None:
                    for i, box in enumerate(result.boxes):
                        # Extract bounding box
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                        confidence = float(box.conf[0].cpu().numpy())
                        class_id = int(box.cls[0].cpu().numpy())

                        detection = {
                            'bbox': [int(x1), int(y1), int(x2), int(y2)],
                            'confidence': confidence,
                            'class_id': class_id,
                            'class_name': self.model.names[class_id],
                            'center': [int((x1 + x2) / 2), int((y1 + y2) / 2)],
                            'width': int(x2 - x1),
                            'height': int(y2 - y1)
                        }

                        # Extract keypoints if available (for pose model)
                        if result.keypoints is not None and i < len(result.keypoints):
                            keypoints = result.keypoints[i].xy[0].cpu().numpy()
                            detection['keypoints'] = [
                                [float(kp[0]), float(kp[1])]
                                for kp in keypoints
                            ]

                        detections.append(detection)

            logger.debug(f"Detected {len(detections)} hand(s)")
            return detections

        except Exception as e:
            logger.error(f"Error during hand detection: {str(e)}")
            return []

    def draw_detections(
        self,
        image: np.ndarray,
        detections: List[Dict],
        draw_keypoints: bool = True,
        thickness: int = 2,
        color: Tuple[int, int, int] = (0, 255, 0)
    ) -> np.ndarray:
        """
        Draw detections on image

        Args:
            image: Input image
            detections: List of detections
            draw_keypoints: Whether to draw hand keypoints
            thickness: Box thickness
            color: Box color (BGR)

        Returns:
            Image with drawn detections
        """
        annotated = image.copy()

        for detection in detections:
            # Draw bounding box
            x1, y1, x2, y2 = detection['bbox']
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, thickness)

            # Draw center point
            cx, cy = detection['center']
            cv2.circle(annotated, (cx, cy), 5, color, -1)

            # Draw label
            label = f"{detection['class_name']}: {detection['confidence']:.2f}"
            cv2.putText(
                annotated,
                label,
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                thickness
            )

            # Draw keypoints if available
            if draw_keypoints and 'keypoints' in detection:
                for kp in detection['keypoints']:
                    x, y = int(kp[0]), int(kp[1])
                    if x > 0 and y > 0:
                        cv2.circle(annotated, (x, y), 3, (255, 0, 0), -1)

        return annotated

    def get_hand_trajectory(
        self,
        detections_history: List[List[Dict]],
        max_distance: float = 100.0
    ) -> List[List[Tuple[int, int]]]:
        """
        Calculate hand trajectories from detection history

        Args:
            detections_history: List of detection lists from previous frames
            max_distance: Maximum distance to consider same hand

        Returns:
            List of trajectories (center points over time)
        """
        trajectories = []

        if not detections_history or len(detections_history) < 2:
            return trajectories

        # Simple tracking: connect detections across frames
        current_detections = detections_history[-1]

        for detection in current_detections:
            trajectory = [tuple(detection['center'])]

            # Look back through history
            for prev_frame_detections in reversed(detections_history[:-1]):
                if not prev_frame_detections:
                    break

                # Find closest detection in previous frame
                min_distance = float('inf')
                closest_detection = None

                for prev_detection in prev_frame_detections:
                    prev_center = tuple(prev_detection['center'])
                    curr_center = trajectory[0]

                    distance = np.sqrt(
                        (prev_center[0] - curr_center[0]) ** 2 +
                        (prev_center[1] - curr_center[1]) ** 2
                    )

                    if distance < min_distance and distance < max_distance:
                        min_distance = distance
                        closest_detection = prev_detection

                if closest_detection:
                    trajectory.insert(0, tuple(closest_detection['center']))
                else:
                    break

            if len(trajectory) > 1:
                trajectories.append(trajectory)

        return trajectories

    def calculate_hand_velocity(
        self,
        trajectory: List[Tuple[int, int]],
        fps: float = 30.0
    ) -> float:
        """
        Calculate hand velocity from trajectory

        Args:
            trajectory: List of center points over time
            fps: Frames per second for velocity calculation

        Returns:
            Velocity in pixels per second
        """
        if len(trajectory) < 2:
            return 0.0

        # Calculate distance between first and last point
        p1 = np.array(trajectory[0])
        p2 = np.array(trajectory[-1])

        distance = np.linalg.norm(p2 - p1)
        time_frames = len(trajectory) - 1
        time_seconds = time_frames / fps

        velocity = distance / time_seconds if time_seconds > 0 else 0.0
        return velocity

    def is_hand_moving(
        self,
        trajectory: List[Tuple[int, int]],
        velocity_threshold: float = 100.0,
        fps: float = 30.0
    ) -> bool:
        """
        Determine if hand is moving fast enough to slice

        Args:
            trajectory: Hand trajectory
            velocity_threshold: Minimum velocity for slicing
            fps: Frames per second

        Returns:
            True if hand is moving fast enough
        """
        velocity = self.calculate_hand_velocity(trajectory, fps)
        return velocity > velocity_threshold
