# Fruit Ninja YOLO Backend

Flask server for real-time hand detection and fruit slicing using YOLO and PyTorch with CUDA GPU acceleration.

## Features

- Real-time hand detection using YOLOv8 Pose model
- CUDA GPU acceleration for fast inference
- Hand motion tracking for slice detection
- Fruit identification by color
- RESTful API for easy integration
- Docker support with GPU

## Requirements

- Python 3.8 or higher
- 8GB RAM minimum
- NVIDIA GPU with CUDA 11.8+ (optional but recommended)

## Installation

### Local Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. For CUDA GPU support, install PyTorch with CUDA:
```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

3. Run the server:
```bash
python app.py
```

### Using Startup Scripts

Linux/Mac:
```bash
chmod +x run.sh
./run.sh
```

Windows:
```bash
run.bat
```

### Docker Setup

```bash
docker-compose up -d
```

## API Endpoints

### GET /health
Check server status.

Response:
```json
{
  "status": "healthy",
  "device": "cuda:0",
  "cuda_available": true,
  "models_loaded": true
}
```

### POST /detect
Detect hands in an image.

Request:
```json
{
  "image": "base64_encoded_image"
}
```

Response:
```json
{
  "detections": [
    {
      "bbox": [100, 150, 200, 250],
      "confidence": 0.95,
      "center": [150, 200],
      "class_name": "person"
    }
  ],
  "image": "base64_annotated_image",
  "device": "cuda:0"
}
```

### POST /slice
Process fruit slicing with hand motion.

Request:
```json
{
  "image": "base64_encoded_image",
  "hand_history": []
}
```

Response:
```json
{
  "sliced": true,
  "affected_fruits": [
    {
      "type": "red",
      "position": [300, 400],
      "confidence": 0.85
    }
  ],
  "hand_motion": {
    "is_slicing": true,
    "velocity": 150.5
  }
}
```

### POST /process-video
Process multiple video frames.

Request:
```json
{
  "frames": ["base64_frame1", "base64_frame2"]
}
```

### GET /model-info
Get model and GPU information.

### POST /reset-device
Clear GPU cache.

## Configuration

Edit `config.json`:

```json
{
  "server": {
    "host": "0.0.0.0",
    "port": 5000
  },
  "hand_detector": {
    "model_path": "yolov8n-pose.pt",
    "confidence_threshold": 0.5,
    "device": "cuda"
  },
  "fruit_slicer": {
    "motion_threshold": 20.0,
    "velocity_threshold": 50.0
  }
}
```

## Testing

Run the test suite:
```bash
python test_backend.py
```

Use the Python client:
```bash
python client.py --health
python client.py --detect path/to/image.jpg
python client.py --slice path/to/image.jpg
```

## Troubleshooting

### CUDA Not Detected
```bash
pip uninstall torch
pip install torch --index-url https://download.pytorch.org/whl/cu118
```

### Out of Memory
Edit `config.json` and reduce `img_size` to 320 or 480.

### Model Download Fails
Manually download:
```bash
wget https://github.com/ultralytics/assets/releases/download/v8.1.0/yolov8n-pose.pt
```

### Slow Performance
- Verify GPU usage: `GET /model-info`
- Monitor GPU: `nvidia-smi`
- Use smaller model: `yolov8n-pose.pt`

## File Structure

```
backend/
├── app.py               # Main Flask server
├── hand_detector.py     # YOLO hand detection
├── fruit_slicer.py      # Fruit slicing logic
├── utils.py             # Utility functions
├── client.py            # Python client example
├── test_backend.py      # Test suite
├── config.json          # Configuration
├── requirements.txt     # Dependencies
├── Dockerfile           # Docker image
├── docker-compose.yml   # Docker Compose
├── run.sh               # Linux/Mac startup
├── run.bat              # Windows startup
└── README.md            # This file
```

## Performance

On NVIDIA RTX 3080:
- Hand detection: 120+ FPS
- Slice processing: 90+ FPS
- Latency: 3-5ms per frame

On CPU (Intel i7):
- Hand detection: 15-20 FPS
- Latency: 50-100ms per frame

## Quick Start

```bash
# Install
pip install -r requirements.txt

# Run
python app.py

# Test
curl http://localhost:5000/health
```
