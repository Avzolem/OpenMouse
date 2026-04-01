import 'dart:typed_data';
import 'dart:convert';

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

  static Uint8List keyPress(int keyCode, int action) {
    final bd = ByteData(4);
    bd.setUint8(0, 0x20);
    bd.setUint16(1, keyCode);
    bd.setUint8(3, action);
    return bd.buffer.asUint8List();
  }

  static Uint8List keyText(String text) {
    final encoded = utf8.encode(text);
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
  static Uint8List wrapTcp(Uint8List packet) {
    final bd = ByteData(2 + packet.length);
    bd.setUint16(0, packet.length);
    final bytes = bd.buffer.asUint8List();
    bytes.setRange(2, 2 + packet.length, packet);
    return bytes;
  }
}
