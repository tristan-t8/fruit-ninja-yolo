# Option A: Integrating Hand Detection into the Flutter Fruit Cutting Game

This guide modifies the existing Flutter game (`Fruit-Cutting-Game-main`) so it uses
your Python YOLO backend for hand-tracking instead of (or alongside) touch input.

## Architecture

```
┌───────────────────────────┐      HTTP POST      ┌──────────────────────┐
│  Flutter game (Windows)   │ ──────────────────▶ │  Python Flask +      │
│  - Flame engine + sprites │  (JPEG frame)       │  YOLO + CUDA (GPU)   │
│  - Webcam via `camera`    │                     │  on localhost:5000   │
│  - HandControllerOverlay  │ ◀────────────────── │                      │
│    paints hand cursor     │  {x, y, confidence} │                      │
│    feeds pan events       │                     │                      │
│    into Flame game        │                     │                      │
└───────────────────────────┘                     └──────────────────────┘
```

The **Python backend you already have is not modified**. Your running
`start_server.bat` stays exactly as-is. Only the Flutter game changes.

---

## Prerequisites

- Python backend running at `http://localhost:5000` (you already have this ✓)
- Flutter SDK installed (you have this ✓)
- A webcam connected to your PC
- For Windows desktop build: Visual Studio Build Tools with "Desktop development with C++" workload (you have Visual Studio Build Tools 2019 ✓)

---

## Step 1: Add dependencies to `pubspec.yaml`

Open `pubspec.yaml` in the game's root and add these under `dependencies:`:

```yaml
dependencies:
  flutter:
    sdk: flutter
  # ... your existing packages (flame, etc.)
  camera: ^0.11.0
  http: ^1.2.0
```

Then in PowerShell, inside the game folder:

```powershell
flutter pub get
```

---

## Step 2: Add the two new files

Copy these two files (provided in the `flutter_integration/lib/` folder) into
your game's `lib/` directory, preserving the folder structure:

```
<game-root>/
  lib/
    services/
      hand_detection_service.dart    ← NEW
    widgets/
      hand_controller_overlay.dart   ← NEW
```

---

## Step 3: Find the game's gesture handler

The game uses Flame. Somewhere in `lib/` there will be a Flame game class that
handles swipes. It usually looks like one of these:

```dart
class FruitCuttingGame extends FlameGame with PanDetector {
  void onPanUpdate(DragUpdateInfo info) { ... }
}
```

or

```dart
class FruitCuttingGame extends FlameGame with HasDraggables {
  ...
}
```

**Find the `onPanUpdate` / `onDragUpdate` method** — this is where the game
turns finger-swipes into fruit-slicing. Let's call your game class
`FruitCuttingGame` (rename to match whatever yours is called).

---

## Step 4: Expose virtual pan events on the game class

Open your game class (probably `lib/game/fruit_cutting_game.dart` or similar)
and add these three methods at the bottom of the class:

```dart
// Virtual pan entrypoints for hand-tracking.
// Existing touch/mouse input still works; these just drive the same logic.

Vector2? _virtualHand;

void onVirtualPanStart(Vector2 position) {
  _virtualHand = position;
  // Call the same thing your touch handler calls.
  // If you have onPanStart(DragStartInfo info), the easiest way is to
  // build a fake DragStartInfo, but often just triggering your slice
  // logic directly is simpler. Adapt this to your game:
  //
  //   onPanStart(DragStartInfo.fromDetails(this, DragStartDetails(
  //     globalPosition: position.toOffset(),
  //     localPosition: position.toOffset(),
  //   )));
}

void onVirtualPanUpdate(Vector2 position) {
  if (_virtualHand != null) {
    final delta = position - _virtualHand!;
    _virtualHand = position;

    // If your game uses onPanUpdate(DragUpdateInfo info):
    //   final info = DragUpdateInfo.fromDetails(this, DragUpdateDetails(
    //     globalPosition: position.toOffset(),
    //     localPosition: position.toOffset(),
    //     delta: delta.toOffset(),
    //   ));
    //   onPanUpdate(info);

    // OR — simpler and more reliable — call your slicing logic directly:
    // Iterate through fruits and check collision with a line from
    // _virtualHand to position, like your pan handler already does.
  }
}

void onVirtualPanEnd() {
  _virtualHand = null;
}
```

**The cleanest integration**: find the method that checks "did this swipe hit a
fruit" and call it from `onVirtualPanUpdate` with the current position. That
way both touch and hand input share the same slicing logic.

If your existing touch handler already converts the global Offset through
`componentsAtPoint(...)` or similar, you can just pass the hand position in
identically.

---

## Step 5: Wrap the game widget with HandControllerOverlay

Find where `GameWidget(game: ...)` is created (usually in a screen widget
under `lib/screens/` or in `main.dart`). Wrap it like this:

