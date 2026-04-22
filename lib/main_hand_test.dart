// lib/main_hand_test.dart
// Standalone test app - verifies hand tracking works end-to-end
// before you modify the real game.
//
// Run with:
//   flutter run -d windows -t lib/main_hand_test.dart
//   flutter run -d chrome  -t lib/main_hand_test.dart

import 'package:flutter/material.dart';
import 'widgets/hand_controller_overlay.dart';

void main() {
  runApp(const HandTestApp());
}

class HandTestApp extends StatelessWidget {
  const HandTestApp({super.key});
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Hand Tracking Test',
      debugShowCheckedModeBanner: false,
      theme: ThemeData.dark(),
      home: const TestScreen(),
    );
  }
}

class TestScreen extends StatefulWidget {
  const TestScreen({super.key});
  @override
  State<TestScreen> createState() => _TestScreenState();
}

class _TestScreenState extends State<TestScreen> {
  Offset? _handPos;
  int _updateCount = 0;

  // Simple targets to "hit" with the hand
  final List<_Target> _targets = List.generate(
    6,
    (i) => _Target(
      Offset(100.0 + (i % 3) * 200, 150.0 + (i ~/ 3) * 250),
      40,
    ),
  );
  Offset? _lastHand;

  void _onHand(Offset? pos) {
    setState(() {
      _handPos = pos;
      _updateCount++;

      if (pos != null && _lastHand != null) {
        // Swipe hit-test: treat last→current as a line
        for (final t in _targets) {
          if (t.hit) continue;
          if (_lineCircleIntersects(_lastHand!, pos, t.center, t.radius)) {
            t.hit = true;
          }
        }
      }
      _lastHand = pos;
    });
  }

  bool _lineCircleIntersects(Offset a, Offset b, Offset c, double r) {
    final dx = b.dx - a.dx;
    final dy = b.dy - a.dy;
    final lenSq = dx * dx + dy * dy;
    if (lenSq == 0) {
      return (a - c).distance <= r;
    }
    double t = ((c.dx - a.dx) * dx + (c.dy - a.dy) * dy) / lenSq;
    t = t.clamp(0.0, 1.0);
    final closest = Offset(a.dx + dx * t, a.dy + dy * t);
    return (closest - c).distance <= r;
  }

  void _reset() {
    setState(() {
      for (final t in _targets) {
        t.hit = false;
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final hitCount = _targets.where((t) => t.hit).length;

    return Scaffold(
      body: HandControllerOverlay(
        backendUrl: 'http://localhost:5000',
        showCameraPreview: true,
        showHandCursor: true,
        mirror: true,
        onHandMove: _onHand,
        child: Stack(
          children: [
            // Dark gradient background
            Container(
              decoration: const BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [Color(0xFF1a1a2e), Color(0xFF0f0f1e)],
                ),
              ),
            ),

            // Targets
            CustomPaint(
              size: Size.infinite,
              painter: _TargetsPainter(_targets),
            ),

            // Info panel
            Positioned(
              top: 80,
              left: 16,
              child: Material(
                color: Colors.black54,
                borderRadius: BorderRadius.circular(8),
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Text('Hand Tracking Test',
                          style: TextStyle(
                              fontSize: 18, fontWeight: FontWeight.bold)),
                      const SizedBox(height: 8),
                      Text('Updates: $_updateCount'),
                      Text('Hand: ${_handPos ?? "not detected"}'),
                      Text('Targets hit: $hitCount / ${_targets.length}'),
                    ],
                  ),
                ),
              ),
            ),

            // Reset button
            Positioned(
              bottom: 16,
              left: 16,
              child: FilledButton.icon(
                onPressed: _reset,
                icon: const Icon(Icons.refresh),
                label: const Text('Reset targets'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _Target {
  final Offset center;
  final double radius;
  bool hit = false;
  _Target(this.center, this.radius);
}

class _TargetsPainter extends CustomPainter {
  final List<_Target> targets;
  _TargetsPainter(this.targets);

  @override
  void paint(Canvas canvas, Size size) {
    for (final t in targets) {
      final paint = Paint()
        ..color = t.hit ? Colors.greenAccent : Colors.redAccent
        ..style = PaintingStyle.fill;
      canvas.drawCircle(t.center, t.radius, paint);

      final border = Paint()
        ..color = Colors.white
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2;
      canvas.drawCircle(t.center, t.radius, border);
    }
  }

  @override
  bool shouldRepaint(covariant _TargetsPainter old) =>
      old.targets != targets;
}
