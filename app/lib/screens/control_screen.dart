// app/lib/screens/control_screen.dart (temporary placeholder)
import 'package:flutter/material.dart';
import 'package:openmouse/services/connection_service.dart';

class ControlScreen extends StatelessWidget {
  final ConnectionService connectionService;
  const ControlScreen({super.key, required this.connectionService});

  @override
  Widget build(BuildContext context) {
    return const Scaffold(body: Center(child: Text('Control Screen - placeholder')));
  }
}
