import 'dart:convert';

import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:openmouse/models/packet.dart';

void main() {
  group('Packet encoding', () {
    test('encodes mouse move', () {
      final bytes = Packet.mouseMove(150, -200);
      expect(bytes.length, 5);
      expect(bytes[0], 0x01);
      final bd = ByteData.sublistView(bytes);
      expect(bd.getInt16(1), 150);
      expect(bd.getInt16(3), -200);
    });

    test('encodes scroll', () {
      final bytes = Packet.scroll(-3);
      expect(bytes.length, 3);
      expect(bytes[0], 0x02);
      final bd = ByteData.sublistView(bytes);
      expect(bd.getInt16(1), -3);
    });

    test('encodes left click', () {
      final bytes = Packet.leftClick(2);
      expect(bytes.length, 2);
      expect(bytes[0], 0x10);
      expect(bytes[1], 2);
    });

    test('encodes right click', () {
      final bytes = Packet.rightClick(2);
      expect(bytes.length, 2);
      expect(bytes[0], 0x11);
      expect(bytes[1], 2);
    });

    test('encodes double click', () {
      final bytes = Packet.doubleClick();
      expect(bytes.length, 1);
      expect(bytes[0], 0x12);
    });

    test('encodes key press', () {
      final bytes = Packet.keyPress(0x0041, 0);
      expect(bytes.length, 4);
      expect(bytes[0], 0x20);
      final bd = ByteData.sublistView(bytes);
      expect(bd.getUint16(1), 0x0041);
      expect(bytes[3], 0);
    });

    test('encodes key text', () {
      final bytes = Packet.keyText('hello');
      expect(bytes[0], 0x21);
      final bd = ByteData.sublistView(bytes);
      expect(bd.getUint16(1), 5);
      expect(String.fromCharCodes(bytes.sublist(3)), 'hello');
    });

    test('encodes media play pause', () {
      final bytes = Packet.mediaPlayPause();
      expect(bytes, [0x30]);
    });

    test('encodes media next', () {
      final bytes = Packet.mediaNext();
      expect(bytes, [0x31]);
    });

    test('encodes media prev', () {
      final bytes = Packet.mediaPrev();
      expect(bytes, [0x32]);
    });

    test('encodes volume up', () {
      final bytes = Packet.volumeUp();
      expect(bytes, [0x33]);
    });

    test('encodes volume down', () {
      final bytes = Packet.volumeDown();
      expect(bytes, [0x34]);
    });

    test('encodes volume mute', () {
      final bytes = Packet.volumeMute();
      expect(bytes, [0x35]);
    });

    test('wraps TCP packet with length prefix', () {
      final inner = Packet.leftClick(2);
      final wrapped = Packet.wrapTcp(inner);
      expect(wrapped.length, 4); // 2 bytes length + 2 bytes packet
      final bd = ByteData.sublistView(wrapped);
      expect(bd.getUint16(0), 2);
      expect(wrapped[2], 0x10);
      expect(wrapped[3], 2);
    });
  });

  group('Packet.encodeKey', () {
    test('las teclas de caracter viajan como su code point', () {
      expect(Packet.encodeKey(LogicalKeyboardKey.keyA), 0x61);
      expect(Packet.encodeKey(LogicalKeyboardKey.space), 0x20);
      expect(Packet.encodeKey(LogicalKeyboardKey.digit1), 0x31);
    });

    test('las teclas especiales usan el Area de Uso Privado, no basura Unicode',
        () {
      // Antes: keyId & 0xFFFF hacia que arrowUp llegase como chr(772) y
      // shiftLeft como 'Ă'.
      expect(Packet.encodeKey(LogicalKeyboardKey.enter), 0xE000);
      expect(Packet.encodeKey(LogicalKeyboardKey.backspace), 0xE001);
      expect(Packet.encodeKey(LogicalKeyboardKey.arrowUp), 0xE00A);
      expect(Packet.encodeKey(LogicalKeyboardKey.shiftLeft), 0xE00E);
      expect(Packet.encodeKey(LogicalKeyboardKey.f1), 0xE020);
    });

    test('todos los codigos caben en el u16 del protocolo', () {
      for (final key in [
        LogicalKeyboardKey.enter,
        LogicalKeyboardKey.arrowRight,
        LogicalKeyboardKey.controlLeft,
        LogicalKeyboardKey.f12,
        LogicalKeyboardKey.keyZ,
      ]) {
        final code = Packet.encodeKey(key)!;
        expect(code, inInclusiveRange(0, 0xFFFF));
      }
    });

    test('una tecla no representable devuelve null en vez de basura', () {
      expect(Packet.encodeKey(LogicalKeyboardKey.gameButton1), isNull);
    });
  });

  group('Packet.keyText', () {
    test('recorta el texto que no cabe en el prefijo u16', () {
      final huge = 'a' * 70000;
      final packet = Packet.keyText(huge);
      final declared = ByteData.sublistView(packet).getUint16(1);
      expect(declared, Packet.maxTextBytes);
      expect(packet.length, 3 + Packet.maxTextBytes);
    });

    test('no parte una secuencia UTF-8 al recortar', () {
      final huge = 'ñ' * 40000; // 80000 bytes
      final packet = Packet.keyText(huge);
      final declared = ByteData.sublistView(packet).getUint16(1);
      final body = packet.sublist(3, 3 + declared);
      expect(() => utf8.decode(body), returnsNormally);
    });
  });

  group('limites del frame TCP', () {
    test('el keyText mas largo sigue cabiendo en el prefijo u16', () {
      final packet = Packet.keyText('a' * 70000);
      expect(packet.length, lessThanOrEqualTo(Packet.maxFrameBytes));
      final framed = Packet.wrapTcp(packet);
      final declared = ByteData.sublistView(framed).getUint16(0);
      expect(declared, packet.length,
          reason: 'la longitud declarada debe coincidir con la real');
      expect(framed.length, 2 + packet.length);
    });

    test('wrapTcp rechaza un payload que no cabe en vez de truncarlo', () {
      expect(() => Packet.wrapTcp(Uint8List(Packet.maxFrameBytes + 1)),
          throwsArgumentError);
    });
  });
}
