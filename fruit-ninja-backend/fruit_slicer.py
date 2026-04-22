"""
Fruit Slicer Module
Detects hand motion and processes fruit slicing
"""

import cv2
import numpy as np
import torch
import logging
from typing import List, Dict, Tuple, Optional
from scipy.spatial.distance import euclidean

logger = logging.getLogger(__name__)


class FruitSlicer:
    """
    Handles fruit slicing detection and processing
    Uses hand motion detection to identify slice actions
    """

    def __init__(
        self,
        motion_threshold: float = 20.0,
        max_trail_length: int = 100,
        device: torch.device = None
    ):
        """
        Initialize fruit slicer

        Args:
            motion_threshold: Minimum pixel distance to detect motion
            max_trail_length: Maximum length of hand trail
            device: PyTorch device
        """
        self.motion_threshold = motion_threshold
        self.max_trail_length = max_trail_length
        self.device = device or torch.device('cpu')
        self.hand_trail = []
        self.prev_hand_position = None

        logger.info(f"Fruit slicer initialized on {device}")

    def process_slice(
        self,
        image: np.ndarray,
        current_detections: List[Dict],
        hand_history: Optional[List[List[Dict]]] = None,
        velocity_threshold: float = 50.0
    ) -> Dict:
        """
        Process fruit slicing based on hand motion

        Args:
            image: Current frame image
            current_detections: Hand detections in current frame
            hand_history: History of hand detections
            velocity_threshold: Minimum velocity for slicing

        Returns:
            Dict with slicing information
        """
        result = {
            'sliced': False,
            'affected_fruits': [],
            'hand_motion': None,
            'confidence': 0.0,
            'annotated_image': image.copy(),
            'hand_trail': self.hand_trail.copy()
        }

        if not current_detections:
            self.hand_trail = []
            self.prev_hand_position = None
            return result

        # Get primary hand (usually the most confident detection)
        primary_hand = max(current_detections, key=lambda x: x['confidence'])
        current_position = tuple(primary_hand['center'])

        # Update hand trail
        self._update_hand_trail(current_position)

        # Check for slicing motion
        slicing_info = self._detect_slice_motion(
            current_position,
            hand_history,
            velocity_threshold
        )

        result['hand_motion'] = slicing_info

        # If slicing detected, find affected fruits
        if slicing_info and slicing_info.get('is_slicing', False):
            result['sliced'] = True
            result['confidence'] = min(1.0, slicing_info.get('velocity', 0.0) / 100.0)

            # Find fruits affected by slice motion
            affected = self._find_affected_fruits(
                image,
                self.hand_trail,
                slicing_info
            )
            result['affected_fruits'] = affected

        # Draw annotations
        annotated = self._draw_annotations(
            image.copy(),
            current_detections,
            self.hand_trail,
            result['affected_fruits'],
            result['sliced']
        )
        result['annotated_image'] = annotated

        return result

    def _update_hand_trail(self, position: Tuple[int, int]):
        """Update hand trail with new position"""
        self.hand_trail.append(position)

        # Keep trail length in check
        if len(self.hand_trail) > self.max_trail_length:
            self.hand_trail.pop(0)

        self.prev_hand_position = position

    def _detect_slice_motion(
        self,
        current_position: Tuple[int, int],
        hand_history: Optional[List[List[Dict]]],
        velocity_threshold: float = 50.0
    ) -> Optional[Dict]:
        """
        Detect if hand motion indicates a slice action

        Args:
            current_position: Current hand center position
            hand_history: History of hand detections
            velocity_threshold: Minimum velocity for slicing

        Returns:
            Dict with slice motion info or None
        """
        if self.prev_hand_position is None:
            self.prev_hand_position = current_position
            return None

        # Calculate motion
        motion_distance = euclidean(self.prev_hand_position, current_position)

        # Check if motion exceeds threshold
        if motion_distance < self.motion_threshold:
            return None

        # Analyze trajectory for continuity (indicates deliberate swipe, not jitter)
        if len(self.hand_trail) > 5:
            trajectory_smoothness = self._calculate_trajectory_smoothness(
                self.hand_trail[-10:]
            )
        else:
            trajectory_smoothness = 0.5

        # Calculate velocity (approximate FPS of 30)
        velocity = motion_distance * 30

        # Determine if slicing
        is_slicing = (
            motion_distance > self.motion_threshold and
            velocity > velocity_threshold and
            trajectory_smoothness > 0.3
        )

        slice_info = {
            'is_slicing': is_slicing,
            'motion_distance': float(motion_distance),
            'velocity': float(velocity),
            'trajectory_smoothness': float(trajectory_smoothness)
        }

        return slice_info

    def _calculate_trajectory_smoothness(
        self,
        trajectory: List[Tuple[int, int]]
    ) -> float:
        """
        Calculate smoothness of trajectory (0-1, higher is smoother)
        Helps distinguish intentional swipes from jitter
        """
        if len(trajectory) < 3:
            return 0.5

        # Calculate angles between consecutive segments
        angles = []
        for i in range(len(trajectory) - 2):
            p1 = np.array(trajectory[i])
            p2 = np.array(trajectory[i + 1])
            p3 = np.array(trajectory[i + 2])

            v1 = p2 - p1
            v2 = p3 - p2

            if np.linalg.norm(v1) > 0 and np.linalg.norm(v2) > 0:
                cos_angle = np.dot(v1, v2) / (
                    np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-6
                )
                angle = np.arccos(np.clip(cos_angle, -1, 1))
                angles.append(angle)

        if not angles:
            return 0.5

        # Lower variance in angles means smoother trajectory
        angle_variance = np.var(angles)
        smoothness = 1.0 / (1.0 + angle_variance)

        return float(smoothness)

    def _find_affected_fruits(
        self,
        image: np.ndarray,
        hand_trail: List[Tuple[int, int]],
        slicing_info: Dict,
        trail_width: int = 50
    ) -> List[Dict]:
        """
        Find fruits affected by the slice motion

        Args:
            image: Current frame
            hand_trail: Hand trajectory
            slicing_info: Slice motion information
            trail_width: Width of slicing area around trail

        Returns:
            List of affected fruits with positions
        """
        affected = []

        if len(hand_trail) < 2:
            return affected

        # Create mask for slice area
        mask = np.zeros(image.shape[:2], dtype=np.uint8)

        # Draw thick line along hand trail
        for i in range(len(hand_trail) - 1):
            pt1 = tuple(map(int, hand_trail[i]))
            pt2 = tuple(map(int, hand_trail[i + 1]))
            cv2.line(mask, pt1, pt2, 255, trail_width)

        # Analyze colors in the affected area
        affected_pixels = int(np.count_nonzero(mask))

        if affected_pixels > 0:
            # Simple fruit detection based on color ranges
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

            fruits = []

            # Red fruits (apple, strawberry)
            lower_red1 = np.array([0, 100, 100])
            upper_red1 = np.array([10, 255, 255])
            red_mask1 = cv2.inRange(hsv, lower_red1, upper_red1)

            lower_red2 = np.array([170, 100, 100])
            upper_red2 = np.array([180, 255, 255])
            red_mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
            red_mask = cv2.bitwise_or(red_mask1, red_mask2)

            # Yellow fruits (banana, pineapple)
            lower_yellow = np.array([15, 100, 100])
            upper_yellow = np.array([35, 255, 255])
            yellow_mask = cv2.inRange(hsv, lower_yellow, upper_yellow)

            # Orange fruits (orange)
            lower_orange = np.array([5, 100, 100])
            upper_orange = np.array([25, 255, 255])
            orange_mask = cv2.inRange(hsv, lower_orange, upper_orange)

            # Green fruits (lime, green apple)
            lower_green = np.array([40, 50, 50])
            upper_green = np.array([90, 255, 255])
            green_mask = cv2.inRange(hsv, lower_green, upper_green)

            # Purple fruits (grape)
            lower_purple = np.array([130, 50, 50])
            upper_purple = np.array([170, 255, 255])
            purple_mask = cv2.inRange(hsv, lower_purple, upper_purple)

            # Find contours for each fruit type
            fruit_types = [
                ('red', red_mask),
                ('yellow', yellow_mask),
                ('orange', orange_mask),
                ('green', green_mask),
                ('purple', purple_mask)
            ]

            for fruit_type, fruit_mask in fruit_types:
                # Combine with slice mask
                intersection = cv2.bitwise_and(fruit_mask, mask)

                if np.count_nonzero(intersection) > 100:
                    # Find contours
                    contours, _ = cv2.findContours(
                        intersection,
                        cv2.RETR_EXTERNAL,
                        cv2.CHAIN_APPROX_SIMPLE
                    )

                    for contour in contours:
                        if cv2.contourArea(contour) > 50:
                            M = cv2.moments(contour)
                            if M['m00'] > 0:
                                cx = int(M['m10'] / M['m00'])
                                cy = int(M['m01'] / M['m00'])

                                fruits.append({
                                    'type': fruit_type,
                                    'position': [cx, cy],
                                    'confidence': min(0.95, affected_pixels / 10000.0),
                                    'area': float(cv2.contourArea(contour))
                                })

            affected = fruits

        return affected

    def _draw_annotations(
        self,
        image: np.ndarray,
        detections: List[Dict],
        hand_trail: List[Tuple[int, int]],
        affected_fruits: List[Dict],
        sliced: bool
    ) -> np.ndarray:
        """
        Draw annotations on image
        """
        annotated = image.copy()

        # Draw hand detections
        for detection in detections:
            x1, y1, x2, y2 = detection['bbox']
            color = (0, 255, 0)
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

            cx, cy = detection['center']
            cv2.circle(annotated, (cx, cy), 5, color, -1)

        # Draw hand trail
        if len(hand_trail) > 1:
            trail_color = (255, 0, 0) if sliced else (0, 255, 255)
            for i in range(len(hand_trail) - 1):
                pt1 = tuple(map(int, hand_trail[i]))
                pt2 = tuple(map(int, hand_trail[i + 1]))
                cv2.line(annotated, pt1, pt2, trail_color, 3)

        # Draw affected fruits
        for fruit in affected_fruits:
            x, y = fruit['position']
            cv2.circle(annotated, (x, y), 20, (0, 0, 255), 2)
            cv2.putText(
                annotated,
                f"{fruit['type']}",
                (x - 20, y - 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 0, 255),
                2
            )

        # Draw status
        status = "SLICING!" if sliced else "Ready"
        status_color = (0, 0, 255) if sliced else (0, 255, 0)
        cv2.putText(
            annotated,
            status,
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            status_color,
            2
        )

        return annotated

    def reset(self):
        """Reset internal state"""
        self.hand_trail = []
        self.prev_hand_position = None
