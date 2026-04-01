// app/lib/screens/home_screen.dart
import 'package:flutter/material.dart';
import 'package:openmouse/services/discovery_service.dart';
import 'package:openmouse/services/connection_service.dart';
import 'package:openmouse/screens/control_screen.dart';

class HomeScreen extends StatefulWidget {
  final ConnectionService connectionService;

  const HomeScreen({super.key, required this.connectionService});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final DiscoveryService _discovery = DiscoveryService();
  final TextEditingController _ipController = TextEditingController();
  List<DiscoveredServer> _servers = [];
  bool _connecting = false;

  @override
  void initState() {
    super.initState();
    _discovery.serversStream.listen((servers) {
      if (mounted) setState(() => _servers = servers);
    });
    _discovery.startScan();
  }

  @override
  void dispose() {
    _discovery.dispose();
    _ipController.dispose();
    super.dispose();
  }

  Future<void> _connectTo(String ip, {int udpPort = 19780, int tcpPort = 19781}) async {
    setState(() => _connecting = true);
    try {
      await widget.connectionService.connect(ip, udpPort: udpPort, tcpPort: tcpPort);
      if (mounted) {
        Navigator.of(context).pushReplacement(
          MaterialPageRoute(
            builder: (_) => ControlScreen(
              connectionService: widget.connectionService,
            ),
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Connection failed: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _connecting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF1A1A2E),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: 40),
              const Text(
                'OpenMouse',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 32,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                'Searching for servers...',
                style: TextStyle(color: Colors.grey[400], fontSize: 16),
              ),
              const SizedBox(height: 32),
              Expanded(
                child: _servers.isEmpty
                    ? Center(
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            CircularProgressIndicator(
                              color: Colors.green[400],
                            ),
                            const SizedBox(height: 16),
                            Text(
                              'Looking for OpenMouse servers\non your network...',
                              textAlign: TextAlign.center,
                              style: TextStyle(color: Colors.grey[500]),
                            ),
                          ],
                        ),
                      )
                    : ListView.builder(
                        itemCount: _servers.length,
                        itemBuilder: (context, index) {
                          final server = _servers[index];
                          return Card(
                            color: const Color(0xFF16213E),
                            margin: const EdgeInsets.only(bottom: 12),
                            child: ListTile(
                              leading: Icon(
                                Icons.computer,
                                color: Colors.green[400],
                                size: 32,
                              ),
                              title: Text(
                                server.name,
                                style: const TextStyle(
                                  color: Colors.white,
                                  fontWeight: FontWeight.w500,
                                ),
                              ),
                              subtitle: Text(
                                server.ip,
                                style: TextStyle(color: Colors.grey[400]),
                              ),
                              trailing: const Icon(
                                Icons.arrow_forward_ios,
                                color: Colors.white54,
                                size: 16,
                              ),
                              onTap: () => _connectTo(
                                server.ip,
                                udpPort: server.udpPort,
                                tcpPort: server.tcpPort,
                              ),
                            ),
                          );
                        },
                      ),
              ),
              const Divider(color: Colors.white24),
              const SizedBox(height: 12),
              Text(
                'Connect manually',
                style: TextStyle(color: Colors.grey[400], fontSize: 14),
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _ipController,
                      style: const TextStyle(color: Colors.white),
                      decoration: InputDecoration(
                        hintText: '192.168.1.100',
                        hintStyle: TextStyle(color: Colors.grey[600]),
                        filled: true,
                        fillColor: const Color(0xFF16213E),
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(8),
                          borderSide: BorderSide.none,
                        ),
                      ),
                      keyboardType: const TextInputType.numberWithOptions(decimal: true),
                    ),
                  ),
                  const SizedBox(width: 12),
                  ElevatedButton(
                    onPressed: _connecting
                        ? null
                        : () {
                            final ip = _ipController.text.trim();
                            if (ip.isNotEmpty) _connectTo(ip);
                          },
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.green[400],
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(
                        horizontal: 24,
                        vertical: 16,
                      ),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(8),
                      ),
                    ),
                    child: _connecting
                        ? const SizedBox(
                            width: 20,
                            height: 20,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              color: Colors.white,
                            ),
                          )
                        : const Text('Connect'),
                  ),
                ],
              ),
              const SizedBox(height: 16),
            ],
          ),
        ),
      ),
    );
  }
}
