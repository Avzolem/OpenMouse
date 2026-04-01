// app/lib/services/connection_service.dart
import 'dart:async';
import 'dart:io';
import 'dart:typed_data';
import 'package:openmouse/models/packet.dart';

class ConnectionService {
  static const int defaultUdpPort = 19780;
  static const int defaultTcpPort = 19781;

  RawDatagramSocket? _udpSocket;
  Socket? _tcpSocket;
  String? _serverIp;
  bool _connected = false;
  Timer? _reconnectTimer;

  final StreamController<bool> _connectionController =
      StreamController<bool>.broadcast();

  Stream<bool> get connectionStream => _connectionController.stream;
  bool get isConnected => _connected;
  String? get serverIp => _serverIp;

  Future<void> connect(String ip,
      {int udpPort = defaultUdpPort, int tcpPort = defaultTcpPort}) async {
    _serverIp = ip;

    _udpSocket = await RawDatagramSocket.bind(InternetAddress.anyIPv4, 0);

    _tcpSocket = await Socket.connect(ip, tcpPort);
    _tcpSocket!.listen(
      (_) {},
      onError: (_) => _handleDisconnect(),
      onDone: _handleDisconnect,
    );

    _connected = true;
    _connectionController.add(true);
  }

  void sendUdp(Uint8List data) {
    if (_udpSocket != null && _serverIp != null) {
      _udpSocket!.send(data, InternetAddress(_serverIp!), defaultUdpPort);
    }
  }

  void sendTcp(Uint8List data) {
    if (_tcpSocket != null) {
      _tcpSocket!.add(Packet.wrapTcp(data));
    }
  }

  void _handleDisconnect() {
    _connected = false;
    _connectionController.add(false);
    _startReconnect();
  }

  void _startReconnect() {
    _reconnectTimer?.cancel();
    _reconnectTimer = Timer.periodic(const Duration(seconds: 2), (_) async {
      if (_serverIp == null) return;
      try {
        await connect(_serverIp!);
        _reconnectTimer?.cancel();
      } catch (_) {
        // Will retry on next tick
      }
    });
  }

  Future<void> disconnect() async {
    _reconnectTimer?.cancel();
    _tcpSocket?.destroy();
    _udpSocket?.close();
    _tcpSocket = null;
    _udpSocket = null;
    _connected = false;
    _serverIp = null;
    _connectionController.add(false);
  }

  void dispose() {
    disconnect();
    _connectionController.close();
  }
}
