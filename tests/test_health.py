import types

import pytest

pytest.importorskip("flask")
from flask import Flask  # noqa: E402

import routes.health as health_module  # noqa: E402


def test_health_ok(monkeypatch):
    monkeypatch.setattr(health_module.obs_health, "healthy", lambda timeout=0.05: True)
    monkeypatch.setattr(health_module, "check_media_mtx", lambda timeout=0.05: True)
    monkeypatch.setattr(health_module, "is_process_running", lambda name: True)
    monkeypatch.setattr(
        health_module.psutil,
        "disk_usage",
        lambda path: types.SimpleNamespace(free=0),
        raising=False,
    )
    monkeypatch.setattr(
        health_module.psutil,
        "cpu_percent",
        lambda interval=None: 0,
        raising=False,
    )
    monkeypatch.setattr(
        health_module.psutil,
        "virtual_memory",
        lambda: types.SimpleNamespace(percent=0),
        raising=False,
    )
    app = Flask(__name__)
    app.register_blueprint(health_module.health_bp, url_prefix="/api/health")
    with app.test_client() as client:
        resp = client.get("/api/health")
    assert resp.status_code == 200
