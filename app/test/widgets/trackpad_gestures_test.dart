import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:openmouse/services/connection_service.dart';
import 'package:openmouse/widgets/trackpad.dart';

/// Captura los paquetes en vez de mandarlos por la red.
class _SpyConnection extends ConnectionService {
  final List<Uint8List> udp = [];
  final List<Uint8List> tcp = [];

  @override
  void sendUdp(Uint8List data) => udp.add(data);

  @override
  void sendTcp(Uint8List data) => tcp.add(data);

  List<int> get udpTypes => udp.map((p) => p[0]).toList();
  List<int> get tcpTypes => tcp.map((p) => p[0]).toList();
}

const int kMouseMove = 0x01;
const int kScroll = 0x02;

Future<void> _pump(WidgetTester tester, _SpyConnection spy) async {
  await tester.pumpWidget(MaterialApp(
    home: Scaffold(body: Trackpad(connectionService: spy)),
  ));
}

void main() {
  testWidgets('un dedo mueve el cursor y no hace scroll', (tester) async {
    final spy = _SpyConnection();
    await _pump(tester, spy);

    final area = tester.getCenter(find.byIcon(Icons.touch_app));
    final finger = await tester.startGesture(area);
    for (var i = 0; i < 10; i++) {
      await finger.moveBy(const Offset(6, 4));
      await tester.pump();
    }
    await finger.up();
    await tester.pumpAndSettle();

    expect(spy.udpTypes, contains(kMouseMove));
    expect(spy.udpTypes, isNot(contains(kScroll)));
  });

  testWidgets('dos dedos hacen scroll y no mueven el cursor', (tester) async {
    final spy = _SpyConnection();
    await _pump(tester, spy);

    final area = tester.getCenter(find.byIcon(Icons.touch_app));
    final first = await tester.startGesture(area - const Offset(30, 0));
    final second = await tester.startGesture(area + const Offset(30, 0));
    await tester.pump();

    // Ambos dedos bajan a la vez: el punto focal se desplaza, la escala no.
    for (var i = 0; i < 40; i++) {
      await first.moveBy(const Offset(0, 8));
      await second.moveBy(const Offset(0, 8));
      await tester.pump();
    }
    await first.up();
    await second.up();
    await tester.pumpAndSettle();

    expect(spy.udpTypes, contains(kScroll));
    expect(spy.udpTypes, isNot(contains(kMouseMove)));
  });

  testWidgets('la franja lateral hace scroll', (tester) async {
    final spy = _SpyConnection();
    await _pump(tester, spy);

    final strip = tester.getCenter(find.byIcon(Icons.unfold_more));
    await tester.dragFrom(strip, const Offset(0, 400));
    await tester.pumpAndSettle();

    expect(spy.udpTypes, contains(kScroll));
  });
}
