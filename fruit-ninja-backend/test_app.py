"""
Fruit Ninja YOLO Backend Server
Detects hands using YOLO and processes fruit slicing with CUDA support
Includes browser-based testing page at /test
"""

import os
import sys
import cv2
import numpy as np
import torch
import logging
import webbrowser
import threading
import time
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from datetime import datetime
from typing import Optional
import base64
from io import BytesIO
from PIL import Image

# Import custom modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hand_detector import HandDetector
from fruit_slicer import FruitSlicer
from utils import (
    setup_logging,
    load_config,
    validate_input_image,
    encode_image_to_base64,
)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Setup logging
logger = setup_logging()

# Load configuration
config = load_config()

# Global objects
hand_detector = None
fruit_slicer = None
device = None


# ============================================================
# Browser-based testing page HTML
# ============================================================
TEST_PAGE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Fruit Ninja YOLO - Browser Test</title>
    <meta charset="UTF-8">
    <style>
        * { box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0;
            padding: 20px;
            min-height: 100vh;
            color: #333;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            padding: 30px;
        }
        h1 {
            color: #667eea;
            margin-top: 0;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .status-card {
            background: #f7f9fc;
            border-left: 4px solid #667eea;
            padding: 15px;
            border-radius: 4px;
            margin-bottom: 20px;
        }
        .status-ok { border-left-color: #48bb78; }
        .status-fail { border-left-color: #f56565; }
        .status-pending { border-left-color: #ed8936; }
        .grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-top: 20px;
        }
        @media (max-width: 768px) {
            .grid { grid-template-columns: 1fr; }
        }
        .panel {
            background: #f7f9fc;
            padding: 20px;
            border-radius: 8px;
            border: 1px solid #e2e8f0;
        }
        .panel h2 {
            margin-top: 0;
            color: #4a5568;
            font-size: 18px;
        }
        video, canvas, img {
            max-width: 100%;
            border-radius: 8px;
            background: #2d3748;
        }
        button {
            background: #667eea;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            margin: 5px;
            transition: background 0.2s;
        }
        button:hover { background: #5568d3; }
        button:disabled { background: #cbd5e0; cursor: not-allowed; }
        button.red { background: #f56565; }
        button.red:hover { background: #e53e3e; }
        button.green { background: #48bb78; }
        button.green:hover { background: #38a169; }
        .btn-group { margin: 10px 0; }
        input[type="file"] {
            margin: 10px 0;
            padding: 10px;
            width: 100%;
            border: 2px dashed #cbd5e0;
            border-radius: 6px;
        }
        .results {
            background: #1a202c;
            color: #48bb78;
            padding: 15px;
            border-radius: 6px;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            overflow-x: auto;
            max-height: 400px;
            overflow-y: auto;
            white-space: pre-wrap;
            margin-top: 10px;
        }
        .info-grid {
            display: grid;
            grid-template-columns: auto 1fr;
            gap: 10px;
            font-size: 14px;
        }
        .info-grid > div:nth-child(odd) {
            font-weight: 600;
            color: #4a5568;
        }
        .badge {
            display: inline-block;
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
        }
        .badge-ok { background: #c6f6d5; color: #22543d; }
        .badge-fail { background: #fed7d7; color: #742a2a; }
        .badge-warn { background: #feebc8; color: #744210; }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 10px;
            margin-top: 15px;
        }
        .stat {
            background: white;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
            border: 1px solid #e2e8f0;
        }
        .stat-value {
            font-size: 24px;
            font-weight: bold;
            color: #667eea;
        }
        .stat-label {
            font-size: 11px;
            color: #718096;
            text-transform: uppercase;
            margin-top: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎮 Fruit Ninja YOLO Backend - Browser Test</h1>

        <div id="status-card" class="status-card status-pending">
            <strong>Server Status:</strong> <span id="status">Checking...</span>
        </div>

        <div class="stats" id="stats" style="display:none;">
            <div class="stat">
                <div class="stat-value" id="stat-device">-</div>
                <div class="stat-label">Device</div>
            </div>
            <div class="stat">
                <div class="stat-value" id="stat-cuda">-</div>
                <div class="stat-label">CUDA</div>
            </div>
            <div class="stat">
                <div class="stat-value" id="stat-models">-</div>
                <div class="stat-label">Models</div>
            </div>
        </div>

        <div class="grid">
            <!-- LEFT: Camera/Upload Panel -->
            <div class="panel">
                <h2>📹 Camera / Upload</h2>

                <div class="btn-group">
                    <button id="btn-start-camera" class="green">Start Camera</button>
                    <button id="btn-stop-camera" class="red" disabled>Stop Camera</button>
                </div>

                <video id="video" autoplay muted playsinline style="display:none;"></video>
                <canvas id="canvas" style="display:none;"></canvas>
                <img id="preview" style="display:none;" alt="Preview">

                <div style="margin-top:15px;">
                    <strong>Or upload an image:</strong>
                    <input type="file" id="file-input" accept="image/*">
                </div>

                <div class="btn-group">
                    <button id="btn-detect">Detect Hand</button>
                    <button id="btn-slice">Detect Slice</button>
                    <button id="btn-auto" class="green">Auto Mode (Live)</button>
                    <button id="btn-stop-auto" class="red" disabled>Stop Auto</button>
                </div>
            </div>

            <!-- RIGHT: Results Panel -->
            <div class="panel">
                <h2>📊 Results</h2>
                <img id="result-image" style="display:none;" alt="Result">
                <div id="result-summary" style="margin-top:15px;"></div>
                <div class="results" id="results">Ready. Click a button to test the backend.</div>
            </div>
        </div>
    </div>

    <script>
        const SERVER_URL = window.location.origin;
        let stream = null;
        let handHistory = [];
        let autoInterval = null;

        const video = document.getElementById('video');
        const canvas = document.getElementById('canvas');
        const preview = document.getElementById('preview');
        const resultImage = document.getElementById('result-image');
        const results = document.getElementById('results');
        const summary = document.getElementById('result-summary');

        function log(msg) {
            const time = new Date().toLocaleTimeString();
            results.textContent = `[${time}] ${msg}\n` + results.textContent;
        }

        function setStatus(text, type) {
            const card = document.getElementById('status-card');
            card.className = 'status-card status-' + type;
            document.getElementById('status').textContent = text;
        }

        // Check server health on load
        async function checkHealth() {
            try {
                const res = await fetch(SERVER_URL + '/health');
                const data = await res.json();
                if (data.status === 'healthy') {
                    setStatus('Healthy ✓', 'ok');
                    document.getElementById('stats').style.display = 'grid';
                    document.getElementById('stat-device').textContent = data.device;
                    document.getElementById('stat-cuda').textContent = data.cuda_available ? '✓' : '✗';
                    document.getElementById('stat-models').textContent = data.models_loaded ? '✓' : '✗';
                    log('Server healthy. Device: ' + data.device);
                } else {
                    setStatus('Not Ready', 'fail');
                }
            } catch (e) {
                setStatus('Offline', 'fail');
                log('ERROR: Cannot reach server. ' + e.message);
            }
        }

        // Start camera
        document.getElementById('btn-start-camera').onclick = async () => {
            try {
                stream = await navigator.mediaDevices.getUserMedia({
                    video: { width: 640, height: 480, facingMode: 'user' }
                });
                video.srcObject = stream;
                video.style.display = 'block';
                preview.style.display = 'none';
                document.getElementById('btn-start-camera').disabled = true;
                document.getElementById('btn-stop-camera').disabled = false;
                log('Camera started');
            } catch (e) {
                log('ERROR: Cannot access camera. ' + e.message);
            }
        };

        // Stop camera
        document.getElementById('btn-stop-camera').onclick = () => {
            if (stream) {
                stream.getTracks().forEach(t => t.stop());
                stream = null;
            }
            video.style.display = 'none';
            document.getElementById('btn-start-camera').disabled = false;
            document.getElementById('btn-stop-camera').disabled = true;
            log('Camera stopped');
        };

        // File upload
        document.getElementById('file-input').onchange = (e) => {
            const file = e.target.files[0];
            if (!file) return;
            const reader = new FileReader();
            reader.onload = (ev) => {
                preview.src = ev.target.result;
                preview.style.display = 'block';
                video.style.display = 'none';
                log('Image loaded: ' + file.name);
            };
            reader.readAsDataURL(file);
        };

        // Get current image as base64
        function captureImage() {
            if (stream && video.videoWidth > 0) {
                canvas.width = video.videoWidth;
                canvas.height = video.videoHeight;
                canvas.getContext('2d').drawImage(video, 0, 0);
                return canvas.toDataURL('image/jpeg', 0.8).split(',')[1];
            } else if (preview.src) {
                canvas.width = preview.naturalWidth || 640;
                canvas.height = preview.naturalHeight || 480;
                canvas.getContext('2d').drawImage(preview, 0, 0, canvas.width, canvas.height);
                return canvas.toDataURL('image/jpeg', 0.8).split(',')[1];
            }
            return null;
        }

        // Detect hand
        document.getElementById('btn-detect').onclick = async () => {
            const image = captureImage();
            if (!image) {
                log('ERROR: No image. Start camera or upload an image.');
                return;
            }
            log('Detecting hand...');
            try {
                const t0 = Date.now();
                const res = await fetch(SERVER_URL + '/detect', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({image: image})
                });
                const data = await res.json();
                const elapsed = Date.now() - t0;

                if (data.image) {
                    resultImage.src = 'data:image/png;base64,' + data.image;
                    resultImage.style.display = 'block';
                }

                const count = (data.detections || []).length;
                summary.innerHTML = `<span class="badge badge-ok">${count} hand(s) detected</span>
                    <span class="badge badge-warn">${elapsed}ms</span>`;
                log(`Detected ${count} hand(s) in ${elapsed}ms`);
                log(JSON.stringify(data.detections, null, 2));
            } catch (e) {
                log('ERROR: ' + e.message);
            }
        };

        // Detect slice
        document.getElementById('btn-slice').onclick = async () => {
            const image = captureImage();
            if (!image) {
                log('ERROR: No image. Start camera or upload an image.');
                return;
            }
            log('Processing slice...');
            try {
                const t0 = Date.now();
                const res = await fetch(SERVER_URL + '/slice', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({image: image, hand_history: handHistory})
                });
                const data = await res.json();
                const elapsed = Date.now() - t0;

                if (data.image) {
                    resultImage.src = 'data:image/png;base64,' + data.image;
                    resultImage.style.display = 'block';
                }

                handHistory.push(data.current_detections || []);
                if (handHistory.length > 5) handHistory.shift();

                const sliced = data.sliced ? 'SLICED!' : 'No slice';
                const badgeClass = data.sliced ? 'badge-ok' : 'badge-warn';
                const fruitCount = (data.affected_fruits || []).length;
                summary.innerHTML = `<span class="badge ${badgeClass}">${sliced}</span>
                    <span class="badge badge-ok">${fruitCount} fruits affected</span>
                    <span class="badge badge-warn">${elapsed}ms</span>`;
                log(`Slice: ${sliced}, Fruits: ${fruitCount}, Time: ${elapsed}ms`);
            } catch (e) {
                log('ERROR: ' + e.message);
            }
        };

        // Auto mode - live detection
        document.getElementById('btn-auto').onclick = () => {
            if (!stream) {
                log('ERROR: Start camera first for auto mode');
                return;
            }
            document.getElementById('btn-auto').disabled = true;
            document.getElementById('btn-stop-auto').disabled = false;
            log('Auto mode started (detecting every 200ms)');
            autoInterval = setInterval(async () => {
                const image = captureImage();
                if (!image) return;
                try {
                    const res = await fetch(SERVER_URL + '/slice', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({image: image, hand_history: handHistory})
                    });
                    const data = await res.json();
                    if (data.image) {
                        resultImage.src = 'data:image/png;base64,' + data.image;
                        resultImage.style.display = 'block';
                    }
                    handHistory.push(data.current_detections || []);
                    if (handHistory.length > 5) handHistory.shift();
                    if (data.sliced) {
                        log('SLICE! Cut ' + (data.affected_fruits || []).length + ' fruits');
                    }
                } catch (e) {}
            }, 200);
        };

        document.getElementById('btn-stop-auto').onclick = () => {
            if (autoInterval) clearInterval(autoInterval);
            autoInterval = null;
            document.getElementById('btn-auto').disabled = false;
            document.getElementById('btn-stop-auto').disabled = true;
            log('Auto mode stopped');
        };

        // Initial health check
        checkHealth();
        setInterval(checkHealth, 10000);
    </script>
</body>
</html>
"""


def initialize_models():
    """Initialize YOLO hand detector and fruit slicer with CUDA support"""
    global hand_detector, fruit_slicer, device

    try:
        # Detect available device
        if torch.cuda.is_available():
            device = torch.device('cuda:0')
            logger.info(f"Using CUDA: {torch.cuda.get_device_name(0)}")
            logger.info(f"CUDA Version: {torch.version.cuda}")
        else:
            device = torch.device('cpu')
            logger.warning("CUDA not available. Using CPU for inference.")

        # Initialize hand detector
        logger.info("Loading YOLO hand detection model...")
        hand_detector = HandDetector(
            model_path=config['hand_detector']['model_path'],
            confidence_threshold=config['hand_detector']['confidence_threshold'],
            device=device
        )
        logger.info("Hand detector initialized successfully")

        # Initialize fruit slicer
        logger.info("Initializing fruit slicer...")
        fruit_slicer = FruitSlicer(
            motion_threshold=config['fruit_slicer']['motion_threshold'],
            max_trail_length=config['fruit_slicer']['max_trail_length'],
            device=device
        )
        logger.info("Fruit slicer initialized successfully")

    except Exception as e:
        logger.error(f"Error initializing models: {str(e)}")
        raise


@app.route('/')
def index():
    """Root page - redirects to test page"""
    return """
    <html>
    <head><title>Fruit Ninja YOLO Backend</title></head>
    <body style="font-family: Arial; padding: 40px; background: #f7f9fc;">
        <h1>🎮 Fruit Ninja YOLO Backend</h1>
        <p>Server is running!</p>
        <p><a href="/test" style="font-size: 20px; color: #667eea;">→ Open Browser Test Page</a></p>
        <hr>
        <h3>Available Endpoints:</h3>
        <ul>
            <li><a href="/health">/health</a> - Health check</li>
            <li><a href="/model-info">/model-info</a> - Model information</li>
            <li><a href="/test">/test</a> - Browser test interface</li>
            <li>POST /detect - Hand detection</li>
            <li>POST /slice - Fruit slicing</li>
            <li>POST /process-video - Video processing</li>
            <li>POST /reset-device - Clear GPU cache</li>
        </ul>
    </body>
    </html>
    """


@app.route('/test')
def test_page():
    """Browser-based testing page"""
    return render_template_string(TEST_PAGE_HTML)


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'device': str(device),
        'cuda_available': torch.cuda.is_available(),
        'models_loaded': hand_detector is not None and fruit_slicer is not None,
        'timestamp': datetime.now().isoformat()
    }), 200


@app.route('/detect', methods=['POST'])
def detect_hand():
    """Detect hands in image"""
    try:
        if hand_detector is None:
            return jsonify({'error': 'Hand detector not initialized'}), 500

        image = _get_image_from_request(request)
        if image is None:
            return jsonify({'error': 'No valid image provided'}), 400

        is_valid, error_msg = validate_input_image(image)
        if not is_valid:
            return jsonify({'error': error_msg}), 400

        detections = hand_detector.detect(image)
        annotated_image = hand_detector.draw_detections(image.copy(), detections)

        response = {
            'detections': detections,
            'image': encode_image_to_base64(annotated_image),
            'timestamp': datetime.now().isoformat(),
            'device': str(device)
        }

        logger.info(f"Hand detection completed. Found {len(detections)} hand(s)")
        return jsonify(response), 200

    except Exception as e:
        logger.error(f"Error in hand detection: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/slice', methods=['POST'])
def slice_fruit():
    """Detect hand motion and slice fruits"""
    try:
        if fruit_slicer is None or hand_detector is None:
            return jsonify({'error': 'Models not initialized'}), 500

        image = _get_image_from_request(request)
        if image is None:
            return jsonify({'error': 'No valid image provided'}), 400

        hand_history = []
        if request.is_json:
            hand_history = request.get_json().get('hand_history', [])

        current_detections = hand_detector.detect(image)

        slicing_info = fruit_slicer.process_slice(
            image=image,
            current_detections=current_detections,
            hand_history=hand_history
        )

        response_image = slicing_info.get('annotated_image', image)

        response = {
            'sliced': slicing_info.get('sliced', False),
            'affected_fruits': slicing_info.get('affected_fruits', []),
            'hand_motion': slicing_info.get('hand_motion', None),
            'confidence': slicing_info.get('confidence', 0.0),
            'current_detections': current_detections,
            'image': encode_image_to_base64(response_image),
            'timestamp': datetime.now().isoformat()
        }

        logger.info(f"Slice processing completed. Sliced: {slicing_info.get('sliced', False)}")
        return jsonify(response), 200

    except Exception as e:
        logger.error(f"Error in fruit slicing: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/process-video', methods=['POST'])
def process_video():
    """Process video stream frame by frame"""
    try:
        if hand_detector is None or fruit_slicer is None:
            return jsonify({'error': 'Models not initialized'}), 500

        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400

        frames = data.get('frames', [])

        if not frames:
            return jsonify({'error': 'No frames provided'}), 400

        processed_results = []
        hand_history = []

        for frame_data in frames:
            image = _decode_base64_image(frame_data)
            if image is None:
                continue

            detections = hand_detector.detect(image)
            hand_history.append(detections)

            if len(hand_history) > 5:
                hand_history.pop(0)

            slicing_info = fruit_slicer.process_slice(
                image=image,
                current_detections=detections,
                hand_history=hand_history
            )

            frame_result = {
                'detections': detections,
                'sliced': slicing_info.get('sliced', False),
                'affected_fruits': slicing_info.get('affected_fruits', []),
                'image': encode_image_to_base64(slicing_info.get('annotated_image', image))
            }

            processed_results.append(frame_result)

        response = {
            'total_frames': len(processed_results),
            'processed_frames': processed_results,
            'timestamp': datetime.now().isoformat()
        }

        logger.info(f"Video processing completed. Processed {len(processed_results)} frames")
        return jsonify(response), 200

    except Exception as e:
        logger.error(f"Error in video processing: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/model-info', methods=['GET'])
def model_info():
    """Get information about loaded models"""
    try:
        info = {
            'device': str(device),
            'cuda_available': torch.cuda.is_available(),
            'cuda_device_count': torch.cuda.device_count() if torch.cuda.is_available() else 0,
            'hand_detector': {
                'model': config['hand_detector'].get('model_name', 'N/A'),
                'model_path': config['hand_detector'].get('model_path', 'N/A'),
                'confidence_threshold': config['hand_detector'].get('confidence_threshold', 0.5),
                'loaded': hand_detector is not None
            },
            'fruit_slicer': {
                'motion_threshold': config['fruit_slicer'].get('motion_threshold', 20),
                'max_trail_length': config['fruit_slicer'].get('max_trail_length', 100),
                'loaded': fruit_slicer is not None
            }
        }

        if torch.cuda.is_available():
            info['gpu_memory'] = {
                'total': torch.cuda.get_device_properties(0).total_memory / 1e9,
                'allocated': torch.cuda.memory_allocated(0) / 1e9,
                'reserved': torch.cuda.memory_reserved(0) / 1e9
            }

        return jsonify(info), 200

    except Exception as e:
        logger.error(f"Error getting model info: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/reset-device', methods=['POST'])
def reset_device():
    """Reset CUDA cache if available"""
    try:
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.reset_peak_memory_stats()
            message = "CUDA cache cleared successfully"
        else:
            message = "CUDA not available"

        logger.info(message)
        return jsonify({'message': message, 'success': True}), 200

    except Exception as e:
        logger.error(f"Error resetting device: {str(e)}")
        return jsonify({'error': str(e), 'success': False}), 500


def _get_image_from_request(request_obj) -> Optional[np.ndarray]:
    """Extract image from Flask request (file or base64)"""
    try:
        if 'image' in request_obj.files:
            file = request_obj.files['image']
            image = Image.open(file.stream)
            return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

        if request_obj.is_json:
            data = request_obj.get_json()
            if data and 'image' in data:
                return _decode_base64_image(data['image'])

        return None

    except Exception as e:
        logger.error(f"Error extracting image from request: {str(e)}")
        return None


def _decode_base64_image(base64_string: str) -> Optional[np.ndarray]:
    """Decode base64 string to numpy array"""
    try:
        if ',' in base64_string:
            base64_string = base64_string.split(',')[1]

        image_data = base64.b64decode(base64_string)
        image = Image.open(BytesIO(image_data))
        return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

    except Exception as e:
        logger.error(f"Error decoding base64 image: {str(e)}")
        return None


@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({'error': 'Internal server error'}), 500


def open_browser(url):
    """Open browser after a short delay"""
    time.sleep(2)
    try:
        webbrowser.open(url)
    except Exception as e:
        logger.warning(f"Could not open browser: {e}")


if __name__ == '__main__':
    try:
        # Initialize models on startup
        initialize_models()

        # Get configuration
        host = config.get('server', {}).get('host', '0.0.0.0')
        port = config.get('server', {}).get('port', 5000)
        debug = config.get('server', {}).get('debug', False)

        # Display URLs
        print()
        print("=" * 60)
        print(" Fruit Ninja YOLO Backend Server")
        print("=" * 60)
        print(f" Server running on: http://localhost:{port}")
        print(f" Browser Test UI:   http://localhost:{port}/test")
        print(f" Health Check:      http://localhost:{port}/health")
        print("=" * 60)
        print(" Press CTRL+C to stop")
        print("=" * 60)
        print()

        logger.info("Starting Fruit Ninja YOLO Backend Server")
        logger.info(f"Server running on {host}:{port}")

        # Open browser automatically (in background thread)
        browser_url = f"http://localhost:{port}/test"
        threading.Thread(target=open_browser, args=(browser_url,), daemon=True).start()

        # Run Flask app (disable reloader to prevent models loading twice)
        app.run(host=host, port=port, debug=debug, threaded=True, use_reloader=False)

    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")
        sys.exit(1)
