import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:openmouse/models/packet.dart';
import 'package:openmouse/services/connection_service.dart';

void main() {
  late ServerSocket server;
  final List<Socket> accepted = [];

  setUp(() async {
    server = await ServerSocket.bind(InternetAddress.loopbackIPv4, 0);
    server.listen(accepted.add);
  });

  tearDown(() async {
    for (final s in accepted) {
      s.destroy();
    }
    accepted.clear();
    await server.close();
  });

  test('connect usa el puerto UDP negociado, no la constante', () async {
    final service = ConnectionService();
    await service.connect('127.0.0.1', udpPort: 40404, tcpPort: server.port);
    expect(service.udpPort, 40404);
    expect(service.isConnected, isTrue);
    await service.dispose();
  });

  test('reconectar no deja sockets colgando', () async {
    final service = ConnectionService();
    await service.connect('127.0.0.1', tcpPort: server.port);
    // Un segundo connect() debe cerrar los sockets del primero.
    await service.connect('127.0.0.1', tcpPort: server.port);
    await service.connect('127.0.0.1', tcpPort: server.port);
    expect(service.isConnected, isTrue);
    await service.dispose();
  });

  test('sendTcp tras desconectar no lanza', () async {
    final service = ConnectionService();
    await service.connect('127.0.0.1', tcpPort: server.port);
    await service.disconnect();
    expect(() => service.sendTcp(Packet.doubleClick()), returnsNormally);
    expect(() => service.sendUdp(Packet.mouseMove(1, 1)), returnsNormally);
    await service.dispose();
  });

  test('dispose cierra el stream sin emitir sobre un controller cerrado',
      () async {
    final service = ConnectionService();
    await service.connect('127.0.0.1', tcpPort: server.port);
    final seen = <bool>[];
    service.connectionStream.listen(seen.add);
    await service.dispose();
    expect(() => service.sendTcp(Uint8List.fromList([0x12])), returnsNormally);
  });

  test('connect a un puerto cerrado propaga el error sin dejar estado sucio',
      () async {
    final service = ConnectionService();
    final closed = await ServerSocket.bind(InternetAddress.loopbackIPv4, 0);
    final port = closed.port;
    await closed.close();
    await expectLater(
      service.connect('127.0.0.1', tcpPort: port),
      throwsA(isA<SocketException>()),
    );
    expect(service.isConnected, isFalse);
    await service.dispose();
  });
}
