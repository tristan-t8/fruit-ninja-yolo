# Flutter Integration Guide

How to integrate the Fruit Ninja YOLO Backend with your Flutter app.

## Add Dependencies

In `pubspec.yaml`:

```yaml
dependencies:
  http: ^1.1.0
  camera: ^0.10.0
```

## Create Backend Service

Create `lib/services/backend_service.dart`:

```dart
import 'dart:convert';
import 'dart:typed_data';
import 'package:http/http.dart' as http;

class BackendService {
  static const String BASE_URL = 'http://localhost:5000';
  static const Duration TIMEOUT = Duration(seconds: 30);

  final http.Client _httpClient = http.Client();

  // Check server health
  Future<bool> isHealthy() async {
    try {
      final response = await _httpClient
          .get(Uri.parse('$BASE_URL/health'))
          .timeout(TIMEOUT);
      return response.statusCode == 200;
    } catch (e) {
      print('Health check error: $e');
      return false;
    }
  }

  // Get model information
  Future<Map<String, dynamic>?> getModelInfo() async {
    try {
      final response = await _httpClient
          .get(Uri.parse('$BASE_URL/model-info'))
          .timeout(TIMEOUT);

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }
      return null;
    } catch (e) {
      print('Model info error: $e');
      return null;
    }
  }

  // Detect hands in image
  Future<DetectionResult?> detectHand(Uint8List imageBytes) async {
    try {
      String base64Image = base64Encode(imageBytes);

      final response = await _httpClient
          .post(
            Uri.parse('$BASE_URL/detect'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({'image': base64Image}),
          )
          .timeout(TIMEOUT);

      if (response.statusCode == 200) {
        return DetectionResult.fromJson(jsonDecode(response.body));
      }
      return null;
    } catch (e) {
      print('Detection error: $e');
      return null;
    }
  }

  // Process fruit slicing
  Future<SliceResult?> sliceFruit(
    Uint8List imageBytes, {
    List<dynamic>? handHistory,
  }) async {
    try {
      String base64Image = base64Encode(imageBytes);

      final response = await _httpClient
          .post(
            Uri.parse('$BASE_URL/slice'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({
              'image': base64Image,
              'hand_history': handHistory ?? [],
            }),
          )
          .timeout(TIMEOUT);

      if (response.statusCode == 200) {
        return SliceResult.fromJson(jsonDecode(response.body));
      }
      return null;
    } catch (e) {
      print('Slicing error: $e');
      return null;
    }
  }

  // Reset GPU cache
  Future<bool> resetDevice() async {
    try {
      final response = await _httpClient
          .post(Uri.parse('$BASE_URL/reset-device'))
          .timeout(TIMEOUT);
      return response.statusCode == 200;
    } catch (e) {
      print('Reset device error: $e');
      return false;
    }
  }

  void dispose() {
    _httpClient.close();
  }
}

// Data Models

class DetectionResult {
  final List<Detection> detections;
  final String image;
  final String device;

  DetectionResult({
    required this.detections,
    required this.image,
    required this.device,
  });

  factory DetectionResult.fromJson(Map<String, dynamic> json) {
    return DetectionResult(
      detections: (json['detections'] as List)
          .map((d) => Detection.fromJson(d))
          .toList(),
      image: json['image'] ?? '',
      device: json['device'] ?? 'unknown',
    );
  }
}

class Detection {
  final List<int> bbox;
  final double confidence;
  final String className;
  final List<int> center;

  Detection({
    required this.bbox,
    required this.confidence,
    required this.className,
    required this.center,
  });

  factory Detection.fromJson(Map<String, dynamic> json) {
    return Detection(
      bbox: List<int>.from(json['bbox']),
      confidence: (json['confidence'] as num).toDouble(),
      className: json['class_name'] ?? '',
      center: List<int>.from(json['center']),
    );
  }
}

class SliceResult {
  final bool sliced;
  final List<AffectedFruit> affectedFruits;
  final HandMotion? handMotion;
  final double confidence;
  final String image;

  SliceResult({
    required this.sliced,
    required this.affectedFruits,
    required this.handMotion,
    required this.confidence,
    required this.image,
  });

  factory SliceResult.fromJson(Map<String, dynamic> json) {
    return SliceResult(
      sliced: json['sliced'] ?? false,
      affectedFruits: (json['affected_fruits'] as List? ?? [])
          .map((f) => AffectedFruit.fromJson(f))
          .toList(),
      handMotion: json['hand_motion'] != null
          ? HandMotion.fromJson(json['hand_motion'])
          : null,
      confidence: (json['confidence'] ?? 0.0).toDouble(),
      image: json['image'] ?? '',
    );
  }
}

class AffectedFruit {
  final String type;
  final List<int> position;
  final double confidence;

  AffectedFruit({
    required this.type,
    required this.position,
    required this.confidence,
  });

  factory AffectedFruit.fromJson(Map<String, dynamic> json) {
    return AffectedFruit(
      type: json['type'] ?? '',
      position: List<int>.from(json['position']),
      confidence: (json['confidence'] ?? 0.0).toDouble(),
    );
  }
}

class HandMotion {
  final bool isSlicing;
  final double velocity;
  final double motionDistance;
  final double trajectorySmoothness;

  HandMotion({
    required this.isSlicing,
    required this.velocity,
    required this.motionDistance,
    required this.trajectorySmoothness,
  });

  factory HandMotion.fromJson(Map<String, dynamic> json) {
    return HandMotion(
      isSlicing: json['is_slicing'] ?? false,
      velocity: (json['velocity'] ?? 0.0).toDouble(),
      motionDistance: (json['motion_distance'] ?? 0.0).toDouble(),
      trajectorySmoothness: (json['trajectory_smoothness'] ?? 0.0).toDouble(),
    );
  }
}
```

