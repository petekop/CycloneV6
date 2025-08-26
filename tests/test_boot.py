import time

import pytest

from boot_state import get_boot_state

pytest.importorskip("flask")
from flask import Flask  # noqa: E402

from routes.boot_status import boot_status_bp  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr("routes.boot_status.BASE_DIR", tmp_path, raising=False)
    monkeypatch.setattr("routes.boot_status.STATE_DIR", tmp_path / "state", raising=False)
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(boot_status_bp, url_prefix="/api/boot")
    with app.test_client() as client:
        yield client


def test_boot_start_triggers_services(client, monkeypatch):
    calls = []

    def fake_popen(cmd, *args, **kwargs):
        calls.append(cmd)

        class Dummy:
            pass

        return Dummy()

    monkeypatch.setattr("routes.boot_status.subprocess.Popen", fake_popen)
    resp = client.post("/api/boot/start")
    assert resp.status_code == 200
    assert calls == [["hr_daemon"], ["mediamtx"], ["obs"]]


def test_status_transitions_to_ready(client):
    client.post("/api/boot/start")
    state = get_boot_state()
    state["services"]["hr_daemon"] = "READY"
    state["services"]["mediamtx"] = "READY"
    resp = client.get("/api/boot/status")
    data = resp.get_json()
    assert data["ready"] is True
    assert data["progress"] == 100


def _launcher(client, timeout=0.05, interval=0.01):
    client.post("/api/boot/start")
    deadline = time.time() + timeout
    while time.time() < deadline:
        if client.get("/api/boot/status").get_json().get("ready"):
            return 0
        time.sleep(interval)
    raise SystemExit(1)


def test_timeout_reports_error_state(client, monkeypatch):
    monkeypatch.setattr("routes.boot_status.subprocess.Popen", lambda *a, **k: None)
    with pytest.raises(SystemExit) as exc:
        _launcher(client, timeout=0.01, interval=0.005)
    assert exc.value.code == 1
