# OpenMouse — Design Spec

## Overview

OpenMouse is a remote mouse/keyboard/media controller. An Android app (Flutter) connects to a desktop server (Python) over WiFi, allowing the user to control their PC from their phone.

## Architecture

```
┌─────────────────┐         WiFi (LAN)         ┌─────────────────┐
│   Flutter App    │ ◄──────────────────────►   │  Python Server   │
│   (Android)      │                            │  (Windows/Linux) │
│                  │   UDP ──► mouse deltas      │                  │
│  Trackpad zone   │          scroll events      │  pynput          │
│  Keyboard        │                            │  (mouse/keyboard)│
│  Media controls  │   TCP ──► key presses       │                  │
│                  │          clicks             │  pystray         │
│  mDNS discovery  │          media commands     │  (system tray)   │
│  (bonsoir)       │                            │                  │
│                  │   TCP ◄── server status      │  zeroconf        │
│                  │                            │  (mDNS broadcast) │
└─────────────────┘                            └─────────────────┘
```

### Flow

1. Python server starts, publishes itself via mDNS as `_openmouse._tcp.local`
2. Flutter app scans the network for that service
3. On discovery, establishes UDP + TCP connections to the server
4. User gestures are translated into binary packets and sent
5. Server receives packets and executes actions via `pynput`

### Ports

- UDP: 19780 (mouse movement, scroll)
- TCP: 19781 (keyboard, clicks, media, status)

## Protocol

Binary format: 1 byte type + payload.

| Type | Byte | Channel | Payload |
|------|------|---------|---------|
| Mouse move | `0x01` | UDP | `dx` (int16) + `dy` (int16) = 4 bytes |
| Scroll | `0x02` | UDP | `dy` (int16) = 2 bytes |
| Left click | `0x10` | TCP | `action` (1 byte: 0=press, 1=release, 2=click) |
| Right click | `0x11` | TCP | `action` (1 byte) |
| Double click | `0x12` | TCP | no payload |
| Key press | `0x20` | TCP | `key_code` (uint16, Flutter logical key ID) + `action` (1 byte: 0=down, 1=up) |
| Key text | `0x21` | TCP | `length` (uint16) + `utf-8 string` |
| Media play/pause | `0x30` | TCP | no payload |
| Media next | `0x31` | TCP | no payload |
| Media prev | `0x32` | TCP | no payload |
| Volume up | `0x33` | TCP | no payload |
| Volume down | `0x34` | TCP | no payload |
| Volume mute | `0x35` | TCP | no payload |

### Design rationale

- Binary, not JSON — mouse packets are sent 60-100 times/sec. 5 bytes vs 30+ with JSON.
- int16 for deltas — range -32768 to 32767, more than enough between frames.
- UDP/TCP split — mouse/scroll tolerate packet loss (next packet corrects), keyboard/clicks do not.

## Python Server

### Structure

```
server/
├── openmouse.py          # Entry point
├── server.py             # UDP + TCP listeners (asyncio)
├── input_handler.py      # Translates packets → pynput actions
├── discovery.py          # Publishes mDNS service
├── tray.py               # System tray icon + menu
└── requirements.txt
```

### Components

**`server.py`** — Runs two listeners with `asyncio`:
- UDP socket on 19780: receives mouse/scroll, calls `input_handler`
- TCP socket on 19781: receives keyboard/clicks/media, calls `input_handler`

**`input_handler.py`** — Single controller using `pynput`:
- `move(dx, dy)` → `pynput.mouse.Controller().move(dx, dy)`
- `scroll(dy)` → `pynput.mouse.Controller().scroll(0, dy)`
- `click(button, action)` → press/release/click
- `key(code, action)` → `pynput.keyboard.Controller().press/release`
- `media(command)` → maps to OS multimedia keys

**`discovery.py`** — Registers service with `zeroconf`:
- Type: `_openmouse._tcp.local.`
- Name: `OpenMouse on {hostname}`
- Port: 19781 (TCP), includes UDP port in TXT record

**`tray.py`** — Tray icon with `pystray`:
- Shows local IP and status (waiting / connected)
- Menu: "Show IP", "Quit"
- Runs in its own thread (pystray requirement)

### Dependencies

```
pynput
pystray
Pillow
zeroconf
```

### Startup flow