## Usage Example

```dart
import 'package:flutter/material.dart';
import 'services/backend_service.dart';

class GameScreen extends StatefulWidget {
  @override
  _GameScreenState createState() => _GameScreenState();
}

class _GameScreenState extends State<GameScreen> {
  final BackendService _backendService = BackendService();
  List<dynamic> _handHistory = [];

  @override
  void initState() {
    super.initState();
    _checkBackend();
  }

  Future<void> _checkBackend() async {
    bool healthy = await _backendService.isHealthy();
    if (!healthy) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Backend server not available')),
      );
    }
  }

  Future<void> _processFrame(Uint8List imageBytes) async {
    try {
      // Detect hands
      final detection = await _backendService.detectHand(imageBytes);
      if (detection == null) return;

      // Process slicing
      final sliceResult = await _backendService.sliceFruit(
        imageBytes,
        handHistory: _handHistory,
      );

      if (sliceResult?.sliced == true) {
        // Handle fruit slicing
        print('Cut ${sliceResult!.affectedFruits.length} fruits');
        // Add score, play animation, etc.
      }

      // Update hand history
      _handHistory.add(detection.detections);
      if (_handHistory.length > 5) {
        _handHistory.removeAt(0);
      }
    } catch (e) {
      print('Frame processing error: $e');
    }
  }

  @override
  void dispose() {
    _backendService.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Fruit Ninja with YOLO')),
      body: Center(
        child: Text('Game Screen'),
      ),
    );
  }
}
```

## Android Permissions

Add to `android/app/src/main/AndroidManifest.xml`:

```xml
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.CAMERA" />

<application
    android:usesCleartextTraffic="true"
    ...>
```

## iOS Permissions

Add to `ios/Runner/Info.plist`:

```xml
<key>NSLocalNetworkUsageDescription</key>
<string>This app needs local network access for the YOLO backend</string>
<key>NSCameraUsageDescription</key>
<string>This app needs camera access for hand detection</string>
<key>NSAppTransportSecurity</key>
<dict>
    <key>NSAllowsArbitraryLoads</key>
    <true/>
</dict>
```

## Production Configuration

For remote server:
```dart
class BackendService {
  static const String BASE_URL = 'https://your-server.com:5000';
}
```

## Testing Connection

```dart
void testBackend() async {
  final service = BackendService();

  bool healthy = await service.isHealthy();
  print('Backend healthy: $healthy');

  final info = await service.getModelInfo();
  print('Model info: $info');

  service.dispose();
}
```
