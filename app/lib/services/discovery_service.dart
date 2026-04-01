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
  final StreamController<List<DiscoveredServer>> _serversController =
      StreamController<List<DiscoveredServer>>.broadcast();
  final Map<String, DiscoveredServer> _servers = {};

  Stream<List<DiscoveredServer>> get serversStream => _serversController.stream;
  List<DiscoveredServer> get servers => _servers.values.toList();

  Future<void> startScan() async {
    _servers.clear();
    _discovery = BonsoirDiscovery(type: serviceType);
    await _discovery!.ready;

    _discovery!.eventStream!.listen((event) {
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
        _serversController.add(servers);
      } else if (event.type == BonsoirDiscoveryEventType.discoveryServiceLost) {
        final service = event.service;
        if (service == null) return;
        _servers.removeWhere((_, s) => s.name == service.name);
        _serversController.add(servers);
      }
    });

    await _discovery!.start();
  }

  Future<void> stopScan() async {
    await _discovery?.stop();
    _discovery = null;
  }

  void dispose() {
    stopScan();
    _serversController.close();
  }
}
