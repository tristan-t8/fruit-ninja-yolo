"""
Utility functions for Fruit Ninja YOLO Backend
"""

import os
import json
import logging
import base64
import numpy as np
import cv2
from pathlib import Path
from typing import Dict, Tuple, Optional
from datetime import datetime
from io import BytesIO
from PIL import Image


def setup_logging(log_level: str = 'INFO') -> logging.Logger:
    """
    Setup logging configuration

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)

    Returns:
        Configured logger
    """
    # Create logs directory if it doesn't exist
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)

    # Create logger
    logger = logging.getLogger('fruit_ninja_yolo')
    logger.setLevel(getattr(logging, log_level))

    # Avoid adding multiple handlers
    if logger.handlers:
        return logger

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Create file handler
    log_file = log_dir / f'fruit_ninja_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


def load_config(config_path: str = 'config.json') -> Dict:
    """
    Load configuration from JSON file

    Args:
        config_path: Path to config file

    Returns:
        Configuration dictionary
    """
    # Default configuration
    default_config = {
        'server': {
            'host': '0.0.0.0',
            'port': 5000,
            'debug': False,
            'max_content_length': 50 * 1024 * 1024
        },
        'hand_detector': {
            'model_name': 'YOLOv8n Pose',
            'model_path': 'yolov8n-pose.pt',
            'confidence_threshold': 0.5,
            'img_size': 640,
            'device': 'cuda'
        },
        'fruit_slicer': {
            'motion_threshold': 20.0,
            'max_trail_length': 100,
            'velocity_threshold': 50.0,
            'trail_width': 50
        },
        'logging': {
            'level': 'INFO',
            'log_dir': 'logs'
        }
    }

    # Try to load custom config
    config_file = Path(config_path)
    logger = logging.getLogger('fruit_ninja_yolo')

    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                custom_config = json.load(f)
            # Merge with defaults (deep merge)
            for key, value in custom_config.items():
                if isinstance(value, dict) and key in default_config:
                    default_config[key].update(value)
                else:
                    default_config[key] = value
            logger.info(f"Loaded configuration from {config_path}")
        except Exception as e:
            logger.warning(f"Failed to load config from {config_path}: {str(e)}. Using defaults.")

    return default_config


def validate_input_image(image: np.ndarray) -> Tuple[bool, str]:
    """
    Validate input image

    Args:
        image: Input image array

    Returns:
        Tuple of (is_valid, error_message)
    """
    if image is None:
        return False, "Image is None"

    if not isinstance(image, np.ndarray):
        return False, "Image is not a numpy array"

    if image.size == 0:
        return False, "Image is empty"

    if len(image.shape) != 3:
        return False, f"Invalid image shape: {image.shape}. Expected 3D array (H, W, C)"

    if image.shape[2] not in [3, 4]:
        return False, f"Invalid number of channels: {image.shape[2]}. Expected 3 or 4"

    # Check for reasonable image size
    if image.shape[0] < 64 or image.shape[1] < 64:
        return False, f"Image too small: {image.shape[0]}x{image.shape[1]}. Minimum: 64x64"

    if image.shape[0] > 4096 or image.shape[1] > 4096:
        return False, f"Image too large: {image.shape[0]}x{image.shape[1]}. Maximum: 4096x4096"

    return True, ""


def encode_image_to_base64(image: np.ndarray, img_format: str = 'png') -> str:
    """
    Encode image to base64 string

    Args:
        image: Input image (BGR format)
        img_format: Output format ('png' or 'jpg')

    Returns:
        Base64 encoded string
    """
    try:
        # Convert BGR to RGB
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Convert to PIL Image
        pil_image = Image.fromarray(image_rgb)

        # Encode to bytes
        buffer = BytesIO()
        pil_image.save(buffer, format=img_format.upper())
        buffer.seek(0)

        # Encode to base64
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

        return image_base64

    except Exception as e:
        logger = logging.getLogger('fruit_ninja_yolo')
        logger.error(f"Error encoding image to base64: {str(e)}")
        return ""


