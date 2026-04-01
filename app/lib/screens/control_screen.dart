// app/lib/screens/control_screen.dart
import 'dart:async';
import 'package:flutter/material.dart';
import 'package:openmouse/services/connection_service.dart';
import 'package:openmouse/screens/home_screen.dart';
import 'package:openmouse/widgets/trackpad.dart';
import 'package:openmouse/widgets/keyboard_input.dart';
import 'package:openmouse/widgets/media_controls.dart';

class ControlScreen extends StatefulWidget {
  final ConnectionService connectionService;

  const ControlScreen({super.key, required this.connectionService});

  @override
  State<ControlScreen> createState() => _ControlScreenState();
}

class _ControlScreenState extends State<ControlScreen> {
  int _currentIndex = 0;
  late StreamSubscription<bool> _connectionSub;

  @override
  void initState() {
    super.initState();
    _connectionSub = widget.connectionService.connectionStream.listen((connected) {
      if (!connected && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Connection lost. Reconnecting...'),
            backgroundColor: Colors.orange,
          ),
        );
      }
    });
  }

  @override
  void dispose() {
    _connectionSub.cancel();
    super.dispose();
  }

  void _disconnect() {
    widget.connectionService.disconnect();
    Navigator.of(context).pushReplacement(
      MaterialPageRoute(
        builder: (_) => HomeScreen(connectionService: widget.connectionService),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final pages = [
      Trackpad(connectionService: widget.connectionService),
      KeyboardInput(connectionService: widget.connectionService),
      MediaControls(connectionService: widget.connectionService),
    ];

    return Scaffold(
      backgroundColor: const Color(0xFF1A1A2E),
      appBar: AppBar(
        backgroundColor: const Color(0xFF1A1A2E),
        elevation: 0,
        title: Row(
          children: [
            Container(
              width: 8,
              height: 8,
              decoration: BoxDecoration(
                color: widget.connectionService.isConnected
                    ? Colors.green[400]
                    : Colors.orange,
                shape: BoxShape.circle,
              ),
            ),
            const SizedBox(width: 8),
            Text(
              widget.connectionService.serverIp ?? 'OpenMouse',
              style: const TextStyle(fontSize: 16),
            ),
          ],
        ),
        actions: [
          IconButton(
            onPressed: _disconnect,
            icon: const Icon(Icons.close),
            tooltip: 'Disconnect',
          ),
        ],
      ),
      body: pages[_currentIndex],
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _currentIndex,
        onTap: (index) => setState(() => _currentIndex = index),
        backgroundColor: const Color(0xFF16213E),
        selectedItemColor: Colors.green[400],
        unselectedItemColor: Colors.grey[600],
        items: const [
          BottomNavigationBarItem(
            icon: Icon(Icons.touch_app),
            label: 'Trackpad',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.keyboard),
            label: 'Keyboard',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.music_note),
            label: 'Media',
          ),
        ],
      ),
    );
  }
}
