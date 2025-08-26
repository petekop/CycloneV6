import types

import pytest

pytest.importorskip("flask")
from flask import Flask

import routes.health as health_module


@pytest.fixture
def client(monkeypatch):
    app = Flask(__name__)
    app.register_blueprint(health_module.health_bp, url_prefix="/api/health")
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def _patch(monkeypatch, *, obs, mtx, hr, cpu, mem, disk):
    monkeypatch.setattr(
        health_module,
        "obs_health",
        types.SimpleNamespace(healthy=lambda timeout=0.05: obs),
    )
    monkeypatch.setattr(health_module, "check_media_mtx", lambda timeout=0.05: mtx)
    monkeypatch.setattr(health_module, "is_process_running", lambda name: hr)
    monkeypatch.setattr(health_module.psutil, "cpu_percent", lambda interval=None: cpu, raising=False)
    monkeypatch.setattr(
        health_module.psutil,
        "virtual_memory",
        lambda: types.SimpleNamespace(percent=mem),
        raising=False,
    )
    monkeypatch.setattr(
        health_module.psutil,
        "disk_usage",
        lambda path: types.SimpleNamespace(free=disk * 1024**3),
        raising=False,
    )


def test_api_health_service_map_ok(monkeypatch, client):
    _patch(monkeypatch, obs=True, mtx=True, hr=True, cpu=4.0, mem=5.0, disk=6.0)
    data = client.get("/api/health").get_json()
    assert data == {
        "obs_connected": True,
        "mediamtx_running": True,
        "hr_daemon": True,
        "disk_free_gb": 6.0,
        "cpu_percent": 4.0,
        "mem_percent": 5.0,
    }


def test_api_health_service_map_fail(monkeypatch, client):
    _patch(monkeypatch, obs=False, mtx=False, hr=False, cpu=10.0, mem=11.0, disk=12.0)
    data = client.get("/api/health").get_json()
    assert data == {
        "obs_connected": False,
        "mediamtx_running": False,
        "hr_daemon": False,
        "disk_free_gb": 12.0,
        "cpu_percent": 10.0,
        "mem_percent": 11.0,
    }
