# server/discovery.py
import asyncio
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

    def _register(self, ip: str):
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

    def start(self):
        """Publica el servicio y devuelve la IP local.

        El descubrimiento es una comodidad, no un requisito: si el registro
        mDNS falla (red sin multicast, otro demonio ocupando el puerto 5353),
        el servidor tiene que seguir en pie para conectarse a mano por IP.
        """
        ip = self.get_local_ip()
        try:
            self._register(ip)
        except Exception:
            self._info = None
            logger.warning(
                "mDNS no disponible: la app no encontrara el PC sola. "
                f"Conectate a mano con la IP {ip}.",
                exc_info=True,
            )
        return ip

    async def start_async(self):
        """Igual que start(), pero sin bloquear el event loop.

        register_service() de zeroconf es sincrono y puede tardar segundos
        (tiene un timeout interno de 6s), asi que llamarlo dentro de una
        corrutina congela el servidor entero mientras tanto.
        """
        ip = self.get_local_ip()
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(None, self._register, ip)
        except Exception:
            self._info = None
            logger.warning(
                "mDNS no disponible: la app no encontrara el PC sola. "
                f"Conectate a mano con la IP {ip}.",
                exc_info=True,
            )
        return ip

    def stop(self):
        if not self._zeroconf:
            return
        try:
            if self._info:
                self._zeroconf.unregister_service(self._info)
            self._zeroconf.close()
            logger.info("mDNS: service unregistered")
        except Exception:
            logger.warning("no se pudo cerrar el servicio mDNS", exc_info=True)
        finally:
            self._zeroconf = None
            self._info = None
