# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Layout

OpenMouse is a two-part system: a Python desktop server (`server/`) and a Flutter Android client (`app/`). They communicate over the local network using a custom binary protocol on UDP 19780 + TCP 19781. `scripts/` holds the Linux curl-installer pair plus `adb-connect.sh` (dev-only wireless-ADB reconnect), `.github/workflows/release.yml` builds every shipped artifact, and `docs/superpowers/` holds design specs and implementation plans.

## Common Commands

### Server (Python)

Run from `server/` — the modules import each other flat (`from protocol import ...`), so the working directory must be `server/`:

```bash
pip install -r requirements.txt
python openmouse.py                    # run server (on Windows also self-installs on first run)

pytest                                 # run all tests
pytest tests/test_protocol.py          # single file
pytest tests/test_protocol.py::TestParseUdpPacket::test_mouse_move   # single test

pyinstaller openmouse.spec             # build standalone exe (output in dist/)
```

There is no pytest config file; `tests/__init__.py` makes the suite a package so `server/` lands on `sys.path`.

When iterating, run from source — `is_installed()` returns `False` for non-frozen runs and `ensure_installed()` is a no-op outside Windows, so nothing is copied anywhere.

### App (Flutter)

Run from `app/`:

```bash
flutter pub get
flutter run                            # debug on connected device
flutter build apk --release            # release APK at build/app/outputs/flutter-apk/
flutter test                           # widget/unit tests
flutter analyze                        # static analysis (analysis_options.yaml → flutter_lints)
```

A local `flutter build apk --release` is signed with the **debug** key: `android/app/build.gradle` falls back to `signingConfigs.debug` whenever `android/key.properties` is missing. Only CI produces a properly signed APK.

## Architecture

### Two-channel protocol (`server/protocol.py`)

The protocol module is the **single source of truth** for packet layout and is mirrored by `app/lib/models/packet.dart` on the client. Any change to packet types or byte layout must be made in both places.

- **UDP 19780** — high-frequency, lossy events: `MOUSE_MOVE` (5 bytes: type + i16 dx + i16 dy) and `SCROLL` (3 bytes). Sent 60–100 Hz; loss is acceptable.
- **TCP 19781** — reliable events: clicks, key press/release, text typing, media keys. TCP frames are length-prefixed: `u16 length` + payload (`Packet.wrapTcp` on the client, `readexactly(2)` on the server). The first payload byte is always `PacketType`.

Wire-format landmines:

- `PacketType` is an `IntEnum`; values are part of the wire format — never renumber existing entries.
- The type byte is unpacked with a **signed** `!b` in `protocol.py` while Dart writes it with `setUint8`. New `PacketType` values must stay ≤ `0x7F` or the `struct.unpack` round-trip breaks.
- Action bytes are a shared convention: clicks use `0 = press`, `1 = release`, `2 = full click`; `KEY_PRESS` uses `0 = press`, `1 = release`.
- `KEY_PRESS.key_code` is a `u16`. Character keys travel as their **Unicode code point**. Keys with no text (Enter, arrows, Shift, F1…) travel as codes in the Unicode Private Use Area, defined by `SPECIAL_KEYS` in `protocol.py` and mirrored by `Packet._specialKeys` in `packet.dart`. `test_protocol.py::TestSpecialKeys::test_dart_client_mirrors_the_same_codes` fails if the two drift apart. Codes below `0x20` and unmapped PUA codes are dropped by `InputHandler.resolve_key` rather than typed.
- A whole TCP frame must fit the `u16` length prefix, so `Packet.wrapTcp` rejects payloads over `0xFFFF` and `keyText` truncates at `maxTextBytes` (`0xFFFF - 3`), on a UTF-8 character boundary. `setUint16` truncates silently, so an oversized frame would declare a bogus length and desynchronise the stream.

### Server pipeline

`openmouse.py:run_server()` wires the components:

1. `InputHandler` (`input_handler.py`) — wraps `pynput` for mouse/keyboard/media key emulation. The only module that touches OS input.
2. `UdpServer` / `TcpServer` (`network.py`) — asyncio listeners. They parse packets via `protocol.parse_*_packet` and dispatch into `InputHandler`. `_dispatch` is a coroutine because `type_text` goes through `run_in_executor` — pynput types character by character and would otherwise freeze the cursor for the length of the phrase. `TcpServer` tracks live clients in `_clients`; `on_client_disconnected` only fires when the last one leaves, so the tray does not claim "waiting" while another client is still connected.
3. `Discovery` (`discovery.py`) — publishes `_openmouse._tcp.local.` via zeroconf so the Android app finds the PC automatically. `run_server` awaits `start_async()`, which runs the blocking `register_service()` in an executor and returns the LAN IP. mDNS is a convenience, not a requirement: a failed registration is logged and the server keeps serving for manual-IP connections.
4. `Tray` (`tray.py`) — pystray icon with status text, Quit, and Uninstall menu items. Runs in its own thread; communicates back via callbacks (`on_quit`, `on_uninstall`). Imported lazily inside `run_server` and entirely optional — on a desktop without GTK/appindicator `import pystray` raises, and that must not stop the server.
5. `notify` (`notifications.py`) — desktop alert when the phone connects, fired from `on_connect` in `run_server`. Backends are tried in platform order and the tray balloon is the last resort, never the first: on Windows `Shell_NotifyIcon` **returns success and shows nothing** when the app has no registered `AppUserModelID`, so trusting pystray there silently loses every alert (verified against `wpndatabase.db` — pystray attempts left no rows, WinRT toasts did). Windows therefore goes through a WinRT toast launched via `powershell -EncodedCommand`, borrowing PowerShell's own AppID; Linux goes through `notify-send`. Alert text travels in environment variables, never on the command line, so nothing has to be escaped and nothing can be injected into the PowerShell script. External processes run on a throwaway thread (the event loop must not block) with `CREATE_NO_WINDOW` so a console-less exe does not flash a terminal.

