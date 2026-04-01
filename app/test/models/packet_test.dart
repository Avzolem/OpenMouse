import 'dart:typed_data';
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
}
