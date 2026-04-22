# Flutter Integration - Quick Start (Windows)

## What's in this folder

```
flutter_integration/
├── lib/
│   ├── services/
│   │   └── hand_detection_service.dart    ← Talks to Python backend
│   ├── widgets/
│   │   └── hand_controller_overlay.dart   ← Webcam capture + hand cursor overlay
│   └── main_hand_test.dart                ← Standalone test app
├── run_game.bat                           ← Windows launcher
├── INTEGRATION_INSTRUCTIONS.md            ← Step-by-step modification guide
└── README.md                              ← This file
```

## The Fast Path (recommended order)

### 1. Get the standalone test working first

This proves the webcam + backend + Flutter pipeline works before you touch
any game code.

**Copy into your Flutter game project:**
```
<game-root>/lib/services/hand_detection_service.dart
<game-root>/lib/widgets/hand_controller_overlay.dart
<game-root>/lib/main_hand_test.dart
```

**Add to your game's `pubspec.yaml`** under `dependencies:`
```yaml
  camera: ^0.11.0
  http: ^1.2.0
```

**Fix Flutter's git thing:**
```powershell
git config --global --add safe.directory E:/code/flutter
git config --global --add safe.directory "E:/code/fruit-ninja-yolo/Fruit-Cutting-Game-main/Fruit-Cutting-Game-main"
```

**Make sure the Python backend is running** (`start_server.bat` in your backend folder).

**Run the test:**
```powershell
cd "E:\code\fruit-ninja-yolo\Fruit-Cutting-Game-main\Fruit-Cutting-Game-main"
flutter pub get
flutter run -d windows -t lib/main_hand_test.dart
```

If the green cursor follows your hand and red targets turn green when you
swipe through them → **the pipeline works, move on to step 2**.

If something fails, the status banner at the top tells you what.

### 2. Modify the actual game

Open **INTEGRATION_INSTRUCTIONS.md** and follow Steps 3–5. The only
game-specific work is hooking up virtual pan events to whatever method
the game already uses to slice fruits.

### 3. Run the final thing

Either double-click `run_game.bat` and follow the prompts, or:

```powershell
cd "E:\code\fruit-ninja-yolo\Fruit-Cutting-Game-main\Fruit-Cutting-Game-main"
flutter run -d windows
```

## Running order every time

1. Start Python backend: double-click `start_server.bat` in backend folder
2. Open a new terminal, `flutter run -d windows` in the game folder
3. Play

## What if Windows desktop build fails?

Use Chrome instead:
```powershell
flutter run -d chrome
```

Slower, but works with zero additional setup.

## Files you must copy into the game project

Only three Dart files (plus two pubspec lines):

1. `lib/services/hand_detection_service.dart`
2. `lib/widgets/hand_controller_overlay.dart`
3. `lib/main_hand_test.dart` (optional, just for testing)

Everything else (the overlay's camera capture, the backend call, the hand
cursor painting) is already handled inside those files.

---

**Read `INTEGRATION_INSTRUCTIONS.md` for the full detailed guide with code
samples for modifying the game's gesture handler.**