Two things about shutdown are easy to break:

- The tray menu runs on its own thread. `asyncio.Event.set()` from there marks the event but does **not** wake a loop parked in the selector, so Quit did nothing until unrelated network traffic arrived. Callbacks handed to the tray must go through `threadsafe_callback(loop, fn)`, which wraps them in `loop.call_soon_threadsafe`.
- `Server.wait_closed()` waits for the connection handlers, and `_handle_client` blocks forever in `readexactly`. `TcpServer.stop()` therefore closes the tracked client writers first — otherwise stopping with a phone connected never returns.

`Uninstall` sets a flag and stops, then `uninstall()` runs after the loop exits. Port binding and the wait are wrapped so ports and mDNS are always released.

### Install / uninstall — split by platform

The install path is **not** symmetric, and this is the part most likely to be misremembered:

- **Windows**: `openmouse.py` is the installer. `ensure_installed()` writes the frozen exe to `%APPDATA%/OpenMouse/openmouse.exe` and registers `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`. Both `ensure_installed()` and `_register_autostart()` return early on non-Windows.
- **Linux**: install is handled entirely by `scripts/install.sh` (`curl … | sh`). It resolves the right release asset for `x86_64`/`aarch64` from the GitHub API, drops the binary in `~/.local/share/openmouse/`, and writes `~/.config/autostart/openmouse.desktop`. No sudo, nothing outside `$HOME`.

Uninstall lives in *both* places: `uninstall()` in `openmouse.py` (invoked from the tray menu, handles Windows registry + Linux `.desktop`) and `scripts/uninstall.sh` for the terminal path. Both self-delete their own install directory via a detached process that sleeps 2s first, because the running binary lives inside the directory being removed.

The install paths (`~/.local/share/openmouse`, `~/.config/autostart/openmouse.desktop`) are hardcoded in three places — `get_install_dir()`, `install.sh`, `uninstall.sh`. Change them in lockstep.

`getattr(sys, "frozen", False)` distinguishes a PyInstaller-built exe from a `python openmouse.py` dev run.

### App structure (`app/lib/`)

- `services/connection_service.dart` — owns the UDP socket and TCP `Socket`, exposes send-mouse/send-key methods.
- `services/discovery_service.dart` — wraps `bonsoir` to find `_openmouse._tcp.local.`.
- `screens/home_screen.dart` — picks a discovered server or accepts a manual IP.
- `screens/control_screen.dart` — bottom-nav shell hosting `widgets/trackpad.dart`, `widgets/keyboard_input.dart`, `widgets/media_controls.dart`.

`Trackpad` uses a single scale recognizer for both cursor movement (one finger) and scrolling (two fingers): declaring `onPanUpdate` and `onScaleUpdate` on the same `GestureDetector` trips a Flutter assertion, since scale is a superset of pan.

When adding a new control, the path is: define `PacketType` value in both `protocol.py` and `packet.dart` → add encoder in `packet.dart` → add `parse_*_packet` branch in `protocol.py` → handle in `network.py` `_dispatch` / `_UdpProtocol.datagram_received` → add `InputHandler` method.

### Release pipeline

`.github/workflows/release.yml` fires on tags matching `v*.*.*` and produces four assets in one GitHub release: `openmouse-linux-x86_64`, `openmouse-linux-aarch64` (built on `ubuntu-24.04-arm`), `openmouse-windows-x86_64.exe`, and `openmouse-android.apk`.

`scripts/install.sh` reads the **latest** release and greps for `openmouse-linux-${ARCH}` — renaming a release asset breaks the curl installer.

The APK job needs four repo secrets: `ANDROID_KEYSTORE_BASE64`, `ANDROID_KEYSTORE_PASSWORD`, `ANDROID_KEY_ALIAS`, `ANDROID_KEY_PASSWORD`. CI decodes them into `app/android/app/openmouse-release.jks` and `app/android/key.properties` at build time — neither file is ever committed.

## Project Conventions

- README, code comments and user-facing strings are in Spanish; code identifiers are English.
- Tests live in `server/tests/` (pytest + pytest-asyncio). The Flutter side uses default `flutter_test` in `app/test/`.
- The server is intentionally dependency-light. Don't add heavy frameworks — it must build to a small standalone exe.
- No backwards-compatibility for the wire protocol is required yet; both client and server ship together. Still, change them in lockstep.
- Design docs go to `docs/superpowers/specs/`, implementation plans to `docs/superpowers/plans/`, both named `YYYY-MM-DD-<slug>.md`.
