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
  int _resolveFailures = 0;

  /// Cuantos servicios se vieron pero no se pudieron resolver.
  int get resolveFailures => _resolveFailures;

  Stream<List<DiscoveredServer>> get serversStream => _serversController.stream;
  List<DiscoveredServer> get servers => _servers.values.toList();

  Future<void> startScan() async {
    if (_disposed) return;
    await stopScan();
    _servers.clear();
    _resolveFailures = 0;
    final discovery = BonsoirDiscovery(type: serviceType);
    _discovery = discovery;
    await discovery.ready;

    _eventSub = discovery.eventStream!.listen((event) {
      if (event.type == BonsoirDiscoveryEventType.discoveryServiceFound) {
        // bonsoir anuncia el servicio antes de conocer su IP y su puerto. Sin
        // esta llamada nunca llega discoveryServiceResolved y la pantalla se
        // queda buscando para siempre aunque el servidor este publicado.
        event.service?.resolve(discovery.serviceResolver);
      } else if (event.type ==
          BonsoirDiscoveryEventType.discoveryServiceResolved) {
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
      } else if (event.type ==
          BonsoirDiscoveryEventType.discoveryServiceResolveFailed) {
        // Que falle la resolucion es recuperable, pero callarlo deja la
        // pantalla girando sin explicacion.
        _resolveFailures++;
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
