import notifications


class _FakeTray:
    def __init__(self, result=True, boom=False):
        self.result = result
        self.boom = boom
        self.calls = []

    def notify(self, title, message):
        self.calls.append((title, message))
        if self.boom:
            raise NotImplementedError("este backend no notifica")
        return self.result


class TestNotify:
    def setup_method(self):
        # El aviso de "sin backend" solo sale una vez por proceso.
        notifications._warned = False

    def _silence(self, monkeypatch, **overrides):
        """Deja los backends del sistema inertes salvo los que se pidan."""
        monkeypatch.setattr(notifications, "_notify_send",
                            overrides.get("notify_send", lambda t, m: False))
        monkeypatch.setattr(notifications, "_toast_windows",
                            overrides.get("toast_windows", lambda t, m: False))

    def test_the_system_backend_wins_over_the_tray(self, monkeypatch):
        seen = []
        self._silence(monkeypatch,
                      notify_send=lambda t, m: seen.append((t, m)) or True)
        monkeypatch.setattr(notifications, "is_windows", lambda: False)
        tray = _FakeTray()
        assert notifications.notify("t", "m", tray=tray) is True
        assert seen == [("t", "m")]
        # El globo del tray es el ultimo recurso: Windows lo descarta en
        # silencio, asi que no puede ser el camino principal.
        assert tray.calls == []

    def test_falls_back_to_the_tray_when_nothing_else_works(self, monkeypatch):
        self._silence(monkeypatch)
        tray = _FakeTray()
        assert notifications.notify("t", "m", tray=tray) is True
        assert tray.calls == [("t", "m")]

    def test_a_tray_that_raises_does_not_propagate(self, monkeypatch):
        self._silence(monkeypatch)
        assert notifications.notify("t", "m", tray=_FakeTray(boom=True)) is False

    def test_without_any_backend_it_reports_failure_quietly(self, monkeypatch):
        self._silence(monkeypatch)
        assert notifications.notify("t", "m", tray=None) is False

    def test_a_broken_backend_does_not_propagate(self, monkeypatch):
        def boom(title, message):
            raise OSError("no se pudo lanzar")

        self._silence(monkeypatch, notify_send=boom, toast_windows=boom)
        assert notifications.notify("t", "m", tray=None) is False

    def test_on_windows_the_toast_is_tried_first(self, monkeypatch):
        order = []
        monkeypatch.setattr(notifications, "is_windows", lambda: True)
        monkeypatch.setattr(notifications, "_toast_windows",
                            lambda t, m: order.append("toast") or True)
        monkeypatch.setattr(notifications, "_notify_send",
                            lambda t, m: order.append("notify-send") or True)
        assert notifications.notify("t", "m") is True
        assert order == ["toast"]


class TestNotifySend:
    def test_returns_false_when_the_binary_is_missing(self, monkeypatch):
        monkeypatch.setattr(notifications, "is_windows", lambda: False)
        monkeypatch.setattr(notifications.shutil, "which", lambda _: None)
        assert notifications._notify_send("t", "m") is False

    def test_is_skipped_on_windows(self, monkeypatch):
        monkeypatch.setattr(notifications, "is_windows", lambda: True)
        assert notifications._notify_send("t", "m") is False

    def test_passes_app_name_and_the_texts(self, monkeypatch):
        launched = []
        monkeypatch.setattr(notifications, "is_windows", lambda: False)
        monkeypatch.setattr(notifications.shutil, "which",
                            lambda _: "/usr/bin/notify-send")
        monkeypatch.setattr(notifications, "_run_detached",
                            lambda argv, **kw: launched.append(argv))
        assert notifications._notify_send("titulo", "mensaje") is True
        argv = launched[0]
        assert argv[0] == "/usr/bin/notify-send"
        assert "--app-name=OpenMouse" in argv
        assert argv[-2:] == ["titulo", "mensaje"]


class TestIconPath:
    def test_resolves_next_to_the_module_when_not_frozen(self):
        assert notifications.icon_path().name == "icon.png"




class TestToastWindows:
    def test_is_skipped_off_windows(self, monkeypatch):
        monkeypatch.setattr(notifications, "is_windows", lambda: False)
        assert notifications._toast_windows("t", "m") is False

    def test_sends_the_texts_by_environment_not_by_argument(self, monkeypatch):
        """El texto va por entorno para que no haya que escapar comillas."""
        launched = []
        monkeypatch.setattr(notifications, "is_windows", lambda: True)
        monkeypatch.setattr(notifications.shutil, "which",
                            lambda _: "powershell.exe")
        monkeypatch.setattr(notifications, "_run_detached",
                            lambda argv, env_extra=None: launched.append((argv, env_extra)))

        evil = 'x\'; Remove-Item C:\\ -Recurse; \''
        assert notifications._toast_windows("OpenMouse", evil) is True
        argv, env = launched[0]
        assert "-EncodedCommand" in argv
        assert env["OPENMOUSE_TOAST_MESSAGE"] == evil
        # Nada del texto acaba en la linea de comandos.
        assert not any(evil in part for part in argv)

    def test_the_encoded_script_is_valid_utf16(self, monkeypatch):
        import base64
        launched = []
        monkeypatch.setattr(notifications, "is_windows", lambda: True)
        monkeypatch.setattr(notifications.shutil, "which", lambda _: "powershell.exe")
        monkeypatch.setattr(notifications, "_run_detached",
                            lambda argv, env_extra=None: launched.append(argv))
        notifications._toast_windows("t", "m")
        argv = launched[0]
        script = base64.b64decode(argv[argv.index("-EncodedCommand") + 1]).decode("utf-16-le")
        assert "ToastNotificationManager" in script
        assert "APP_ID" not in script
