<p align="center">
  <img src="server/icon.png" alt="OpenMouse Logo" width="150"/>
</p>

<h1 align="center">OpenMouse</h1>

<p align="center">
  <strong>Controla tu PC desde tu celular por WiFi</strong>
</p>

<p align="center">
  <a href="#características">Características</a> •
  <a href="#instalación">Instalación</a> •
  <a href="#uso">Uso</a> •
  <a href="#tecnologías">Tecnologías</a> •
  <a href="#contribuir">Contribuir</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/Flutter-3.0+-02569B?style=for-the-badge&logo=flutter&logoColor=white" alt="Flutter"/>
  <img src="https://img.shields.io/badge/Windows-10+-0078D6?style=for-the-badge&logo=windows&logoColor=white" alt="Windows"/>
  <img src="https://img.shields.io/badge/Linux-compatible-FCC624?style=for-the-badge&logo=linux&logoColor=black" alt="Linux"/>
  <img src="https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge" alt="License"/>
</p>

---

## 📱 ¿Qué es OpenMouse?

**OpenMouse** es un sistema de control remoto que convierte tu celular Android en un mouse, teclado y control multimedia para tu PC, conectándose por WiFi en tu red local.

¿No tienes mouse a la mano? ¿Quieres controlar una presentación desde el sofá? ¿Cambiar de canción sin levantarte? OpenMouse lo resuelve:

- 👆 **Trackpad táctil** = Mueve el cursor con tu dedo
- ⌨️ **Teclado remoto** = Escribe en tu PC desde el celular
- 🎵 **Controles multimedia** = Play, pause, volumen, siguiente canción

---

## ✨ Características

### 🖱️ Trackpad Intuitivo
- Zona táctil amplia para mover el cursor
- Tap = click izquierdo
- Doble tap = doble click
- Presión larga = click derecho
- Barra lateral de scroll dedicada
- Scroll con dos dedos como alternativa

### ⌨��� Teclado Completo
- Captura de teclas en tiempo real
- Campo de texto para enviar frases completas
- Usa el teclado nativo de Android

### 🎵 Control Multimedia
- Play / Pause
- Siguiente / Anterior
- Volumen arriba / abajo / mute
- Botones grandes y fáciles de usar

### 🔍 Descubrimiento Automático
- Encuentra tu PC automáticamente en la red (mDNS)
- Conexión manual por IP como alternativa
- Reconexión automática si se pierde la señal

### 💻 Instalación Sencilla en PC
- Ejecuta el `.exe` y listo — se instala y arranca solo
- Icono en la bandeja del sistema con IP y estado
- Auto-inicio al encender Windows
- Desinstalar desde el menú del tray icon

---

## 📸 Capturas de Pantalla

<p align="center">
  <i>Próximamente...</i>
</p>

<!--
<p align="center">
  <img src="screenshots/home.png" width="200"/>
  <img src="screenshots/trackpad.png" width="200"/>
  <img src="screenshots/keyboard.png" width="200"/>
  <img src="screenshots/media.png" width="200"/>
</p>
-->

---

## 🚀 Instalación

### Servidor (PC - Windows/Linux)

#### Opción 1: Ejecutable (recomendado)

