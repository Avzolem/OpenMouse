# server/discovery.py
import socket
import logging
from zeroconf import Zeroconf, ServiceInfo
from protocol import MDNS_SERVICE_TYPE, TCP_PORT, UDP_PORT

logger = logging.getLogger("openmouse.discovery")


class Discovery:
    def __init__(self, tcp_port: int = TCP_PORT, udp_port: int = UDP_PORT):
        self._zeroconf = None
        self._info = None
        self._tcp_port = tcp_port
        self._udp_port = udp_port

    def get_local_ip(self) -> str:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
        except OSError:
            return "127.0.0.1"
        finally:
            s.close()

    def start(self):
        ip = self.get_local_ip()
        hostname = socket.gethostname()
        self._zeroconf = Zeroconf()
        self._info = ServiceInfo(
            MDNS_SERVICE_TYPE,
            f"OpenMouse on {hostname}.{MDNS_SERVICE_TYPE}",
            addresses=[socket.inet_aton(ip)],
            port=self._tcp_port,
            properties={"udp_port": str(self._udp_port)},
        )
        self._zeroconf.register_service(self._info)
        logger.info(f"mDNS: published as 'OpenMouse on {hostname}' at {ip}")
        return ip

    def stop(self):
        if self._zeroconf and self._info:
            self._zeroconf.unregister_service(self._info)
            self._zeroconf.close()
            logger.info("mDNS: service unregistered")
