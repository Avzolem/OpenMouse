# Linux install via `curl | sh` + CI release workflow — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make OpenMouse installable on Linux with a single `curl | sh` command, backed by automated multi-platform builds in GitHub Actions.

**Architecture:** Three loosely-coupled pieces — (1) GitHub Actions workflow that builds Linux x86_64, Linux aarch64, and Windows x86_64 binaries on tag push and publishes them as a Release with canonical names; (2) POSIX `install.sh` / `uninstall.sh` scripts in `scripts/` that the user invokes via curl; (3) refactor `server/openmouse.py` so `ensure_installed()` is Windows-only and the Linux branch of `uninstall()` actually deletes the install dir.

**Tech Stack:** Python 3.11+, PyInstaller, GitHub Actions (`ubuntu-latest`, `ubuntu-24.04-arm`, `windows-latest`), POSIX `sh`, pytest + pytest-asyncio.

**Spec:** `docs/superpowers/specs/2026-04-29-linux-install-curl-design.md`

---

## Project Conventions (read first)

- **No commits without explicit user authorization.** Per `~/.claude/CLAUDE.md`, every commit step in this plan is **"ask the user first"** — do not run `git commit` automatically. Group changes logically per task and pause for approval.
- **Commit message style:** match recent history (e.g. `feat(server): ...`, `feat: ...`, `docs: ...`, `fix: ...`). No `Co-Authored-By: Claude` line, no `🤖 Generated with` line.
- **No push without explicit "push" command from user.**
- Tests run from `server/` directory: `cd server && pytest`.
- The `server/openmouse.spec` PyInstaller config sits in `server/`. PyInstaller must be invoked from there so `datas=[('icon.png', '.')]` resolves correctly.

---

## File Structure

**New files:**

- `.github/workflows/release.yml` — CI workflow, three matrix builds + release job
- `scripts/install.sh` — POSIX install script, target of `curl | sh`
- `scripts/uninstall.sh` — POSIX uninstall script
- `server/tests/test_openmouse.py` — unit tests for `ensure_installed()` platform gating and `uninstall()` Linux self-deletion fix

**Modified files:**

- `server/openmouse.py` — wrap `ensure_installed()` and `_register_autostart()` to be Windows-only; rewrite Linux branch of `uninstall()` to use detached `sh -c` for self-deletion (mirroring the Windows `.bat` pattern)
- `README.md` — replace Linux install instructions with `curl | sh` one-liner; add Desinstalar subsection

**Files NOT touched:** `server/network.py`, `server/protocol.py`, `server/input_handler.py`, `server/discovery.py`, `server/tray.py`, `server/openmouse.spec`, anything in `app/`.

---

## Task 1: Make `ensure_installed()` and `_register_autostart()` Windows-only

**Why first:** Smallest, lowest-risk change. Pure platform gating. Sets up the test file other tasks will reuse.

**Files:**
- Create: `server/tests/test_openmouse.py`
- Modify: `server/openmouse.py:47-95` (the two functions)

- [ ] **Step 1.1: Write the failing tests**

Create `server/tests/test_openmouse.py`:

```python
import sys
from unittest.mock import patch, MagicMock
import pytest


class TestEnsureInstalled:
    def test_returns_early_on_linux(self, tmp_path, monkeypatch):
        monkeypatch.setattr(sys, "platform", "linux")
        monkeypatch.setattr("openmouse.get_install_dir", lambda: tmp_path / "install")
        with patch("openmouse.shutil.copy2") as mock_copy, \
             patch("openmouse._register_autostart") as mock_reg:
            from openmouse import ensure_installed
            assert ensure_installed() is None
            mock_copy.assert_not_called()
            mock_reg.assert_not_called()

    def test_returns_early_on_macos(self, tmp_path, monkeypatch):
        monkeypatch.setattr(sys, "platform", "darwin")
        monkeypatch.setattr("openmouse.get_install_dir", lambda: tmp_path / "install")
        with patch("openmouse._register_autostart") as mock_reg:
            from openmouse import ensure_installed
            assert ensure_installed() is None
            mock_reg.assert_not_called()


class TestRegisterAutostart:
    def test_returns_early_on_linux(self, tmp_path, monkeypatch):
        monkeypatch.setattr(sys, "platform", "linux")
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        from openmouse import _register_autostart
        _register_autostart(tmp_path / "openmouse")
        # Should not have created the .desktop file
        assert not (tmp_path / ".config" / "autostart" / "openmouse.desktop").exists()
```

