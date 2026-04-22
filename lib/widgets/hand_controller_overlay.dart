// lib/widgets/hand_controller_overlay.dart
//
// This widget wraps any game widget and provides hand-tracking
// "virtual touch" events. It captures webcam frames, sends them to
// the YOLO backend, and synthesizes pan/swipe gestures at the
// detected hand's screen position.
//
// How it works:
//   1. Opens the webcam using the `camera` package.
//   2. Every N ms, grabs a frame and POSTs it to /detect on the backend.
//   3. Maps the returned (x,y) hand-center into the widget's screen space.
//   4. Calls onHandMove(Offset) every time hand position updates.
//   5. Draws a glowing cursor at the hand's position.
//
// Your game screen should pass the hand Offset into the Flame game's
// gesture handlers (onPanStart / onPanUpdate / onPanEnd) to drive slicing.

import 'dart:async';
import 'dart:typed_data';

import 'package:camera/camera.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import '../services/hand_detection_service.dart';

typedef HandMoveCallback = void Function(Offset? screenPosition);

class HandControllerOverlay extends StatefulWidget {
  /// The child widget (your game) to wrap
  final Widget child;

  /// Called whenever hand position updates. Null means no hand detected.
  final HandMoveCallback? onHandMove;

  /// Backend URL
  final String backendUrl;

  /// How often to send frames to backend (lower = more responsive, more GPU load)
  final Duration detectionInterval;

  /// Whether to show the camera preview (debug) behind the game
  final bool showCameraPreview;

  /// Whether to show the hand cursor indicator
  final bool showHandCursor;

  /// Mirror X coordinates (useful for front-facing webcams)
  final bool mirror;

  const HandControllerOverlay({
    super.key,
    required this.child,
    this.onHandMove,
    this.backendUrl = 'http://localhost:5000',
    this.detectionInterval = const Duration(milliseconds: 120),
    this.showCameraPreview = false,
    this.showHandCursor = true,
    this.mirror = true,
  });

  @override
  State<HandControllerOverlay> createState() => _HandControllerOverlayState();
}

class _HandControllerOverlayState extends State<HandControllerOverlay> {
  CameraController? _cameraController;
  late HandDetectionService _service;
  Timer? _detectTimer;

  bool _cameraReady = false;
  bool _backendReady = false;
  String _statusText = 'Initializing...';

  Offset? _handScreenPos;
  final List<_TrailPoint> _trail = [];

  @override
  void initState() {
    super.initState();
    _service = HandDetectionService(baseUrl: widget.backendUrl);
    _initialize();
  }

  Future<void> _initialize() async {
    // Check backend
    setState(() => _statusText = 'Checking backend...');
    _backendReady = await _service.isHealthy();
    if (!_backendReady) {
      setState(() => _statusText =
          'Backend offline at ${widget.backendUrl}\n'
          'Make sure the Python server is running.');
      return;
    }

    // Initialize camera
    setState(() => _statusText = 'Requesting camera...');
    try {
      final cameras = await availableCameras();
      if (cameras.isEmpty) {
        setState(() => _statusText = 'No camera available');
        return;
      }

      // Prefer front camera
      final camera = cameras.firstWhere(
        (c) => c.lensDirection == CameraLensDirection.front,
        orElse: () => cameras.first,
      );

      _cameraController = CameraController(
        camera,
        ResolutionPreset.medium,
        enableAudio: false,
        imageFormatGroup: ImageFormatGroup.jpeg,
      );

      await _cameraController!.initialize();
      if (!mounted) return;

      setState(() {
        _cameraReady = true;
        _statusText = 'Ready';
      });

      _startDetectionLoop();
    } catch (e) {
      debugPrint('Camera init error: $e');
      setState(() => _statusText = 'Camera error: $e');
    }
  }

  void _startDetectionLoop() {
    _detectTimer?.cancel();
    _detectTimer = Timer.periodic(widget.detectionInterval, (_) async {
      if (!_cameraReady || _cameraController == null) return;
      if (!_cameraController!.value.isInitialized) return;

      try {
        // Take a snapshot frame
        final XFile file = await _cameraController!.takePicture();
        final Uint8List bytes = await file.readAsBytes();

        final previewSize = _cameraController!.value.previewSize;
        if (previewSize == null) return;

        final detection = await _service.detectFromJpegBytes(
          bytes,
          sourceWidth: previewSize.height.toInt(),
          sourceHeight: previewSize.width.toInt(),
        );

        if (!mounted) return;

        if (detection == null) {
          _updateHand(null);
        } else {
          // Map from image coordinates -> screen coordinates
          final RenderBox? box = context.findRenderObject() as RenderBox?;
          if (box == null || !box.hasSize) return;
          final Size widgetSize = box.size;

          double normX = detection.x / detection.imageWidth;
          final double normY = detection.y / detection.imageHeight;
          if (widget.mirror) normX = 1.0 - normX;

          final screenPos = Offset(
            normX * widgetSize.width,
            normY * widgetSize.height,
          );
          _updateHand(screenPos);
        }
      } catch (e) {
        debugPrint('Detection loop error: $e');
      }
    });
  }

