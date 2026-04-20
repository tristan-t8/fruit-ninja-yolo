/*
 * @ Author: Flutter Journey 🎯 <flutterjourney.org@gmail.com>
 * @ Created: 2024-12-09 13:15:47
 * @ Message: You look very hardworking 👨‍💻. Keep focusing on your goals. 🌤️
 */

import 'package:flutter/material.dart';

class FruitModel {
  String image;
  Color color;
  bool isBomb;

  FruitModel({
    required this.image,
    this.color = Colors.transparent,
    this.isBomb = false,
  });
}