Note: we deliberately don't add a "runs on Windows" test. Windows behavior is unchanged by this refactor and exercising the real `winreg` / `shutil.copy2` paths under mocks is brittle. We're testing the **new** behavior — early return on non-Windows.

- [ ] **Step 1.2: Run tests to verify they fail**

```
cd server && pytest tests/test_openmouse.py -v
```

Expected: `test_returns_early_on_linux` for both classes FAIL because the current implementation does Linux work.

- [ ] **Step 1.3: Wrap `ensure_installed()` to be Windows-only**

Edit `server/openmouse.py`. Replace the body of `ensure_installed()` (lines 47-71) with a Windows-gated version:

```python
def ensure_installed():
    """Install silently if not already running from install dir. Returns installed exe path. Windows-only — Linux is handled by scripts/install.sh."""
    if sys.platform != "win32":
        return None

    install_dir = get_install_dir()
    install_dir.mkdir(parents=True, exist_ok=True)

    src = get_exe_path()

    if getattr(sys, "frozen", False):
        dest = install_dir / src.name
        if src.resolve() != dest.resolve():
            shutil.copy2(src, dest)
            logger.info(f"Installed to: {dest}")
        else:
            dest = src
    else:
        dest = src

    icon_src = Path(__file__).parent / "icon.png"
    icon_dest = install_dir / "icon.png"
    if icon_src.exists() and icon_src.resolve() != icon_dest.resolve():
        shutil.copy2(icon_src, icon_dest)

    _register_autostart(dest)
    return dest
```

- [ ] **Step 1.4: Strip Linux branch from `_register_autostart()`**

Replace the function body (lines 74-95) with:

```python
def _register_autostart(exe_path: Path):
    """Register the executable to start on login. Windows-only — Linux is handled by scripts/install.sh."""
    if sys.platform != "win32":
        return
    import winreg
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY, 0, winreg.KEY_SET_VALUE)
    winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, str(exe_path))
    winreg.CloseKey(key)
    logger.info("Registered in Windows startup.")
```

- [ ] **Step 1.5: Update the entry point**

The `if __name__ == "__main__":` block at line 193 calls `ensure_installed()` unconditionally. That stays — `ensure_installed()` now no-ops on Linux internally. No change needed.

- [ ] **Step 1.6: Run tests to verify they pass**

```
cd server && pytest tests/test_openmouse.py -v
```

Expected: PASS for all 3 tests in this task.

- [ ] **Step 1.7: Run full server test suite**

```
cd server && pytest -v
```

