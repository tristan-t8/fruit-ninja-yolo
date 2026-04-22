// lib/services/hand_detection_service.dart
// Service that talks to the Python YOLO backend

import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

/// Result of a single hand detection
class HandDetection {
  final double x;          // Hand center X (in image coordinates)
  final double y;          // Hand center Y (in image coordinates)
  final double confidence; // Detection confidence 0-1
  final int imageWidth;    // Width of the image sent
  final int imageHeight;   // Height of the image sent

  HandDetection({
    required this.x,
    required this.y,
    required this.confidence,
    required this.imageWidth,
    required this.imageHeight,
  });
}

/// Service that communicates with the Flask/YOLO backend
class HandDetectionService {
  /// URL of the backend server.
  /// - For desktop/web on same machine: http://localhost:5000
  /// - For Android emulator: http://10.0.2.2:5000
  /// - For real device on same WiFi: http://YOUR_PC_IP:5000 (e.g., http://192.168.1.14:5000)
  final String baseUrl;

  /// Image size to send to backend (smaller = faster)
  final int imageSize;

  /// JPEG quality 0-100 (lower = faster, less accurate)
  final int jpegQuality;

  final http.Client _client = http.Client();
  bool _busy = false;

  HandDetectionService({
    this.baseUrl = 'http://localhost:5000',
    this.imageSize = 320,
    this.jpegQuality = 60,
  });

  /// Check if backend is reachable and healthy
  Future<bool> isHealthy() async {
    try {
      final response = await _client
          .get(Uri.parse('$baseUrl/health'))
          .timeout(const Duration(seconds: 3));
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return data['status'] == 'healthy' && data['models_loaded'] == true;
      }
      return false;
    } catch (e) {
      debugPrint('HandDetectionService health check failed: $e');
      return false;
    }
  }

  /// Detect the primary (most confident) hand in a JPEG byte array.
  /// Returns null if no hand detected, backend down, or error.
  /// Automatically drops frames if a previous request is still in flight.
  Future<HandDetection?> detectFromJpegBytes(
    Uint8List jpegBytes, {
    required int sourceWidth,
    required int sourceHeight,
  }) async {
    if (_busy) return null; // drop frame
    _busy = true;

    try {
      final base64Image = base64Encode(jpegBytes);

      final response = await _client
          .post(
            Uri.parse('$baseUrl/detect'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({'image': base64Image}),
          )
          .timeout(const Duration(seconds: 3));

      if (response.statusCode != 200) return null;

      final data = jsonDecode(response.body);
      final detections = data['detections'] as List?;
      if (detections == null || detections.isEmpty) return null;

      // Pick most confident detection
      Map<String, dynamic>? best;
      double bestConf = 0;
      for (final d in detections) {
        final conf = (d['confidence'] as num).toDouble();
        if (conf > bestConf) {
          bestConf = conf;
          best = d as Map<String, dynamic>;
        }
      }
      if (best == null) return null;

      final center = best['center'] as List;
      return HandDetection(
        x: (center[0] as num).toDouble(),
        y: (center[1] as num).toDouble(),
        confidence: bestConf,
        imageWidth: sourceWidth,
        imageHeight: sourceHeight,
      );
    } catch (e) {
      debugPrint('HandDetectionService.detect error: $e');
      return null;
    } finally {
      _busy = false;
    }
  }

  /// Convert a ui.Image to JPEG bytes (helper for camera frame capture)
  static Future<Uint8List?> imageToJpegBytes(ui.Image image) async {
    final byteData =
        await image.toByteData(format: ui.ImageByteFormat.png);
    return byteData?.buffer.asUint8List();
  }

  void dispose() {
    _client.close();
  }
}
