import types

from utils.obs_control import ObsController
import importlib
from utils.obs_health import ObsHealth

obs_health_module = importlib.import_module("utils.obs_health")


def test_obs_controller_invokes_client(monkeypatch):
    class DummyClient:
        def __init__(self):
            self.calls = []

        def start_record(self):
            self.calls.append("start")

        def pause_record(self):
            self.calls.append("pause")

        def resume_record(self):
            self.calls.append("resume")

        def stop_record(self):
            self.calls.append("stop")

    oc = ObsController()
    oc._client = DummyClient()  # bypass connection
    oc.start_record()
    oc.pause_record()
    oc.resume_record()
    oc.stop_record()
    assert oc._client.calls == ["start", "pause", "resume", "stop"]


def test_obs_controller_hotkey_fallback(monkeypatch):
    sent: list[tuple[str, ...]] = []
    monkeypatch.setattr(
        "utils.obs_control.pyautogui",
        types.SimpleNamespace(hotkey=lambda *c: sent.append(c)),
        raising=False,
    )
    oc = ObsController()

    def boom(_func):
        raise RuntimeError

    monkeypatch.setattr(oc, "_with_client", boom, raising=True)
    oc.start_record()
    assert sent == [("f9",)]


def test_obs_health(monkeypatch):
    class SockOK:
        def settimeout(self, t):
            pass

        def connect(self, addr):
            pass

        def close(self):
            pass

    class SockFail:
        def settimeout(self, t):
            pass

        def connect(self, addr):
            raise OSError

        def close(self):
            pass

    monkeypatch.setattr(
        obs_health_module, "socket", types.SimpleNamespace(socket=lambda: SockOK())
    )
    h = ObsHealth()
    assert h.healthy()
    monkeypatch.setattr(
        obs_health_module, "socket", types.SimpleNamespace(socket=lambda: SockFail())
    )
    assert not h.healthy()
