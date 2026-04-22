import torch
from ultralytics import YOLO

class HandDetector:
    def __init__(self, model_path="backend/models/hand_yolov8n.pt"):
        self.device = 0 if torch.cuda.is_available() else "cpu"
        print(f"🚀 YOLO Hand Detector using: {'CUDA GPU' if self.device == 0 else 'CPU'}")
        self.model = YOLO(model_path).to(self.device)

    def detect(self, frame):
        results = self.model(frame, conf=0.5, imgsz=640, verbose=False)
        hands = []
        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cx = (x1 + x2) // 2
                cy = (y1 + y2) // 2
                hands.append({"x": cx, "y": cy})
        return hands[0] if hands else None   # return center of first detected hand (finger approx)