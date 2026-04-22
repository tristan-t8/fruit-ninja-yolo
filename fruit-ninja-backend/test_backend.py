#!/usr/bin/env python3
"""
Fruit Ninja YOLO Backend - Test Script
Tests all components and verifies setup
"""

import sys
import os
import time
import subprocess
import json
from pathlib import Path


def print_header(text):
    print()
    print("=" * 50)
    print(text.center(50))
    print("=" * 50)
    print()


def test_python():
    """Test Python installation"""
    print("[1] Testing Python...")
    try:
        version = sys.version_info
        if version.major < 3 or (version.major == 3 and version.minor < 8):
            print(f"  FAIL: Python {version.major}.{version.minor} found. Python 3.8+ required.")
            return False
        print(f"  OK: Python {version.major}.{version.minor}.{version.micro}")
        return True
    except Exception as e:
        print(f"  FAIL: Python test failed: {e}")
        return False


def test_imports():
    """Test required imports"""
    print("\n[2] Testing imports...")

    required_packages = {
        'numpy': 'numpy',
        'cv2': 'opencv-python',
        'torch': 'torch',
        'flask': 'Flask',
        'PIL': 'Pillow',
        'ultralytics': 'ultralytics',
        'scipy': 'scipy',
    }

    all_ok = True
    for module, package_name in required_packages.items():
        try:
            __import__(module)
            print(f"  OK: {module}")
        except ImportError:
            print(f"  FAIL: {module} not found (pip install {package_name})")
            all_ok = False

    return all_ok


def test_cuda():
    """Test CUDA availability"""
    print("\n[3] Testing CUDA...")
    try:
        import torch

        if torch.cuda.is_available():
            print("  OK: CUDA Available")
            print(f"    Device: {torch.cuda.get_device_name(0)}")
            print(f"    CUDA Version: {torch.version.cuda}")
            print(f"    GPU Count: {torch.cuda.device_count()}")

            # Test GPU computation
            try:
                x = torch.randn(1000, 1000).cuda()
                y = torch.randn(1000, 1000).cuda()
                z = torch.mm(x, y)
                print("  OK: GPU computation works")
            except Exception as e:
                print(f"  WARN: GPU computation test failed: {e}")

            return True
        else:
            print("  WARN: CUDA Not Available (CPU will be used)")
            return True
    except Exception as e:
        print(f"  FAIL: CUDA test failed: {e}")
        return False


def test_models():
    """Test model loading"""
    print("\n[4] Testing model loading...")
    try:
        from ultralytics import YOLO
        import torch

        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

        print("  Loading YOLOv8n-pose model (this may take a minute on first run)...")
        model = YOLO('yolov8n-pose.pt')
        model.to(device)
        print("  OK: Model loaded successfully")
        return True
    except Exception as e:
        print(f"  FAIL: Model loading failed: {e}")
        print("  Try: pip install ultralytics")
        return False


def test_config():
    """Test configuration file"""
    print("\n[5] Testing configuration...")
    try:
        config_path = Path('config.json')
        if not config_path.exists():
            print("  FAIL: config.json not found")
            return False

        with open(config_path) as f:
            config = json.load(f)

        # Validate config structure
        required_keys = ['server', 'hand_detector', 'fruit_slicer']
        for key in required_keys:
            if key not in config:
                print(f"  FAIL: Missing '{key}' in config.json")
                return False

        print("  OK: Configuration valid")
        print(f"    Server: {config['server']['host']}:{config['server']['port']}")
        print(f"    Device: {config['hand_detector']['device']}")
        return True
    except json.JSONDecodeError as e:
        print(f"  FAIL: Invalid JSON in config.json: {e}")
        return False
    except Exception as e:
        print(f"  FAIL: Configuration test failed: {e}")
        return False


def test_server():
    """Test if server can start"""
    print("\n[6] Testing server startup...")
    print("  Starting server in background...")

    try:
        import requests
    except ImportError:
        print("  SKIP: requests package not installed")
        return True

    process = None
    try:
        process = subprocess.Popen(
            [sys.executable, 'app.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Wait for server to start
        time.sleep(8)

        # Check if process is still running
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            print("  FAIL: Server failed to start")
            print(f"  Error: {stderr[:500]}")
            return False

        # Test health endpoint
        try:
            response = requests.get('http://localhost:5000/health', timeout=5)
            if response.status_code == 200:
                print("  OK: Server started successfully")
                health = response.json()
                print(f"    Status: {health.get('status')}")
                print(f"    Device: {health.get('device')}")
                print(f"    Models loaded: {health.get('models_loaded')}")
                return True
            else:
                print(f"  FAIL: Health check returned {response.status_code}")
                return False
        except requests.exceptions.ConnectionError:
            print("  FAIL: Could not connect to server on localhost:5000")
            return False
    except Exception as e:
        print(f"  FAIL: Server test failed: {e}")
        return False
    finally:
        if process is not None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()


def print_summary(results):
    """Print test summary"""
    print_header("Test Summary")

    test_names = [
        "Python Version",
        "Required Imports",
        "CUDA Support",
        "Model Loading",
        "Configuration",
        "Server Startup"
    ]

    passed = sum(1 for r in results if r)
    total = len(results)

    for name, result in zip(test_names, results):
        status = "PASS" if result else "FAIL"
        print(f"  {name:<30} [{status}]")

    print(f"\n  Overall: {passed}/{total} tests passed")

    if passed == total:
        print("\n  All tests passed! Backend is ready to use.")
        print("\n  Start the server with: python app.py")
        print("  Test with: curl http://localhost:5000/health")
        return True
    else:
        print("\n  Some tests failed. Please fix the issues above.")
        return False


def main():
    """Run all tests"""
    print_header("Fruit Ninja YOLO Backend Test Suite")

    results = [
        test_python(),
        test_imports(),
        test_cuda(),
        test_models(),
        test_config(),
        test_server()
    ]

    success = print_summary(results)
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
