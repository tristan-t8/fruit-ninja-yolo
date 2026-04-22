#!/usr/bin/env python3
"""
Fruit Ninja YOLO Backend - Python Client Example
Demonstrates how to use the backend from a Python client
"""

import sys
import requests
import cv2
import base64
import time
import argparse
from typing import List, Dict, Optional


class FruitNinjaClient:
    """
    Client for interacting with Fruit Ninja YOLO Backend
    """

    def __init__(self, base_url: str = 'http://localhost:5000', timeout: int = 30):
        """
        Initialize client

        Args:
            base_url: Backend server URL
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()

    def health_check(self) -> bool:
        """
        Check if backend is healthy

        Returns:
            True if healthy, False otherwise
        """
        try:
            response = self.session.get(
                f'{self.base_url}/health',
                timeout=self.timeout
            )
            if response.status_code == 200:
                data = response.json()
                print("Backend is healthy")
                print(f"  Status: {data.get('status')}")
                print(f"  Device: {data.get('device')}")
                print(f"  Models loaded: {data.get('models_loaded')}")
                return True
            else:
                print(f"Health check failed: {response.status_code}")
                return False
        except requests.exceptions.ConnectionError:
            print(f"Cannot connect to backend at {self.base_url}")
            return False
        except Exception as e:
            print(f"Health check error: {e}")
            return False

    def get_model_info(self) -> Optional[Dict]:
        """
        Get information about loaded models

        Returns:
            Dictionary with model information
        """
        try:
            response = self.session.get(
                f'{self.base_url}/model-info',
                timeout=self.timeout
            )
            data = response.json()

            print("\nModel Information:")
            print(f"  Device: {data.get('device')}")
            print(f"  CUDA Available: {data.get('cuda_available')}")

            if data.get('hand_detector'):
                hd = data['hand_detector']
                print("\n  Hand Detector:")
                print(f"    Model: {hd.get('model')}")
                print(f"    Confidence Threshold: {hd.get('confidence_threshold')}")
                print(f"    Loaded: {hd.get('loaded')}")

            if data.get('gpu_memory'):
                gpu = data['gpu_memory']
                print("\n  GPU Memory:")
                print(f"    Total: {gpu.get('total'):.2f} GB")
                print(f"    Allocated: {gpu.get('allocated'):.2f} GB")
                print(f"    Reserved: {gpu.get('reserved'):.2f} GB")

            return data
        except Exception as e:
            print(f"Error getting model info: {e}")
            return None

    def detect_hand(self, image_path: str) -> Optional[List[Dict]]:
        """
        Detect hands in an image

        Args:
            image_path: Path to image file

        Returns:
            List of detections with bounding boxes
        """
        try:
            # Read image
            image = cv2.imread(image_path)
            if image is None:
                print(f"Cannot read image: {image_path}")
                return None

            # Encode to base64
            _, buffer = cv2.imencode('.jpg', image)
            image_base64 = base64.b64encode(buffer).decode()

            # Send request
            start_time = time.time()
            response = self.session.post(
                f'{self.base_url}/detect',
                json={'image': image_base64},
                timeout=self.timeout
            )
            elapsed = time.time() - start_time

            if response.status_code == 200:
                data = response.json()
                detections = data.get('detections', [])

                print(f"\nHand Detection (took {elapsed:.3f}s)")
                print(f"  Found {len(detections)} hand(s)")

                for i, det in enumerate(detections):
                    print(f"\n  Hand {i + 1}:")
                    print(f"    Confidence: {det.get('confidence'):.3f}")
                    print(f"    BBox: {det.get('bbox')}")
                    print(f"    Center: {det.get('center')}")
                    print(f"    Class: {det.get('class_name')}")

                # Save annotated image
                if data.get('image'):
                    image_data = base64.b64decode(data['image'])
                    with open('detection_result.png', 'wb') as f:
                        f.write(image_data)
                    print("\n  Annotated image saved: detection_result.png")

                return detections
            else:
                print(f"Detection failed: {response.status_code}")
                print(f"  {response.text}")
                return None
        except Exception as e:
            print(f"Detection error: {e}")
            return None

    def slice_fruit(self, image_path: str, hand_history: List = None) -> Optional[Dict]:
        """
        Detect fruit slicing

        Args:
            image_path: Path to image file
            hand_history: Previous hand detections

        Returns:
            Slicing result with affected fruits
        """
        try:
            # Read image
            image = cv2.imread(image_path)
            if image is None:
                print(f"Cannot read image: {image_path}")
                return None

            # Encode to base64
            _, buffer = cv2.imencode('.jpg', image)
            image_base64 = base64.b64encode(buffer).decode()

            # Send request
            start_time = time.time()
            response = self.session.post(
                f'{self.base_url}/slice',
                json={
                    'image': image_base64,
                    'hand_history': hand_history or []
                },
                timeout=self.timeout
            )
            elapsed = time.time() - start_time

            if response.status_code == 200:
                data = response.json()

                print(f"\nSlice Processing (took {elapsed:.3f}s)")
                print(f"  Sliced: {data.get('sliced')}")
                print(f"  Confidence: {data.get('confidence'):.3f}")

                if data.get('affected_fruits'):
                    fruits = data['affected_fruits']
                    print(f"  Affected Fruits: {len(fruits)}")
                    for fruit in fruits:
                        print(f"    - {fruit.get('type')} at {fruit.get('position')}")

                if data.get('hand_motion'):
                    motion = data['hand_motion']
                    print("\n  Hand Motion:")
                    print(f"    Is Slicing: {motion.get('is_slicing')}")
                    print(f"    Velocity: {motion.get('velocity'):.2f}")
                    print(f"    Motion Distance: {motion.get('motion_distance'):.2f}")

                return data
            else:
                print(f"Slicing failed: {response.status_code}")
                return None
        except Exception as e:
            print(f"Slicing error: {e}")
            return None

    def process_video(self, video_path: str, sample_rate: int = 5) -> Optional[Dict]:
        """
        Process video file

        Args:
            video_path: Path to video file
            sample_rate: Process every Nth frame

        Returns:
            Processed video results
        """
        try:
            # Open video
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                print(f"Cannot open video: {video_path}")
                return None

            frames = []
            frame_count = 0

            print("\nReading video frames...")
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                # Sample frames
                if frame_count % sample_rate == 0:
                    _, buffer = cv2.imencode('.jpg', frame)
                    image_base64 = base64.b64encode(buffer).decode()
                    frames.append(image_base64)
                    print(f"  Loaded {len(frames)} frames", end='\r')

                frame_count += 1

            cap.release()
            print(f"\nLoaded {len(frames)} frames from {frame_count} total")

            # Process frames
            print("\nProcessing frames...")
            start_time = time.time()
            response = self.session.post(
                f'{self.base_url}/process-video',
                json={'frames': frames},
                timeout=300
            )
            elapsed = time.time() - start_time

            if response.status_code == 200:
                data = response.json()
                print(f"\nVideo Processing Complete (took {elapsed:.3f}s)")
                print(f"  Total Frames: {data.get('total_frames')}")

                # Count slices
                sliced_count = sum(
                    1 for f in data.get('processed_frames', [])
                    if f.get('sliced')
                )
                print(f"  Frames with slices: {sliced_count}")

                return data
            else:
                print(f"Video processing failed: {response.status_code}")
                return None
        except Exception as e:
            print(f"Video processing error: {e}")
            return None

    def reset_device(self) -> bool:
        """
        Clear GPU cache

        Returns:
            True if successful
        """
        try:
            response = self.session.post(
                f'{self.base_url}/reset-device',
                timeout=self.timeout
            )
            if response.status_code == 200:
                print("GPU cache cleared")
                return True
            else:
                print(f"Reset failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"Reset error: {e}")
            return False


def main():
    """
    Main function with CLI interface
    """
    parser = argparse.ArgumentParser(
        description='Fruit Ninja YOLO Backend Client'
    )
    parser.add_argument('--url', default='http://localhost:5000', help='Backend server URL')
    parser.add_argument('--detect', help='Detect hands in image')
    parser.add_argument('--slice', dest='slice_img', help='Process fruit slicing')
    parser.add_argument('--video', help='Process video file')
    parser.add_argument('--sample-rate', type=int, default=5, help='Video sampling rate')
    parser.add_argument('--health', action='store_true', help='Check backend health')
    parser.add_argument('--info', action='store_true', help='Get model information')
    parser.add_argument('--reset', action='store_true', help='Reset GPU cache')

    args = parser.parse_args()

    # Create client
    client = FruitNinjaClient(base_url=args.url)

    # Default to health check if no args
    if not any([args.detect, args.slice_img, args.video, args.health, args.info, args.reset]):
        args.health = True

    # Health check
    if args.health:
        if not client.health_check():
            return 1

    # Get model info
    if args.info:
        client.get_model_info()

    # Detect
    if args.detect:
        client.detect_hand(args.detect)

    # Slice
    if args.slice_img:
        client.slice_fruit(args.slice_img)

    # Process video
    if args.video:
        client.process_video(args.video, sample_rate=args.sample_rate)

    # Reset
    if args.reset:
        client.reset_device()

    return 0


if __name__ == '__main__':
    sys.exit(main())
