// app/lib/main.dart
import 'package:flutter/material.dart';
import 'package:openmouse/services/connection_service.dart';
import 'package:openmouse/screens/home_screen.dart';

void main() {
  runApp(const OpenMouseApp());
}

class OpenMouseApp extends StatefulWidget {
  const OpenMouseApp({super.key});

  @override
  State<OpenMouseApp> createState() => _OpenMouseAppState();
}

class _OpenMouseAppState extends State<OpenMouseApp> {
  final ConnectionService _connectionService = ConnectionService();

  @override
  void dispose() {
    _connectionService.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'OpenMouse',
      debugShowCheckedModeBanner: false,
      theme: ThemeData.dark().copyWith(
        colorScheme: ColorScheme.dark(
          primary: Colors.green[400]!,
        ),
      ),
      home: HomeScreen(connectionService: _connectionService),
    );
  }
}