def decode_base64_to_image(image_base64: str) -> Optional[np.ndarray]:
    """
    Decode base64 string to image

    Args:
        image_base64: Base64 encoded image string

    Returns:
        Image as numpy array (BGR format) or None
    """
    try:
        # Remove data URI prefix if present
        if ',' in image_base64:
            image_base64 = image_base64.split(',')[1]

        # Decode from base64
        image_bytes = base64.b64decode(image_base64)

        # Load as PIL image
        pil_image = Image.open(BytesIO(image_bytes))

        # Convert to numpy array and BGR
        image_rgb = np.array(pil_image)
        image_bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)

        return image_bgr

    except Exception as e:
        logger = logging.getLogger('fruit_ninja_yolo')
        logger.error(f"Error decoding base64 to image: {str(e)}")
        return None


def resize_image(image: np.ndarray, max_width: int = 1280, max_height: int = 720) -> np.ndarray:
    """
    Resize image to fit within max dimensions while maintaining aspect ratio

    Args:
        image: Input image
        max_width: Maximum width
        max_height: Maximum height

    Returns:
        Resized image
    """
    height, width = image.shape[:2]

    # Calculate scaling factor
    scale = min(max_width / width, max_height / height, 1.0)

    if scale < 1.0:
        new_width = int(width * scale)
        new_height = int(height * scale)
        image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)

    return image


def crop_image(image: np.ndarray, box: Tuple[int, int, int, int]) -> np.ndarray:
    """
    Crop image to bounding box

    Args:
        image: Input image
        box: Bounding box (x1, y1, x2, y2)

    Returns:
        Cropped image
    """
    x1, y1, x2, y2 = box
    x1 = max(0, x1)
    y1 = max(0, y1)
    x2 = min(image.shape[1], x2)
    y2 = min(image.shape[0], y2)

    return image[y1:y2, x1:x2]


def draw_box(
    image: np.ndarray,
    box: Tuple[int, int, int, int],
    label: str = "",
    color: Tuple[int, int, int] = (0, 255, 0),
    thickness: int = 2
) -> np.ndarray:
    """
    Draw bounding box on image

    Args:
        image: Input image
        box: Bounding box (x1, y1, x2, y2)
        label: Label text
        color: Box color (BGR)
        thickness: Box thickness

    Returns:
        Image with drawn box
    """
    x1, y1, x2, y2 = box

    # Draw rectangle
    cv2.rectangle(image, (x1, y1), (x2, y2), color, thickness)

    # Draw label if provided
    if label:
        label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)[0]
        cv2.rectangle(
            image,
            (x1, y1 - label_size[1] - 4),
            (x1 + label_size[0], y1),
            color,
            -1
        )
        cv2.putText(
            image,
            label,
            (x1, y1 - 2),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            1
        )

    return image


def calculate_iou(
    box1: Tuple[int, int, int, int],
    box2: Tuple[int, int, int, int]
) -> float:
    """
    Calculate Intersection over Union (IoU) between two boxes

    Args:
        box1: First box (x1, y1, x2, y2)
        box2: Second box (x1, y1, x2, y2)

    Returns:
        IoU value (0-1)
    """
    x1_min, y1_min, x1_max, y1_max = box1
    x2_min, y2_min, x2_max, y2_max = box2

    # Calculate intersection
    inter_xmin = max(x1_min, x2_min)
    inter_ymin = max(y1_min, y2_min)
    inter_xmax = min(x1_max, x2_max)
    inter_ymax = min(y1_max, y2_max)

    if inter_xmax < inter_xmin or inter_ymax < inter_ymin:
        return 0.0

    inter_area = (inter_xmax - inter_xmin) * (inter_ymax - inter_ymin)

    # Calculate union
    box1_area = (x1_max - x1_min) * (y1_max - y1_min)
    box2_area = (x2_max - x2_min) * (y2_max - y2_min)
    union_area = box1_area + box2_area - inter_area

    if union_area == 0:
        return 0.0

    return inter_area / union_area


def get_performance_metrics() -> Dict:
    """
    Get system performance metrics

    Returns:
        Dictionary with performance metrics
    """
    import torch

    metrics = {
        'timestamp': datetime.now().isoformat(),
        'gpu_available': torch.cuda.is_available()
    }

    try:
        import psutil
        metrics['cpu_percent'] = psutil.cpu_percent(interval=1)
        metrics['memory_percent'] = psutil.virtual_memory().percent
    except ImportError:
        pass

    if torch.cuda.is_available():
        metrics['gpu_memory_used'] = torch.cuda.memory_allocated() / 1e9
        metrics['gpu_memory_total'] = torch.cuda.get_device_properties(0).total_memory / 1e9

    return metrics
