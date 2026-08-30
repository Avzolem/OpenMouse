#!/usr/bin/env python3
"""Pregunta a un movil concreto en que puerto escucha su ADB inalambrico.

Envia una unica consulta DNS-SD unicast al puerto 5353 de cada host indicado y
lee el registro SRV de `_adb-tls-connect._tcp`. Esto NO es un barrido de
puertos: se le pregunta al dispositivo por el dato que el mismo publica, que es
justo para lo que existe mDNS.

Hace falta porque WSL en modo NAT no recibe el multicast de la LAN, asi que
`adb mdns services` siempre sale vacio ahi.

Uso:   adb-mdns-port.py 192.168.100.11 [mas ips...]
Salida: "IP:PUERTO" del primero que conteste, o nada y codigo 1.
"""
import socket
import struct
import sys

SERVICE = "_adb-tls-connect._tcp.local"
TYPE_PTR = 12
TYPE_SRV = 33
TIMEOUT = 2.5


def encode_name(name):
    out = b""
    for label in name.split("."):
        if label:
            out += bytes([len(label)]) + label.encode()
    return out + b"\x00"


def read_name(buf, off):
    parts = []
    end = None
    for _ in range(128):
        length = buf[off]
        if length & 0xC0 == 0xC0:  # puntero de compresion
            pointer = struct.unpack("!H", buf[off:off + 2])[0] & 0x3FFF
            if end is None:
                end = off + 2
            off = pointer
            continue
        off += 1
        if length == 0:
            break
        parts.append(buf[off:off + length].decode("utf-8", "replace"))
        off += length
    else:
        raise ValueError("bucle de punteros en el nombre")
    return ".".join(parts), (end if end is not None else off)


def ports_in(buf):
    """Devuelve los puertos SRV que traiga la respuesta, en orden."""
    qd, an, ns, ar = struct.unpack("!HHHH", buf[4:12])
    off = 12
    for _ in range(qd):
        _, off = read_name(buf, off)
        off += 4
    found = []
    for _ in range(an + ns + ar):
        _, off = read_name(buf, off)
        rtype, _cls, _ttl, rdlen = struct.unpack("!HHIH", buf[off:off + 10])
        off += 10
        if rtype == TYPE_SRV and rdlen >= 6:
            found.append(struct.unpack("!H", buf[off + 4:off + 6])[0])
        off += rdlen
    return found


def ask(host, qtype):
    # El bit alto de QCLASS es QU: pide respuesta unicast en vez de multicast.
    packet = struct.pack("!HHHHHH", 0x4144, 0, 1, 0, 0, 0)
    packet += encode_name(SERVICE) + struct.pack("!HH", qtype, 0x8001)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(TIMEOUT)
    try:
        sock.sendto(packet, (host, 5353))
        while True:
            data, _ = sock.recvfrom(9000)
            try:
                for port in ports_in(data):
                    return port
            except (ValueError, IndexError, struct.error):
                continue  # respuesta malformada: se prueba la siguiente
    except (socket.timeout, OSError):
        return None
    finally:
        sock.close()


def main(argv):
    for host in argv:
        # El PTR suele traer el SRV en la seccion adicional; si no, se pide.
        for qtype in (TYPE_PTR, TYPE_SRV):
            port = ask(host, qtype)
            if port:
                print(f"{host}:{port}")
                return 0
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
