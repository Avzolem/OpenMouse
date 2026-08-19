# Linux install via `curl | sh` + CI release workflow

**Status**: approved (design)
**Date**: 2026-04-29

## Goal

Make OpenMouse installable on Linux through a single terminal command:

```sh
curl -fsSL https://raw.githubusercontent.com/Avzolem/OpenMouse/master/scripts/install.sh | sh
```

The Windows experience (download `.exe`, run) stays unchanged. Both binaries are produced automatically by GitHub Actions on every release tag.

## Non-Goals

- macOS / iOS support.
- System-wide installs (`/usr/local`, `apt`, snap, flatpak). User-local only.
- Wayland-specific input emulation. We rely on `pynput` defaults; if the user is on Wayland and input doesn't work, they get the same behavior as today — out of scope for this work.
- Cross-compilation. Each binary is built on its native runner.

## Architecture

Three independent pieces:

1. **CI release workflow** — builds binaries for 3 targets, publishes to GitHub Releases.
2. **Install / uninstall scripts** — POSIX shell scripts in `scripts/` that the user invokes via `curl | sh`.
3. **Server code refactor** — `ensure_installed()` becomes Windows-only; `uninstall()` Linux branch fixed.

These are loosely coupled: the scripts depend only on the asset naming convention from CI; the server code change is independent of both.

## 1. CI Release Workflow

### File: `.github/workflows/release.yml`

Trigger: push of a tag matching `v*.*.*`.

Three matrix jobs build in parallel, then a final `release` job aggregates artifacts and publishes the GitHub Release.

| Job ID | Runner | Output filename |
|---|---|---|
| `build-linux-x86_64` | `ubuntu-latest` | `openmouse-linux-x86_64` |
| `build-linux-aarch64` | `ubuntu-24.04-arm` | `openmouse-linux-aarch64` |
| `build-windows-x86_64` | `windows-latest` | `openmouse-windows-x86_64.exe` |

### Build steps (per job)

1. `actions/checkout@v4`
2. `actions/setup-python@v5` with Python 3.11
3. `pip install -r server/requirements.txt pyinstaller`
4. `pyinstaller server/openmouse.spec` (run from `server/` to keep relative paths working)
5. Rename `dist/openmouse` (or `dist/openmouse.exe`) to the canonical asset name listed above
6. `actions/upload-artifact@v4` — upload renamed binary

### Release job

- `needs: [build-linux-x86_64, build-linux-aarch64, build-windows-x86_64]`
- `actions/download-artifact@v4` — pulls all three
- `softprops/action-gh-release@v2` — creates the Release for the tag, attaches the three binaries
- Permissions: `contents: write`

### User flow to release

```sh
git tag v1.2.3
git push --tags
```

CI handles the rest. The Release page on GitHub will show three downloadable assets with the canonical names.

## 2. Install / Uninstall Scripts

### Asset naming contract

The scripts depend on this exact contract — changing it breaks the curl-pipe-sh URL for every existing user:

- Linux x86_64 → `openmouse-linux-x86_64`
- Linux aarch64 → `openmouse-linux-aarch64`
- Windows x86_64 → `openmouse-windows-x86_64.exe`

### File: `scripts/install.sh`

POSIX `sh`, no bashisms. `set -eu` at the top. Dependencies assumed present on any Linux desktop: `curl`, `uname`, `mkdir`, `chmod`, `cat`, `pkill`, `nohup`, `grep`, `cut`. No `jq`.

**Constants:**

```sh
REPO="Avzolem/OpenMouse"
INSTALL_DIR="$HOME/.local/share/openmouse"
BIN_PATH="$INSTALL_DIR/openmouse"
AUTOSTART="$HOME/.config/autostart/openmouse.desktop"
```

**Steps:**

1. **Detect arch** — `case "$(uname -m)"` mapping `x86_64 → x86_64`, `aarch64|arm64 → aarch64`. Anything else: print "Unsupported architecture: $(uname -m)" and exit 1.

2. **Resolve download URL** — `curl -fsSL https://api.github.com/repos/$REPO/releases/latest | grep "browser_download_url.*openmouse-linux-${ARCH}\"" | cut -d '"' -f 4`. If empty, print "No release found for $ARCH. Has a release been published yet?" and exit 1.

3. **Stop running instance** — `pkill -x openmouse 2>/dev/null || true`. Required because we're about to overwrite the binary.

4. **Download** — `mkdir -p "$INSTALL_DIR"` then `curl -fsSL -o "$BIN_PATH" "$URL"` then `chmod +x "$BIN_PATH"`.

5. **Write autostart entry** — `mkdir -p "$(dirname "$AUTOSTART")"` then write the heredoc:

   ```
   [Desktop Entry]
   Type=Application
   Name=OpenMouse
   Exec=$BIN_PATH
   Hidden=false
   NoDisplay=false
   X-GNOME-Autostart-enabled=true
   ```