Expected: all existing tests still PASS (we didn't touch protocol/network/input).

- [ ] **Step 1.8: Pause for commit authorization**

Suggested commit:

```
git add server/openmouse.py server/tests/test_openmouse.py
git commit -m "refactor(server): make ensure_installed Windows-only

Linux installation will be handled by scripts/install.sh.
ensure_installed() and _register_autostart() now no-op on
non-Windows platforms."
```

Ask the user before running.

---

## Task 2: Fix Linux self-deletion bug in `uninstall()`

**Why second:** Same file, related concern, builds on Task 1's test infrastructure. Must be done before publishing the install scripts so users uninstalling via tray actually get a clean removal.

**Bug:** Current code at `server/openmouse.py:135-137`:
```python
current = get_exe_path().resolve()
if not current.is_relative_to(install_dir):
    shutil.rmtree(install_dir)
```
When the binary runs from `~/.local/share/openmouse/`, `is_relative_to(install_dir)` is `True`, so `shutil.rmtree` is **skipped** and the install dir is never removed.

**Fix:** Mirror the Windows `.bat` detached-deletion pattern with a `sh -c "sleep 2 && rm -rf <dir>"` spawned via `subprocess.Popen` with `start_new_session=True`.

**Files:**
- Modify: `server/openmouse.py:127-138` (Linux branch of `uninstall()`)
- Modify: `server/tests/test_openmouse.py` (add new test class)

- [ ] **Step 2.1: Write the failing test**

Append to `server/tests/test_openmouse.py`:

```python
class TestUninstallLinux:
    def test_schedules_detached_removal_of_install_dir(self, tmp_path, monkeypatch):
        install_dir = tmp_path / "openmouse"
        install_dir.mkdir()
        (install_dir / "openmouse").write_text("fake binary")

        # The current uninstall() builds the desktop path as
        # Path.home() / ".config" / "autostart" / "openmouse.desktop",
        # so create it at the same location relative to our fake home.
        autostart = tmp_path / ".config" / "autostart" / "openmouse.desktop"
        autostart.parent.mkdir(parents=True)
        autostart.write_text("entry")

        monkeypatch.setattr(sys, "platform", "linux")
        monkeypatch.setattr("openmouse.get_install_dir", lambda: install_dir)
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

        captured = []
        def fake_popen(cmd, **kwargs):
            captured.append((cmd, kwargs))
            return MagicMock()
        monkeypatch.setattr("subprocess.Popen", fake_popen)

        from openmouse import uninstall
        uninstall()

        # Autostart entry removed inline
        assert not autostart.exists()

        # Detached deletion scheduled
        assert len(captured) == 1
        cmd, kwargs = captured[0]
        assert cmd[0] == "sh"
        assert cmd[1] == "-c"
        assert "rm -rf" in cmd[2]
        assert str(install_dir) in cmd[2]
        assert kwargs.get("start_new_session") is True

    def test_no_op_when_nothing_installed(self, tmp_path, monkeypatch):
        monkeypatch.setattr(sys, "platform", "linux")
        monkeypatch.setattr("openmouse.get_install_dir", lambda: tmp_path / "missing")
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

        called = []
        monkeypatch.setattr(
            "subprocess.Popen",
            lambda cmd, **kw: called.append(cmd) or MagicMock(),
        )

        from openmouse import uninstall
        uninstall()  # should not raise
        assert called == []  # no removal scheduled if dir doesn't exist
```

- [ ] **Step 2.2: Run new tests to verify they fail**

```
cd server && pytest tests/test_openmouse.py::TestUninstallLinux -v
```

Expected: `test_schedules_detached_removal_of_install_dir` FAILS — current code calls `shutil.rmtree` directly (or skips it), not `subprocess.Popen`.

- [ ] **Step 2.3: Rewrite the Linux branch of `uninstall()`**

In `server/openmouse.py`, replace the `else:` branch (lines 127-138, after the `if sys.platform == "win32":` block) with:

```python
    else:
        desktop_entry = Path.home() / ".config" / "autostart" / "openmouse.desktop"
        if desktop_entry.exists():
            desktop_entry.unlink()
            logger.info("Removed from Linux autostart.")

        install_dir = get_install_dir()
        if install_dir.exists():
            # Schedule detached removal so we can delete the directory we're
            # currently running from. Mirrors the Windows .bat pattern.
            import subprocess
            subprocess.Popen(
                ["sh", "-c", f'sleep 2 && rm -rf "{install_dir}"'],
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            logger.info(f"Scheduled removal of: {install_dir}")
```

Note: the `import subprocess` already exists earlier in the function (Windows branch). Keep the local import in the Linux branch only if subprocess is not already imported at module top — currently it isn't, so this local import is correct and matches the Windows branch style.

- [ ] **Step 2.4: Run new tests to verify they pass**

```
cd server && pytest tests/test_openmouse.py::TestUninstallLinux -v
```

Expected: PASS for both tests.

- [ ] **Step 2.5: Run full suite**

```
cd server && pytest -v
```

Expected: all PASS.

- [ ] **Step 2.6: Pause for commit authorization**

Suggested commit:

```
git add server/openmouse.py server/tests/test_openmouse.py
git commit -m "fix(server): linux uninstall actually removes install dir

The previous code skipped rmtree when the running exe lived inside
the install dir, which is the normal post-install case. Now schedules
a detached 'sh -c sleep 2 && rm -rf' that runs after the process
exits, mirroring the Windows .bat self-deletion pattern."
```

Ask the user.

---

## Task 3: Create `scripts/install.sh`

**Files:**
- Create: `scripts/install.sh`

No automated tests — POSIX shell with no shellcheck setup in repo. Verification is manual (Step 3.4).

- [ ] **Step 3.1: Create the scripts directory**

```
mkdir -p /home/avsolem/sites/openmouse/scripts
```

- [ ] **Step 3.2: Write `scripts/install.sh`**

Create `scripts/install.sh` with this exact content:

```sh
#!/usr/bin/env sh
# OpenMouse Linux installer.
# Usage: curl -fsSL https://raw.githubusercontent.com/Avzolem/OpenMouse/master/scripts/install.sh | sh
set -eu

REPO="Avzolem/OpenMouse"
INSTALL_DIR="$HOME/.local/share/openmouse"
BIN_PATH="$INSTALL_DIR/openmouse"
AUTOSTART="$HOME/.config/autostart/openmouse.desktop"

# 1. Detect architecture
case "$(uname -m)" in
    x86_64)
        ARCH="x86_64"
        ;;
    aarch64|arm64)
        ARCH="aarch64"
        ;;
    *)
        echo "OpenMouse: unsupported architecture: $(uname -m)" >&2
        echo "Supported: x86_64, aarch64" >&2
        exit 1
        ;;
esac

ASSET="openmouse-linux-${ARCH}"
echo "OpenMouse: detected ${ARCH}, looking for ${ASSET}..."

# 2. Resolve download URL from the latest release
URL=$(
    curl -fsSL "https://api.github.com/repos/${REPO}/releases/latest" \
        | grep "browser_download_url.*${ASSET}\"" \
        | head -n 1 \
        | cut -d '"' -f 4
)

if [ -z "$URL" ]; then
    echo "OpenMouse: no release asset found for ${ARCH}." >&2
    echo "Check https://github.com/${REPO}/releases" >&2
    exit 1
fi

# 3. Stop any running instance (we are about to overwrite the binary)
pkill -x openmouse 2>/dev/null || true

# 4. Download
mkdir -p "$INSTALL_DIR"
echo "OpenMouse: downloading from $URL"
curl -fsSL -o "$BIN_PATH" "$URL"
chmod +x "$BIN_PATH"

# 5. Autostart entry
mkdir -p "$(dirname "$AUTOSTART")"
cat > "$AUTOSTART" <<EOF
[Desktop Entry]
Type=Application
Name=OpenMouse
Exec=$BIN_PATH
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
EOF

# 6. Launch
nohup "$BIN_PATH" >/dev/null 2>&1 &

echo ""
echo "OpenMouse installed and running."
echo "Look for the green icon in your system tray — it shows your PC's IP."
echo "To uninstall: curl -fsSL https://raw.githubusercontent.com/${REPO}/master/scripts/uninstall.sh | sh"
```

- [ ] **Step 3.3: Make it executable**

```
chmod +x /home/avsolem/sites/openmouse/scripts/install.sh
```

- [ ] **Step 3.4: Manual smoke test of the script structure**

Run a dry-syntax check (will fail at the API call since no release exists yet, but should at least pass shell parsing and arch detection):

```
sh -n /home/avsolem/sites/openmouse/scripts/install.sh
```

Expected: no output (syntax OK).

Then verify arch detection works in isolation:

```
sh -c 'case "$(uname -m)" in x86_64) echo OK x86_64 ;; aarch64|arm64) echo OK aarch64 ;; *) echo BAD ;; esac'
```

Expected: `OK x86_64` (or aarch64 depending on host).

Full end-to-end test (download + run) is deferred to Task 5 once CI publishes a real release.

- [ ] **Step 3.5: Pause for commit authorization**

Suggested commit:

```
git add scripts/install.sh
git commit -m "feat: add Linux install script for curl | sh

POSIX sh, user-local, no sudo. Detects x86_64/aarch64,
downloads matching binary from latest GitHub Release,
writes autostart entry, launches the server."
```

Ask the user.

---

## Task 4: Create `scripts/uninstall.sh`

**Files:**
- Create: `scripts/uninstall.sh`

- [ ] **Step 4.1: Write `scripts/uninstall.sh`**

```sh
#!/usr/bin/env sh
# OpenMouse Linux uninstaller.
# Usage: curl -fsSL https://raw.githubusercontent.com/Avzolem/OpenMouse/master/scripts/uninstall.sh | sh
set -eu

INSTALL_DIR="$HOME/.local/share/openmouse"
AUTOSTART="$HOME/.config/autostart/openmouse.desktop"

pkill -x openmouse 2>/dev/null || true
rm -rf "$INSTALL_DIR"
rm -f "$AUTOSTART"

echo "OpenMouse removed."
```

- [ ] **Step 4.2: Make it executable**

```
chmod +x /home/avsolem/sites/openmouse/scripts/uninstall.sh
```

- [ ] **Step 4.3: Syntax check**

```
sh -n /home/avsolem/sites/openmouse/scripts/uninstall.sh
```

Expected: no output.

- [ ] **Step 4.4: Pause for commit authorization**

Suggested commit:

```
git add scripts/uninstall.sh
git commit -m "feat: add Linux uninstall script

Stops running instance, removes ~/.local/share/openmouse
and the autostart .desktop file."
```

Ask the user.

---

## Task 5: Create GitHub Actions release workflow

**Files:**
- Create: `.github/workflows/release.yml`

- [ ] **Step 5.1: Create the workflow directory**

```
mkdir -p /home/avsolem/sites/openmouse/.github/workflows
```

- [ ] **Step 5.2: Write `.github/workflows/release.yml`**

```yaml
name: Release

on:
  push:
    tags:
      - 'v*.*.*'

permissions:
  contents: write

jobs:
  build-linux-x86_64:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r server/requirements.txt
          pip install pyinstaller
      - name: Build
        working-directory: server
        run: pyinstaller openmouse.spec
      - name: Rename
        run: mv server/dist/openmouse server/dist/openmouse-linux-x86_64
      - uses: actions/upload-artifact@v4
        with:
          name: openmouse-linux-x86_64
          path: server/dist/openmouse-linux-x86_64

  build-linux-aarch64:
    runs-on: ubuntu-24.04-arm
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r server/requirements.txt
          pip install pyinstaller
      - name: Build
        working-directory: server
        run: pyinstaller openmouse.spec
      - name: Rename
        run: mv server/dist/openmouse server/dist/openmouse-linux-aarch64
      - uses: actions/upload-artifact@v4
        with:
          name: openmouse-linux-aarch64
          path: server/dist/openmouse-linux-aarch64

  build-windows-x86_64:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r server/requirements.txt
          pip install pyinstaller
      - name: Build
        working-directory: server
        run: pyinstaller openmouse.spec
      - name: Rename
        run: mv server/dist/openmouse.exe server/dist/openmouse-windows-x86_64.exe
      - uses: actions/upload-artifact@v4
        with:
          name: openmouse-windows-x86_64
          path: server/dist/openmouse-windows-x86_64.exe

  release:
    needs: [build-linux-x86_64, build-linux-aarch64, build-windows-x86_64]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/download-artifact@v4
        with:
          path: dist
          merge-multiple: true
      - name: Publish release
        uses: softprops/action-gh-release@v2
        with:
          files: |
            dist/openmouse-linux-x86_64
            dist/openmouse-linux-aarch64
            dist/openmouse-windows-x86_64.exe
          generate_release_notes: true
```

- [ ] **Step 5.3: Validate YAML syntax locally**

```
python3 -c "import yaml; yaml.safe_load(open('/home/avsolem/sites/openmouse/.github/workflows/release.yml'))"
```

Expected: no output, no exception.

- [ ] **Step 5.4: Pause for commit authorization**

Suggested commit:

```
git add .github/workflows/release.yml
git commit -m "ci: add release workflow for multi-platform builds

Builds openmouse for linux x86_64, linux aarch64, and
windows x86_64 in parallel on tag push (v*.*.*), then
publishes a GitHub Release with all three binaries
under canonical names that the install.sh script expects."
```

Ask the user.

- [ ] **Step 5.5: End-to-end verification (after user pushes a tag)**

This step requires a real release. Sequence the user runs:

1. `git tag v0.1.0 && git push --tags`
2. Wait for CI on https://github.com/Avzolem/OpenMouse/actions to finish (~5-10 min)
3. Confirm the Release page shows three assets:
   - `openmouse-linux-x86_64`
   - `openmouse-linux-aarch64`
   - `openmouse-windows-x86_64.exe`
4. On a Linux machine: `curl -fsSL https://raw.githubusercontent.com/Avzolem/OpenMouse/master/scripts/install.sh | sh` — confirm tray icon appears, Android app sees it.
5. Click "Uninstall" in the tray — wait 3 seconds, confirm `~/.local/share/openmouse/` is gone.
6. Re-install, then run the uninstall script — confirm same result.

If the ARM runner is unavailable on this account, fallback: replace the `runs-on: ubuntu-24.04-arm` job with QEMU-based emulation using `uraimo/run-on-arch-action@v2`. Don't add this preemptively; only if step 5.5 fails on that job.

---

## Task 6: Update README

**Files:**
- Modify: `README.md:100-107` (Linux/Source install block) and a new "Desinstalar" subsection

- [ ] **Step 6.1: Replace the Linux install instructions**

In `README.md`, find the section starting `#### Opción 2: Desde el código fuente` (around line 100) and **insert before it** a new Opción 1 for Linux. The current "Opción 1: Ejecutable" only mentions `openmouse.exe` for Windows. Restructure so it's clear which command is for which OS.

Find this block (around lines 96-107):

```markdown
#### Opción 1: Ejecutable (recomendado)

Descarga `openmouse.exe` desde [Releases](https://github.com/Avzolem/OpenMouse/releases) y ejecútalo. Se instala automáticamente y arranca al encender tu PC.

#### Opción 2: Desde el código fuente

```bash
git clone https://github.com/Avzolem/OpenMouse.git
cd OpenMouse/server
pip install -r requirements.txt
python openmouse.py
```
```

Replace with:

```markdown
#### Opción 1: Instalación rápida (recomendado)

**Windows:** Descarga `openmouse-windows-x86_64.exe` desde [Releases](https://github.com/Avzolem/OpenMouse/releases) y ejecútalo. Se instala automáticamente y arranca al encender tu PC.

**Linux (x86_64 y aarch64):**

```bash
curl -fsSL https://raw.githubusercontent.com/Avzolem/OpenMouse/master/scripts/install.sh | sh
```

Se descarga el binario, se registra en autostart, y arranca el server. Todo queda en `~/.local/share/openmouse/` — no usa sudo ni toca `/usr/local`.

#### Opción 2: Desde el código fuente

```bash
git clone https://github.com/Avzolem/OpenMouse.git
cd OpenMouse/server
pip install -r requirements.txt
python openmouse.py
```
```

- [ ] **Step 6.2: Update the "Desinstalar" subsection**

Find the existing block (around line 153):

```markdown
### Desinstalar
Click derecho en el tray icon → **Uninstall**. Se elimina el auto-inicio y los archivos.
```

Replace with:

```markdown
### Desinstalar

**Desde la app:** Click derecho en el tray icon → **Uninstall**. Se elimina el auto-inicio y los archivos.

**Linux por terminal:**

```bash
curl -fsSL https://raw.githubusercontent.com/Avzolem/OpenMouse/master/scripts/uninstall.sh | sh
```
```

- [ ] **Step 6.3: Pause for commit authorization**

Suggested commit:

```
git add README.md
git commit -m "docs: document Linux curl install + uninstall

Adds the curl | sh one-liner for Linux install (x86_64
and aarch64), updates Windows asset name to match the
new CI release naming, and documents both the tray and
script uninstall paths."
```

Ask the user.

---

## Done criteria

- [ ] All tasks 1-6 complete and committed (with user authorization).
- [ ] `cd server && pytest -v` — all green (existing tests + 5 new ones in `test_openmouse.py`).
- [ ] `sh -n scripts/install.sh && sh -n scripts/uninstall.sh` — both pass.
- [ ] `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/release.yml'))"` — no error.
- [ ] User has pushed a tag and confirmed the Release contains the three canonical-named assets.
- [ ] User has run `install.sh` end-to-end on a Linux machine and confirmed tray + Android app connection.
- [ ] User has run `uninstall.sh` (or tray Uninstall) and confirmed full removal.
