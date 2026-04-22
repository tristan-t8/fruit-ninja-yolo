/*
 * @ Author: Flutter Journey 🎯 <flutterjourney.org@gmail.com>
 * @ Created: 2024-12-09 13:15:47
 * @ Message: You look very hardworking 👨‍💻. Keep focusing on your goals. 🌤️
 */

import 'dart:math';
import 'package:flame/components.dart';
import 'package:flutter/material.dart';
import 'package:fruit_cutting_game/core/configs/theme/app_colors.dart';

class SliceTrailComponent extends Component {
  final List<Vector2> trailPoints = [];
  final Paint paint = Paint()
    ..color = AppColors.white
    ..strokeWidth = 7
    ..style = PaintingStyle.stroke;
  final Random random = Random();

  @override
  void render(Canvas canvas) {
    if (trailPoints.length > 1) {
      for (int i = 0; i < trailPoints.length - 1; i++) {
        canvas.drawLine(trailPoints[i].toOffset(), trailPoints[i + 1].toOffset(), paint);
      }
    }
  }

  void addPoint(Vector2 point) {
    trailPoints.add(point);
    if (trailPoints.length > 10) {
      trailPoints.removeAt(0); // Limit trail length for a smoother effect
    }
  }

  void clear() {
    trailPoints.clear();
  }

  void changeColor() {
    paint.color = Color.fromRGBO(
      random.nextInt(256),
      random.nextInt(256),
      random.nextInt(256),
      1.0,
    );
  }
}