6. **Launch** — `nohup "$BIN_PATH" >/dev/null 2>&1 &` and print "OpenMouse installed and running. Look for the green icon in your tray for your PC's IP."

### Idempotence

Re-running `install.sh` is the supported update path. Step 3 stops the old instance, step 4 overwrites the binary, step 5 reasserts the autostart entry. No separate `update.sh` script.

### File: `scripts/uninstall.sh`

Same shell, same assumptions. Steps:

1. `pkill -x openmouse 2>/dev/null || true`
2. `rm -rf "$INSTALL_DIR"`
3. `rm -f "$AUTOSTART"`
4. Print "OpenMouse removed."

The user invokes it with the same pipe pattern, swapping `install.sh` for `uninstall.sh`.

## 3. Server code changes (`server/openmouse.py`)

### `ensure_installed()` becomes Windows-only

Currently the function copies the running exe to the install dir, copies `icon.png`, and calls `_register_autostart()`. On Linux this duplicates what `install.sh` already did, and worse, runs every launch.

After the change:

```python
def ensure_installed():
    if sys.platform != "win32":
        return
    # ... existing Windows logic unchanged
```

`_register_autostart()` likewise becomes Windows-only (the Linux branch is dead code now — `install.sh` writes the `.desktop`).

### `uninstall()` Linux branch — fix self-deletion

Current Linux branch:

```python
install_dir = get_install_dir()
if install_dir.exists():
    current = get_exe_path().resolve()
    if not current.is_relative_to(install_dir):
        shutil.rmtree(install_dir)
```

Bug: when the binary is launched from `~/.local/share/openmouse/openmouse` (the normal post-install case), `is_relative_to` returns True and the dir is **never deleted**. The tray "Uninstall" silently leaves the install dir in place.

Fix: mirror the Windows pattern. Spawn a detached shell that waits a couple seconds, then removes the dir, then exits — letting the running process release its file lock first:

```python
import subprocess
detach_script = f'sleep 2 && rm -rf "{install_dir}"'
subprocess.Popen(
    ["sh", "-c", detach_script],
    start_new_session=True,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)
```

The desktop entry is still removed inline (it's not the file being executed). Then the process exits via the existing `stop_event.set()` path.

### What stays unchanged

- `network.py`, `protocol.py`, `input_handler.py`, `discovery.py`, `tray.py`.
- `openmouse.spec` — same spec file works on all three runners; PyInstaller picks up the host platform.

## 4. README updates

In the "Instalación → Servidor → Linux" section, replace the current `git clone + pip install` instructions with:

```sh
curl -fsSL https://raw.githubusercontent.com/Avzolem/OpenMouse/master/scripts/install.sh | sh
```

Keep the "Opción 2: Desde el código fuente" block for developers. Add a "Desinstalar" subsection mentioning both the tray "Uninstall" item and the `uninstall.sh` one-liner.

The Windows section stays exactly as it is — download `.exe`, run.

## Testing strategy

The new code is mostly shell + CI config, neither of which fits well into pytest. Verification is manual + observational:

1. **CI workflow** — push a throwaway tag (`v0.0.0-test1`) to a fork or a draft branch. Confirm all three jobs succeed and the Release page shows the three binaries with the canonical names. Delete the test release after.
2. **`install.sh`** — run it on a clean Linux VM (or Docker container with a desktop). Confirm:
   - Binary lands at `~/.local/share/openmouse/openmouse` and is executable.
   - `~/.config/autostart/openmouse.desktop` exists with the right `Exec=`.
   - Tray icon appears, server is reachable from the Android app.
   - Re-running `install.sh` updates the binary without errors and the running server is replaced.
3. **`uninstall.sh`** — run after install. Confirm binary, dir, and `.desktop` are gone, and no `openmouse` process is running.
4. **Tray "Uninstall" on Linux** — install via script, then click Uninstall in tray. Confirm `~/.local/share/openmouse/` is gone after a few seconds (tests the self-deletion fix).
5. **Existing pytest suite in `server/tests/`** — keep passing; the only Python change is wrapping `ensure_installed()` and modifying `uninstall()`, both of which are not currently covered by tests and don't affect protocol/network/input behavior.

## Risks / Open Questions

- **GitHub-hosted ARM runners** — `ubuntu-24.04-arm` is generally available since 2025 for public repos. If for some reason it's unavailable for this account, fallback is QEMU emulation (`uraimo/run-on-arch-action`) — slower but works on `ubuntu-latest`.
- **Wayland sessions** — `pynput` may not work for input synthesis under Wayland compositors. Out of scope; users on Wayland will see no error in the install flow but mouse events won't move the cursor. A diagnostics flag can be added later.
- **AppIndicator on minimal DEs** — `pystray` needs a tray host. Most major DEs have one; minimal WMs (i3, sway) may not. Out of scope; user can fall back to running headless if needed (the server still works without the tray, just without status feedback).