1. `openmouse.py` starts
2. Starts mDNS discovery (publishes service)
3. Starts UDP + TCP listeners with asyncio
4. Starts system tray in separate thread
5. Listens until user selects "Quit" from tray

## Flutter App (Android)

### Structure

```
lib/
├── main.dart
├── screens/
│   ├── home_screen.dart        # Connection screen (find/select server)
│   └── control_screen.dart     # Main screen with trackpad/keyboard/media
├── widgets/
│   ├── trackpad.dart           # Touch zone for mouse + scroll
│   ├── keyboard_input.dart     # Keyboard input
│   └── media_controls.dart     # Media buttons
├── services/
│   ├── connection_service.dart # Manages UDP + TCP to server
│   └── discovery_service.dart  # Finds servers via mDNS (bonsoir)
└── models/
    └── packet.dart             # Encodes binary packets per protocol
```

### Screens

**Home Screen — Connection:**
- On open, scans network for `_openmouse._tcp.local`
- Shows list of found servers with name and IP
- "Connect manually" button → IP input field
- On server selection, navigates to Control Screen

**Control Screen — Main screen:**
- Full screen, 3 zones accessible via bottom navigation:

**1. Trackpad (main zone):**

```
┌──────────────────────────┬────┐
│                          │ ▲  │
│                          │ │  │
│      Touch zone          │ S  │
│      (mouse move)        │ c  │
│                          │ r  │
│   tap = left click       │ o  │
│   double tap = dbl click │ l  │
│   long press = right clk │ l  │
│                          │ │  │
│                          │ ▼  │
└──────────────────────────┴────┘
         ~85%                ~15%
```

- Touch zone (~85%): `onPanUpdate` sends `0x01` + dx/dy via UDP
- Scroll bar (~15%): vertical finger slide sends `0x02` + dy via UDP
- Two-finger scroll on trackpad zone also sends `0x02` (alternative)
- Tap → left click, double tap → double click, long press → right click

**2. Keyboard:**
- Button that opens Android native keyboard
- Captures each key and sends `0x20` via TCP
- Text field for complete phrases → sends `0x21` via TCP

**3. Media:**
- Row of large buttons: prev, play/pause, next
- Volume row: vol down, mute, vol up
- Each button sends its `0x30`-`0x35` command via TCP

### Dependencies

```yaml
dependencies:
  bonsoir: ^5.0.0
```

Everything else uses `dart:io` (UDP/TCP) and native Flutter widgets.

## Discovery and Connection

### Connection flow

```
Server starts
    ├── Publishes "_openmouse._tcp.local" via zeroconf
    ├── Opens UDP 19780
    └── Opens TCP 19781

App opens
    ├── Scans "_openmouse._tcp.local" with bonsoir
    │   └── Finds: "OpenMouse on MI-PC" → 192.168.1.50
    ├── User selects server (or enters IP manually)
    ├── Opens UDP socket → targets 192.168.1.50:19780
    ├── Opens TCP socket → connects to 192.168.1.50:19781
    └── Ready to send commands
```

### Reconnection

- If TCP connection drops, app shows indicator and retries every 2 seconds
- If user switches WiFi network, returns to Home Screen to reconnect
- No persistent session or state — each connection is independent

### Manual connection (fallback)

- User enters the IP shown by the server tray icon
- App connects directly to that IP on known ports
- Useful when mDNS fails (corporate networks, client isolation)

## Scope

### In scope (MVP)

- Python server for Windows + Linux
- Android Flutter app
- Mouse movement, scroll (bar + two-finger), left/right/double click
- Keyboard (key-by-key + full text)
- Media controls (play/pause, next, prev, vol up/down, mute)
- mDNS auto-discovery + manual IP fallback
- System tray with IP and status
- PyInstaller packaging for distribution
- Professional UI design

### Out of scope

- macOS / iOS
- USB connection
- Gamepad, custom gestures, presentations
- Authentication / encryption
- Multiple simultaneous clients (1 phone at a time)

## Tech Stack

| Component | Technology |
|---|---|
| Server | Python 3.11+, asyncio, pynput, pystray, zeroconf |
| Client | Flutter, dart:io, bonsoir |
| Protocol | UDP (mouse/scroll) + TCP (keyboard/clicks/media) |
| Discovery | mDNS (`_openmouse._tcp.local`) |
| Distribution | PyInstaller (server), APK (client) |
