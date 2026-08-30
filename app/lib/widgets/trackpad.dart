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

  /// Muescas de rueda por pixel logico de dedo. Cada muesca son tres lineas en
  /// Windows, asi que 0.5 daba ~130 muescas por deslizamiento (unas 390 lineas)
  /// y el scroll se iba de las manos. 0.05 deja una muesca por cada ~20 px.
  static const double _scrollSensitivity = 0.05;
  double _scrollAccumulator = 0.0;
  // El residuo fraccionario del movimiento: redondear cada evento por separado
  // tiraba todo delta menor de 1 px, y un arrastre lento no movia el cursor.
  double _moveAccumulatorX = 0.0;
  double _moveAccumulatorY = 0.0;

  /// Un unico reconocedor de escala cubre ambos gestos: scale es un superset de
  /// pan, y declarar los dos en el mismo GestureDetector dispara una asercion.
  /// Un dedo mueve el cursor; dos dedos hacen scroll.
  void _onScaleStart(ScaleStartDetails details) {
    _scrollAccumulator = 0.0;
    _moveAccumulatorX = 0.0;
    _moveAccumulatorY = 0.0;
  }

  void _onScaleUpdate(ScaleUpdateDetails details) {
    if (details.pointerCount >= 2) {
      _accumulateScroll(details.focalPointDelta.dy);
      return;
    }
    _moveAccumulatorX += details.focalPointDelta.dx * _sensitivity;
    _moveAccumulatorY += details.focalPointDelta.dy * _sensitivity;
    final dx = _clampDelta(_moveAccumulatorX.truncateToDouble());
    final dy = _clampDelta(_moveAccumulatorY.truncateToDouble());
    if (dx != 0 || dy != 0) {
      _moveAccumulatorX -= dx;
      _moveAccumulatorY -= dy;
      widget.connectionService.sendUdp(Packet.mouseMove(dx, dy));
    }
  }

  /// dx/dy viajan como int16; un gesto muy rapido puede desbordarlos.
  static int _clampDelta(double value) {
    if (value.isNaN || value.isInfinite) return 0;
    return value.round().clamp(-32768, 32767);
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
    _accumulateScroll(details.delta.dy);
  }

  void _accumulateScroll(double deltaY) {
    _scrollAccumulator += deltaY * _scrollSensitivity;
    final scrollAmount = _scrollAccumulator.truncate();
    if (scrollAmount != 0) {
      // Se niega antes de acotar: -(-32768) volveria a salirse del int16.
      widget.connectionService.sendUdp(Packet.scroll(_clampDelta(-scrollAmount.toDouble())));
      _scrollAccumulator -= scrollAmount;
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
            onTap: _onTap,
            onDoubleTap: _onDoubleTap,
            onLongPress: _onLongPress,
            onScaleStart: _onScaleStart,
            onScaleUpdate: _onScaleUpdate,
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
