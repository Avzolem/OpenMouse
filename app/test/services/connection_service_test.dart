// app/test/services/connection_service_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:openmouse/services/connection_service.dart';

void main() {
  group('ConnectionService', () {
    test('initial state is disconnected', () {
      final service = ConnectionService();
      expect(service.isConnected, false);
    });

    test('serverIp is null when disconnected', () {
      final service = ConnectionService();
      expect(service.serverIp, null);
    });

    test('udpPort defaults to 19780', () {
      expect(ConnectionService.defaultUdpPort, 19780);
    });

    test('tcpPort defaults to 19781', () {
      expect(ConnectionService.defaultTcpPort, 19781);
    });
  });
}
