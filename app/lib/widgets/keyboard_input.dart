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
  // Uno para el KeyboardListener y otro para el TextField: KeyboardListener
  // envuelve al hijo en un Focus normal, asi que pedirle foco a ese nodo roba
  // el del TextField y cierra el teclado en vez de abrirlo.
  final FocusNode _focusNode = FocusNode();
  final FocusNode _textFocusNode = FocusNode();
  bool _keyboardVisible = false;

  @override
  void initState() {
    super.initState();
    _focusNode.addListener(() {
      if (!_focusNode.hasFocus) _releaseHeldKeys();
    });
    _textFocusNode.addListener(() {
      if (mounted) setState(() => _keyboardVisible = _textFocusNode.hasFocus);
    });
  }

  @override
  void dispose() {
    _releaseHeldKeys();
    _textController.dispose();
    _focusNode.dispose();
    _textFocusNode.dispose();
    super.dispose();
  }

  void _toggleKeyboard() {
    if (_textFocusNode.hasFocus) {
      _textFocusNode.unfocus();
    } else {
      _textFocusNode.requestFocus();
    }
  }

  void _sendText() {
    final text = _textController.text;
    if (text.isNotEmpty) {
      widget.connectionService.sendTcp(Packet.keyText(text));
      _textController.clear();
    }
  }

  /// Teclas que hemos enviado como "pulsada" y aun no soltamos. Si el widget
  /// pierde el foco entre el KeyDown y el KeyUp, la tecla se quedaria pulsada
  /// en el PC del usuario para siempre.
  final Set<int> _pressed = {};

  void _onKey(KeyEvent event) {
    final keyCode = Packet.encodeKey(event.logicalKey);
    if (keyCode == null) return;
    // Solo las teclas sin texto viajan en tiempo real. Los caracteres los
    // acumula el TextField y se envian con Send como un unico KEY_TEXT; si se
    // enviaran por ambos caminos, se escribirian dos veces en el PC.
    if (keyCode < 0xE000) return;
    if (event is KeyDownEvent) {
      _pressed.add(keyCode);
      widget.connectionService.sendTcp(Packet.keyPress(keyCode, 0));
    } else if (event is KeyUpEvent) {
      _pressed.remove(keyCode);
      widget.connectionService.sendTcp(Packet.keyPress(keyCode, 1));
    }
  }

  void _releaseHeldKeys() {
    for (final keyCode in _pressed) {
      widget.connectionService.sendTcp(Packet.keyPress(keyCode, 1));
    }
    _pressed.clear();
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
                    focusNode: _textFocusNode,
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
            'Las teclas especiales (Enter, flechas, Escape) se envian al vuelo.\nEscribe una frase y pulsa enviar para teclearla en el PC.',
            textAlign: TextAlign.center,
            style: TextStyle(color: Colors.grey[600], fontSize: 13),
          ),
        ],
      ),
    );
  }
}
