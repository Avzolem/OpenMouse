import 'dart:convert';

import 'package:flutter/services.dart';

class Packet {
  static Uint8List mouseMove(int dx, int dy) {
    final bd = ByteData(5);
    bd.setUint8(0, 0x01);
    bd.setInt16(1, dx);
    bd.setInt16(3, dy);
    return bd.buffer.asUint8List();
  }

  static Uint8List scroll(int dy) {
    final bd = ByteData(3);
    bd.setUint8(0, 0x02);
    bd.setInt16(1, dy);
    return bd.buffer.asUint8List();
  }

  static Uint8List leftClick(int action) {
    return Uint8List.fromList([0x10, action]);
  }

  static Uint8List rightClick(int action) {
    return Uint8List.fromList([0x11, action]);
  }

  static Uint8List doubleClick() {
    return Uint8List.fromList([0x12]);
  }

  /// Codigos de tecla especiales, espejo de SPECIAL_KEYS en server/protocol.py.
  ///
  /// keyCode viaja como u16 y normalmente lleva un code point Unicode. Las
  /// teclas sin texto (Enter, flechas, Shift, F1...) van en el Area de Uso
  /// Privado, que nunca aparece en texto real. Antes se enmascaraba el keyId
  /// con 0xFFFF, y el servidor acababa escribiendo basura: la flecha arriba
  /// llegaba como chr(772) y Shift como 'Ă'.
  static const Map<int, int> _specialKeys = {
    0x0010000000d: 0xE000, // enter
    0x00100000008: 0xE001, // backspace
    0x00100000009: 0xE002, // tab
    0x0010000001b: 0xE003, // escape
    0x0010000007f: 0xE004, // delete
    0x00100000407: 0xE005, // insert
    0x00100000306: 0xE006, // home
    0x00100000305: 0xE007, // end
    0x00100000308: 0xE008, // pageUp
    0x00100000307: 0xE009, // pageDown
    0x00100000304: 0xE00A, // arrowUp
    0x00100000301: 0xE00B, // arrowDown
    0x00100000302: 0xE00C, // arrowLeft
    0x00100000303: 0xE00D, // arrowRight
    0x00200000102: 0xE00E, // shiftLeft
    0x00200000103: 0xE00F, // shiftRight
    0x00200000100: 0xE010, // controlLeft
    0x00200000101: 0xE011, // controlRight
    0x00200000104: 0xE012, // altLeft
    0x00200000105: 0xE013, // altRight
    0x00200000106: 0xE014, // metaLeft
    0x00200000107: 0xE015, // metaRight
    0x00100000104: 0xE016, // capsLock
    0x00100000801: 0xE020, // f1
    0x00100000802: 0xE021, // f2
    0x00100000803: 0xE022, // f3
    0x00100000804: 0xE023, // f4
    0x00100000805: 0xE024, // f5
    0x00100000806: 0xE025, // f6
    0x00100000807: 0xE026, // f7
    0x00100000808: 0xE027, // f8
    0x00100000809: 0xE028, // f9
    0x0010000080a: 0xE029, // f10
    0x0010000080b: 0xE02A, // f11
    0x0010000080c: 0xE02B, // f12
  };

  /// Traduce una tecla logica de Flutter al codigo del protocolo.
  /// Devuelve null si no es representable, para no enviar basura.
  static int? encodeKey(LogicalKeyboardKey key) {
    final special = _specialKeys[key.keyId];
    if (special != null) return special;
    final id = key.keyId;
    // Los caracteres reales viven en el plano Unicode con los bits altos a 0.
    if (id > 0 && id <= 0xFFFF) return id;
    return null;
  }

  static Uint8List keyPress(int keyCode, int action) {
    final bd = ByteData(4);
    bd.setUint8(0, 0x20);
    bd.setUint16(1, keyCode);
    bd.setUint8(3, action);
    return bd.buffer.asUint8List();
  }

  /// Un frame TCP entero (cabecera incluida) tiene que caber en el prefijo de
  /// longitud u16, asi que al texto le quedan 0xFFFF menos los 3 bytes de
  /// cabecera del propio KEY_TEXT.
  static const int maxFrameBytes = 0xFFFF;
  static const int maxTextBytes = maxFrameBytes - 3;

  static Uint8List keyText(String text) {
    var encoded = utf8.encode(text);
    if (encoded.length > maxTextBytes) {
      // Recorta en un limite de caracter para no partir una secuencia UTF-8.
      var end = maxTextBytes;
      while (end > 0 && (encoded[end] & 0xC0) == 0x80) {
        end--;
      }
      encoded = encoded.sublist(0, end);
    }
    final bd = ByteData(3 + encoded.length);
    bd.setUint8(0, 0x21);
    bd.setUint16(1, encoded.length);
    final bytes = bd.buffer.asUint8List();
    bytes.setRange(3, 3 + encoded.length, encoded);
    return bytes;
  }

  static Uint8List mediaPlayPause() => Uint8List.fromList([0x30]);
  static Uint8List mediaNext() => Uint8List.fromList([0x31]);
  static Uint8List mediaPrev() => Uint8List.fromList([0x32]);
  static Uint8List volumeUp() => Uint8List.fromList([0x33]);
  static Uint8List volumeDown() => Uint8List.fromList([0x34]);
  static Uint8List volumeMute() => Uint8List.fromList([0x35]);

  /// Wraps a TCP packet with a 2-byte big-endian length prefix.
  ///
  /// setUint16 trunca en silencio, asi que un payload mayor que 0xFFFF
  /// declararia una longitud absurda y desincronizaria el stream TCP: el
  /// servidor leeria unos pocos bytes y tomaria el resto por frames nuevos.
  static Uint8List wrapTcp(Uint8List packet) {
    if (packet.length > maxFrameBytes) {
      throw ArgumentError.value(
        packet.length,
        'packet',
        'un frame TCP no puede superar $maxFrameBytes bytes',
      );
    }
    final bd = ByteData(2 + packet.length);
    bd.setUint16(0, packet.length);
    final bytes = bd.buffer.asUint8List();
    bytes.setRange(2, 2 + packet.length, packet);
    return bytes;
  }
}