Descarga `openmouse.exe` desde [Releases](https://github.com/Avzolem/OpenMouse/releases) y ejecútalo. Se instala automáticamente y arranca al encender tu PC.

#### Opción 2: Desde el código fuente

```bash
git clone https://github.com/Avzolem/OpenMouse.git
cd OpenMouse/server
pip install -r requirements.txt
python openmouse.py
```

### App Android (Celular)

#### Opción 1: APK

Descarga la APK desde [Releases](https://github.com/Avzolem/OpenMouse/releases) e instálala en tu dispositivo.

#### Opción 2: Compilar desde el código fuente

```bash
cd OpenMouse/app
flutter pub get
flutter run

# O compilar APK release
flutter build apk --release
```

### Requisitos

| Componente | Requisito |
|---|---|
| **PC** | Windows 10+ o Linux con escritorio |
| **Celular** | Android 5.0+ |
| **Red** | Ambos dispositivos en la misma red WiFi |

---

## 📖 Uso

### 1. Inicia el Servidor
Ejecuta `openmouse.exe` en tu PC. Aparecerá un icono verde en la bandeja del sistema mostrando tu IP.

### 2. Conecta desde el Celular
Abre la app OpenMouse en tu Android. Tu PC aparecerá automáticamente en la lista. Tócala para conectar.

> Si no aparece automáticamente, usa "Conectar manualmente" e ingresa la IP que muestra el tray icon.

### 3. Controla tu PC
Usa la navegación inferior para cambiar entre:

- **Trackpad** — Desliza para mover el cursor. Toca para click. Usa la barra lateral para scroll.
- **Teclado** — Escribe texto o envía teclas individuales en tiempo real.
- **Media** — Controla reproducción y volumen con botones grandes.

### Desinstalar
Click derecho en el tray icon → **Uninstall**. Se elimina el auto-inicio y los archivos.

---

## 🛠️ Tecnologías

| Tecnología | Uso |
|---|---|
| **Python 3.11+** | Servidor de escritorio |
| **asyncio** | Listeners UDP + TCP de alto rendimiento |
| **pynput** | Simulación de mouse, teclado y teclas multimedia |
| **pystray** | Icono en la bandeja del sistema |
| **zeroconf** | Descubrimiento automático por mDNS |
| **Flutter** | App Android |
| **dart:io** | Comunicación UDP/TCP |
| **bonsoir** | Descubrimiento mDNS desde Android |
| **PyInstaller** | Empaquetado del servidor como ejecutable |

---

## 🔧 Protocolo

OpenMouse usa un protocolo binario liviano optimizado para baja latencia:

| Canal | Puerto | Uso | Latencia |
|---|---|---|---|
| **UDP** | 19780 | Movimiento del mouse, scroll | ~1-5ms |
| **TCP** | 19781 | Teclado, clicks, multimedia | Fiable |

Los paquetes de mouse se envían 60-100 veces por segundo con solo 5 bytes cada uno, logrando una experiencia fluida e instantánea.

---

## 📁 Estructura del Proyecto

```
OpenMouse/
├── server/                       # Servidor Python (PC)
│   ├── openmouse.py              # Punto de entrada + instalador
│   ├── protocol.py               # Protocolo binario de paquetes
│   ├── input_handler.py          # Control de mouse/teclado (pynput)
│   ├── network.py                # Listeners UDP + TCP (asyncio)
│   ├── discovery.py              # Publicación mDNS (zeroconf)
│   ├── tray.py                   # Icono en bandeja del sistema
│   ├── icon.png                  # Icono de la app
│   ├── requirements.txt          # Dependencias Python
│   └── tests/                    # Tests del servidor
│       ├── test_protocol.py
│       ├── test_input_handler.py
│       └── test_network.py
│
└── app/                          # App Flutter (Android)
    └── lib/
        ├── main.dart             # Punto de entrada
        ├── models/
        │   └── packet.dart       # Codificación de paquetes
        ├── services/
        │   ├─��� connection_service.dart  # Gestión UDP + TCP
        │   └── discovery_service.dart   # Descubrimiento mDNS
        ├── screens/
        │   ├── home_screen.dart         # Conexión a servidor
        │   └── control_screen.dart      # Pantalla principal
        └── widgets/
            ├── trackpad.dart            # Zona táctil + scroll
            ├── keyboard_input.dart      # Entrada de teclado
            └── media_controls.dart      # Controles multimedia
```

---

## 🤝 Contribuir

¡Las contribuciones son bienvenidas! Si quieres mejorar OpenMouse:

1. Haz un Fork del proyecto
2. Crea una rama para tu feature (`git checkout -b feature/NuevaFuncion`)
3. Haz commit de tus cambios (`git commit -m 'Agregar nueva función'`)
4. Push a la rama (`git push origin feature/NuevaFuncion`)
5. Abre un Pull Request

### Ideas para Contribuir
- [ ] Soporte para macOS
- [ ] App para iOS
- [ ] Conexión por USB
- [ ] Gestos personalizables
- [ ] Modo presentación (diapositivas)
- [ ] Gamepad virtual
- [ ] Encriptación de la conexión

---

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Consulta el archivo [LICENSE](LICENSE) para más detalles.

---

## 👨‍💻 Autor

<p align="center">
  <strong>Desarrollado con ❤️ por <a href="https://avsolem.com">avsolem.com</a></strong>
</p>

---

<p align="center">
  <sub>¿Te gusta OpenMouse? ¡Dale una ⭐ al repo!</sub>
</p>
