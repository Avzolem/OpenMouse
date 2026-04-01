// app/lib/widgets/keyboard_input.dart
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:openmouse/models/packet.dart';
import 'package:openmouse/services/connection_service.dart';

class KeyboardInput extends StatefulWidget {
  final ConnectionService connectionService;

  const KeyboardInput({super.key, required this.connectionService});

  @override
  State<KeyboardInput> createState() => _KeyboardInputState();
}

class _KeyboardInputState extends State<KeyboardInput> {
  final TextEditingController _textController = TextEditingController();
  final FocusNode _focusNode = FocusNode();
  bool _keyboardVisible = false;

  @override
  void dispose() {
    _textController.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  void _toggleKeyboard() {
    setState(() {
      _keyboardVisible = !_keyboardVisible;
      if (_keyboardVisible) {
        _focusNode.requestFocus();
      } else {
        _focusNode.unfocus();
      }
    });
  }

  void _sendText() {
    final text = _textController.text;
    if (text.isNotEmpty) {
      widget.connectionService.sendTcp(Packet.keyText(text));
      _textController.clear();
    }
  }

  void _onKey(KeyEvent event) {
    final keyCode = event.logicalKey.keyId & 0xFFFF;
    if (event is KeyDownEvent) {
      widget.connectionService.sendTcp(Packet.keyPress(keyCode, 0));
    } else if (event is KeyUpEvent) {
      widget.connectionService.sendTcp(Packet.keyPress(keyCode, 1));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        children: [
          Row(
            children: [
              Expanded(
                child: KeyboardListener(
                  focusNode: _focusNode,
                  onKeyEvent: _onKey,
                  child: TextField(
                    controller: _textController,
                    style: const TextStyle(color: Colors.white),
                    decoration: InputDecoration(
                      hintText: 'Type text to send...',
                      hintStyle: TextStyle(color: Colors.grey[600]),
                      filled: true,
                      fillColor: const Color(0xFF16213E),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(8),
                        borderSide: BorderSide.none,
                      ),
                    ),
                    onSubmitted: (_) => _sendText(),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              IconButton(
                onPressed: _sendText,
                icon: Icon(Icons.send, color: Colors.green[400]),
                style: IconButton.styleFrom(
                  backgroundColor: const Color(0xFF16213E),
                  padding: const EdgeInsets.all(16),
                ),
              ),
            ],
          ),
          const SizedBox(height: 24),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              onPressed: _toggleKeyboard,
              icon: Icon(
                _keyboardVisible ? Icons.keyboard_hide : Icons.keyboard,
              ),
              label: Text(
                _keyboardVisible ? 'Hide Keyboard' : 'Open Keyboard',
              ),
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF0F3460),
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 16),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(8),
                ),
              ),
            ),
          ),
          const Spacer(),
          Text(
            'Key presses are sent in real-time.\nUse the text field to type and send phrases.',
            textAlign: TextAlign.center,
            style: TextStyle(color: Colors.grey[600], fontSize: 13),
          ),
        ],
      ),
    );
  }
}