```dart
import 'package:flutter/material.dart';
import 'package:flame/game.dart';
import '../widgets/hand_controller_overlay.dart';
// ...import your game class

class GameScreen extends StatefulWidget {
  const GameScreen({super.key});
  @override
  State<GameScreen> createState() => _GameScreenState();
}

class _GameScreenState extends State<GameScreen> {
  late final FruitCuttingGame _game;
  Offset? _lastHandPos;

  @override
  void initState() {
    super.initState();
    _game = FruitCuttingGame();
  }

  void _onHandMove(Offset? pos) {
    if (pos == null) {
      if (_lastHandPos != null) {
        _game.onVirtualPanEnd();
        _lastHandPos = null;
      }
      return;
    }

    final v = Vector2(pos.dx, pos.dy);
    if (_lastHandPos == null) {
      _game.onVirtualPanStart(v);
    } else {
      _game.onVirtualPanUpdate(v);
    }
    _lastHandPos = pos;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: HandControllerOverlay(
        backendUrl: 'http://localhost:5000',
        onHandMove: _onHandMove,
        showCameraPreview: true,  // small debug preview in the corner
        showHandCursor: true,
        mirror: true,              // front-facing webcams need mirroring
        child: GameWidget(game: _game),
      ),
    );
  }
}
```

Change the import for `Vector2` if your game uses it from Flame:
```dart
import 'package:flame/components.dart';
```

---

## Step 6: Windows permissions

Flutter desktop needs no manifest changes for camera access — Windows shows
the standard permission dialog the first time. Just allow it.

For `http://localhost` calls, no ATS/network config is needed on Windows.

---

## Step 7: Run it

Open PowerShell in the game's root folder and run:

```powershell
# One-time Flutter fixes (if you haven't already)
git config --global --add safe.directory E:/code/flutter

# Make sure the Python backend is running in another terminal window
# (i.e., start_server.bat is already running from the backend folder)

# Get packages
flutter pub get

# Run the game on Windows desktop
flutter run -d windows
```

Or on Chrome (sometimes easier for debugging):
```powershell
flutter run -d chrome
```

> **Chrome caveat**: the `camera` plugin on Flutter web works differently and
> `takePicture()` returns a blob URL. The overlay code uses `XFile.readAsBytes()`
> which works on both, so Chrome should work out of the box, just with slower
> frame capture.

---

## Step 8: Tune performance

Once it's running, adjust these knobs in `HandControllerOverlay`:

| Setting | Default | Effect |
|---------|---------|--------|
| `detectionInterval` | 120 ms | Lower = more responsive, more GPU load |
| `showCameraPreview` | false | Turn off to save a tiny bit of CPU |
| `imageSize` (in service) | 320 | Smaller = faster detection |

On your RTX 4080, you can push `detectionInterval` down to ~50 ms easily.

---

## Troubleshooting

### "Backend offline" banner
Your Python server isn't running. Open `start_server.bat` first.

### Camera opens but no hand detected
- Move closer to the webcam
- Make sure lighting is reasonable
- Open `http://localhost:5000/test` in a browser and verify detection works there first
- Try lowering `confidence_threshold` in `config.json` from 0.5 to 0.3

### Hand cursor appears but fruits don't get sliced
Your `onVirtualPanUpdate` isn't actually calling the game's slicing logic.
Look at the game's existing `onPanUpdate` method and replicate what it does.
The easiest test: add a print statement in `onVirtualPanUpdate` to confirm
it's being called, then mirror whatever the touch handler does.

### Mirror is wrong (moving left moves cursor right)
Toggle the `mirror:` parameter on `HandControllerOverlay`.

### Flutter says `camera` package won't build on Windows
Make sure you have Visual Studio Build Tools with C++ desktop workload.
You already have 2019 per your `flutter doctor` — should be fine.

### Android toolchain errors
You don't need Android for this. Stick with `flutter run -d windows` or
`flutter run -d chrome`.

### "Dubious ownership" git error again
```powershell
git config --global --add safe.directory E:/code/flutter
git config --global --add safe.directory "E:/code/fruit-ninja-yolo/Fruit-Cutting-Game-main"
```

---

## Quick Sanity Test (without touching the game code)

If you want to confirm the overlay works before modifying the game, try this
tiny test app:

```dart
// lib/main_test.dart
import 'package:flutter/material.dart';
import 'widgets/hand_controller_overlay.dart';

void main() => runApp(const MaterialApp(home: TestScreen()));

class TestScreen extends StatefulWidget {
  const TestScreen({super.key});
  @override
  State<TestScreen> createState() => _TestScreenState();
}

class _TestScreenState extends State<TestScreen> {
  Offset? _pos;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: HandControllerOverlay(
        showCameraPreview: true,
        onHandMove: (pos) => setState(() => _pos = pos),
        child: Container(
          color: Colors.black,
          alignment: Alignment.center,
          child: Text(
            _pos == null ? 'Move your hand' : 'Hand at $_pos',
            style: const TextStyle(color: Colors.white, fontSize: 24),
          ),
        ),
      ),
    );
  }
}
```

Run with:
```powershell
flutter run -d windows -t lib/main_test.dart
```

If the green cursor follows your hand → the overlay works and you can focus on
Step 4 (wiring pan events into the game's slicing logic).
