import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:openmouse/services/connection_service.dart';
import 'package:openmouse/widgets/trackpad.dart';

void main() {
  testWidgets('Trackpad se construye sin lanzar', (tester) async {
    await tester.pumpWidget(MaterialApp(
      home: Scaffold(body: Trackpad(connectionService: ConnectionService())),
    ));
    expect(find.byType(Trackpad), findsOneWidget);
  });
}
