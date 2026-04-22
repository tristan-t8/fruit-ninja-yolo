import cv2
import asyncio
import websockets
import json
from fastapi import FastAPI
from contextlib import asynccontextmanager
from hand_detector import HandDetector
import uvicorn

detector = None
cap = None
prev_hand = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global detector, cap
    detector = HandDetector()
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    print("✅ Backend ready - YOLO on CUDA if available")
    yield
    cap.release()

app = FastAPI(lifespan=lifespan)

async def websocket_handler(websocket: websockets.WebSocketServerProtocol):
    global prev_hand
    await websocket.accept()
    print("🎮 Flutter connected - streaming hand positions")

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame = cv2.flip(frame, 1)  # mirror

        hand = detector.detect(frame)
        if hand:
            data = {
                "type": "hand_move",
                "x": hand["x"],
                "y": hand["y"]
            }
            await websocket.send(json.dumps(data))
            prev_hand = (hand["x"], hand["y"])
        else:
            prev_hand = None

        await asyncio.sleep(0.016)  # ~60 FPS

@app.websocket("/ws")
async def websocket_endpoint(websocket: websockets.WebSocketServerProtocol):
    await websocket_handler(websocket)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8765)