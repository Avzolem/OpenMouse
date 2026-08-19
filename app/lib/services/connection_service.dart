// app/lib/services/connection_service.dart
import 'dart:async';
import 'dart:io';
import 'dart:typed_data';
import 'package:openmouse/models/packet.dart';

class ConnectionService {
  static const int defaultUdpPort = 19780;
  static const int defaultTcpPort = 19781;
  static const Duration reconnectInterval = Duration(seconds: 2);

  RawDatagramSocket? _udpSocket;
  Socket? _tcpSocket;
  String? _serverIp;
  // Direccion ya resuelta: el descubrimiento mDNS puede devolver un hostname, y
  // construir InternetAddress con uno lanza. Ademas evita reconstruirla en cada
  // paquete de movimiento, que salen a 60-100 Hz.
  InternetAddress? _serverAddress;
  int _udpPort = defaultUdpPort;
  int _tcpPort = defaultTcpPort;
  bool _connected = false;
  bool _disposed = false;
  Timer? _reconnectTimer;
  bool _reconnecting = false;
  // Cada connect()/disconnect() abre una generacion nueva. Un intento en vuelo
  // que termine despues de que el usuario haya pulsado Desconectar pertenece a
  // una generacion vieja y debe recoger sus sockets en vez de revivir.
  int _generation = 0;

  final StreamController<bool> _connectionController =
      StreamController<bool>.broadcast();

  Stream<bool> get connectionStream => _connectionController.stream;
  bool get isConnected => _connected;
  String? get serverIp => _serverIp;
  int get udpPort => _udpPort;
  int get tcpPort => _tcpPort;

  Future<void> connect(String ip,
      {int udpPort = defaultUdpPort, int tcpPort = defaultTcpPort}) async {
    // La generacion se toma antes del primer await: si se captura despues, un
    // disconnect() que ocurra mientras tanto queda pisado por este mismo
    // connect y la conexion revive.
    final generation = ++_generation;
    // Soltar cualquier socket anterior: reconectar sin cerrarlos los filtraba.
    await _closeSockets();

    final socket = await Socket.connect(ip, tcpPort,
        timeout: const Duration(seconds: 5));
    final udp = await RawDatagramSocket.bind(InternetAddress.anyIPv4, 0);

    if (generation != _generation || _disposed) {
      // Alguien desconecto o reconecto mientras abriamos: esto ya no vale.
      socket.destroy();
      udp.close();
      return;
    }

    _serverIp = ip;
    _serverAddress = socket.remoteAddress;
    _udpPort = udpPort;
    _tcpPort = tcpPort;
    _tcpSocket = socket;
    _udpSocket = udp;

    socket.listen(
      (_) {},
      onError: (_) => _handleDisconnect(socket),
      onDone: () => _handleDisconnect(socket),
      cancelOnError: true,
    );

    _connected = true;
    _emit(true);
  }

  void sendUdp(Uint8List data) {
    final socket = _udpSocket;
    final address = _serverAddress;
    if (socket == null || address == null) return;
    try {
      socket.send(data, address, _udpPort);
    } on SocketException {
      // Datagrama perdido: el canal UDP es best-effort por diseno.
    }
  }

  void sendTcp(Uint8List data) {
    final socket = _tcpSocket;
    if (socket == null || !_connected) return;
    try {
      socket.add(Packet.wrapTcp(data));
    } on SocketException {
      _handleDisconnect(socket);
    } on StateError {
      // El socket se cerro entre la comprobacion y el add.
      _handleDisconnect(socket);
    }
  }

  void _emit(bool value) {
    if (!_disposed && !_connectionController.isClosed) {
      _connectionController.add(value);
    }
  }

  /// [source] identifica el socket que reporta el fallo: onError y onDone
  /// pueden dispararse ambos, y un socket ya sustituido no debe tumbar la
  /// conexion nueva.
  void _handleDisconnect(Socket source) {
    if (_disposed) return;
    if (!identical(source, _tcpSocket)) return;
    if (!_connected) return;
    _connected = false;
    _emit(false);
    _startReconnect();
  }

  void _startReconnect() {
    if (_disposed || _reconnectTimer != null) return;
    _reconnectTimer = Timer.periodic(reconnectInterval, (timer) async {
      // Sin este guardia, un connect() mas lento que el intervalo lanzaria
      // intentos solapados.
      if (_reconnecting || _disposed) return;
      final ip = _serverIp;
      if (ip == null) return;
      _reconnecting = true;
      try {
        await connect(ip, udpPort: _udpPort, tcpPort: _tcpPort);
        timer.cancel();
        _reconnectTimer = null;
      } catch (_) {
        // Se reintenta en el siguiente tick.
      } finally {
        _reconnecting = false;
      }
    });
  }

  Future<void> _closeSockets() async {
    final tcp = _tcpSocket;
    _tcpSocket = null;
    _udpSocket?.close();
    _udpSocket = null;
    if (tcp != null) {
      tcp.destroy();
    }
  }

  Future<void> disconnect() async {
    _generation++;
    _reconnectTimer?.cancel();
    _reconnectTimer = null;
    await _closeSockets();
    _connected = false;
    _serverIp = null;
    _serverAddress = null;
    _emit(false);
  }

  Future<void> dispose() async {
    // disconnect() emite en el stream, asi que hay que esperarlo antes de
    // cerrar el controller.
    await disconnect();
    _disposed = true;
    await _connectionController.close();
  }
}
