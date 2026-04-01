// app/lib/widgets/trackpad.dart
import 'package:flutter/material.dart';
import 'package:openmouse/models/packet.dart';
import 'package:openmouse/services/connection_service.dart';

class Trackpad extends StatefulWidget {
  final ConnectionService connectionService;

  const Trackpad({super.key, required this.connectionService});

  @override
  State<Trackpad> createState() => _TrackpadState();
}

class _TrackpadState extends State<Trackpad> {
  static const double _sensitivity = 1.5;
  static const double _scrollSensitivity = 0.5;
  double _scrollAccumulator = 0.0;

  void _onPanUpdate(DragUpdateDetails details) {
    final dx = (details.delta.dx * _sensitivity).round();
    final dy = (details.delta.dy * _sensitivity).round();
    if (dx != 0 || dy != 0) {
      widget.connectionService.sendUdp(Packet.mouseMove(dx, dy));
    }
  }

  void _onTap() {
    widget.connectionService.sendTcp(Packet.leftClick(2));
  }

  void _onDoubleTap() {
    widget.connectionService.sendTcp(Packet.doubleClick());
  }

  void _onLongPress() {
    widget.connectionService.sendTcp(Packet.rightClick(2));
  }

  void _onScrollUpdate(DragUpdateDetails details) {
    _scrollAccumulator += details.delta.dy * _scrollSensitivity;
    final scrollAmount = _scrollAccumulator.truncate();
    if (scrollAmount != 0) {
      widget.connectionService.sendUdp(Packet.scroll(-scrollAmount));
      _scrollAccumulator -= scrollAmount;
    }
  }

  void _onTwoFingerScroll(ScaleUpdateDetails details) {
    if (details.pointerCount < 2) return;
    final dy = (details.focalPointDelta.dy * _scrollSensitivity).round();
    if (dy != 0) {
      widget.connectionService.sendUdp(Packet.scroll(-dy));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        // Trackpad area (85%)
        Expanded(
          flex: 85,
          child: GestureDetector(
            onPanUpdate: _onPanUpdate,
            onTap: _onTap,
            onDoubleTap: _onDoubleTap,
            onLongPress: _onLongPress,
            onScaleUpdate: _onTwoFingerScroll,
            child: Container(
              decoration: BoxDecoration(
                color: const Color(0xFF16213E),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Center(
                child: Icon(
                  Icons.touch_app,
                  size: 48,
                  color: Colors.grey[700],
                ),
              ),
            ),
          ),
        ),
        const SizedBox(width: 8),
        // Scroll bar (15%)
        Expanded(
          flex: 15,
          child: GestureDetector(
            onVerticalDragUpdate: _onScrollUpdate,
            child: Container(
              decoration: BoxDecoration(
                color: const Color(0xFF0F3460),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.keyboard_arrow_up, color: Colors.grey[500]),
                  const SizedBox(height: 8),
                  Icon(Icons.unfold_more, color: Colors.grey[500], size: 32),
                  const SizedBox(height: 8),
                  Icon(Icons.keyboard_arrow_down, color: Colors.grey[500]),
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }
}