  void _updateHand(Offset? pos) {
    setState(() {
      _handScreenPos = pos;
      if (pos != null) {
        _trail.add(_TrailPoint(pos, DateTime.now()));
        // Keep only recent points
        final cutoff = DateTime.now().subtract(const Duration(milliseconds: 400));
        _trail.removeWhere((p) => p.time.isBefore(cutoff));
      } else {
        _trail.clear();
      }
    });
    widget.onHandMove?.call(pos);
  }

  @override
  void dispose() {
    _detectTimer?.cancel();
    _cameraController?.dispose();
    _service.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Stack(
      fit: StackFit.expand,
      children: [
        // The game goes at the bottom
        widget.child,

        // Optional camera preview for debug
        if (widget.showCameraPreview && _cameraReady)
          Positioned(
            bottom: 12,
            right: 12,
            width: 160,
            height: 120,
            child: ClipRRect(
              borderRadius: BorderRadius.circular(8),
              child: Transform(
                alignment: Alignment.center,
                transform: widget.mirror
                    ? (Matrix4.identity()..scale(-1.0, 1.0, 1.0))
                    : Matrix4.identity(),
                child: CameraPreview(_cameraController!),
              ),
            ),
          ),

        // Hand trail + cursor overlay
        if (widget.showHandCursor)
          IgnorePointer(
            child: CustomPaint(
              painter: _HandCursorPainter(
                position: _handScreenPos,
                trail: _trail,
              ),
              size: Size.infinite,
            ),
          ),

        // Status banner while not ready
        if (!_cameraReady || !_backendReady)
          Positioned(
            top: 12,
            left: 12,
            right: 12,
            child: Material(
              color: Colors.black.withValues(alpha: 0.7),
              borderRadius: BorderRadius.circular(8),
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Text(
                  'Hand Controller: $_statusText',
                  style: const TextStyle(color: Colors.white),
                ),
              ),
            ),
          ),
      ],
    );
  }
}

class _TrailPoint {
  final Offset position;
  final DateTime time;
  _TrailPoint(this.position, this.time);
}

class _HandCursorPainter extends CustomPainter {
  final Offset? position;
  final List<_TrailPoint> trail;

  _HandCursorPainter({required this.position, required this.trail});

  @override
  void paint(Canvas canvas, Size size) {
    // Draw trail
    if (trail.length >= 2) {
      final now = DateTime.now();
      for (int i = 1; i < trail.length; i++) {
        final age = now.difference(trail[i].time).inMilliseconds / 400.0;
        final alpha = (1.0 - age).clamp(0.0, 1.0);

        final paint = Paint()
          ..color = Colors.cyanAccent.withValues(alpha: alpha * 0.8)
          ..strokeWidth = 6 + (12 * alpha)
          ..strokeCap = StrokeCap.round
          ..style = PaintingStyle.stroke;

        canvas.drawLine(trail[i - 1].position, trail[i].position, paint);

        final glowPaint = Paint()
          ..color = Colors.cyan.withValues(alpha: alpha * 0.3)
          ..strokeWidth = 20 + (16 * alpha)
          ..strokeCap = StrokeCap.round
          ..style = PaintingStyle.stroke;

        canvas.drawLine(trail[i - 1].position, trail[i].position, glowPaint);
      }
    }

    // Draw current hand cursor
    if (position != null) {
      final outer = Paint()
        ..color = Colors.greenAccent.withValues(alpha: 0.3)
        ..style = PaintingStyle.fill;
      canvas.drawCircle(position!, 30, outer);

      final inner = Paint()
        ..color = Colors.greenAccent
        ..style = PaintingStyle.stroke
        ..strokeWidth = 3;
      canvas.drawCircle(position!, 24, inner);

      final dot = Paint()..color = Colors.white;
      canvas.drawCircle(position!, 4, dot);
    }
  }

  @override
  bool shouldRepaint(covariant _HandCursorPainter old) => true;
}
