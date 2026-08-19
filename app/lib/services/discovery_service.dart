// app/lib/services/discovery_service.dart
import 'dart:async';
import 'package:bonsoir/bonsoir.dart';

class DiscoveredServer {
  final String name;
  final String ip;
  final int tcpPort;
  final int udpPort;

  DiscoveredServer({
    required this.name,
    required this.ip,
    required this.tcpPort,
    required this.udpPort,
  });
}

class DiscoveryService {
  static const String serviceType = '_openmouse._tcp';

  BonsoirDiscovery? _discovery;
  StreamSubscription? _eventSub;
  bool _disposed = false;
  final StreamController<List<DiscoveredServer>> _serversController =
      StreamController<List<DiscoveredServer>>.broadcast();
  final Map<String, DiscoveredServer> _servers = {};

  Stream<List<DiscoveredServer>> get serversStream => _serversController.stream;
  List<DiscoveredServer> get servers => _servers.values.toList();

  Future<void> startScan() async {
    if (_disposed) return;
    await stopScan();
    _servers.clear();
    final discovery = BonsoirDiscovery(type: serviceType);
    _discovery = discovery;
    await discovery.ready;

    _eventSub = discovery.eventStream!.listen((event) {
      if (event.type == BonsoirDiscoveryEventType.discoveryServiceResolved) {
        final service = event.service as ResolvedBonsoirService;
        final ip = service.host;
        if (ip == null) return;
        final udpPortStr = service.attributes['udp_port'];
        final udpPort =
            udpPortStr != null ? int.tryParse(udpPortStr) ?? 19780 : 19780;

        final server = DiscoveredServer(
          name: service.name,
          ip: ip,
          tcpPort: service.port,
          udpPort: udpPort,
        );
        _servers[ip] = server;
        _emit();
      } else if (event.type == BonsoirDiscoveryEventType.discoveryServiceLost) {
        final service = event.service;
        if (service == null) return;
        _servers.removeWhere((_, s) => s.name == service.name);
        _emit();
      }
    });

    await discovery.start();
  }

  void _emit() {
    // Los eventos de bonsoir pueden llegar despues de cerrar la pantalla.
    if (!_disposed && !_serversController.isClosed) {
      _serversController.add(servers);
    }
  }

  Future<void> stopScan() async {
    await _eventSub?.cancel();
    _eventSub = null;
    await _discovery?.stop();
    _discovery = null;
  }

  Future<void> dispose() async {
    _disposed = true;
    await stopScan();
    await _serversController.close();
  }
}
