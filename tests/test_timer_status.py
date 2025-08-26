import importlib
import json
import os
from pathlib import Path

import pytest

pytest.importorskip("vlc")

BASE_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture()
def client(tmp_path, boot_template):
    os.environ["BASE_DIR"] = str(tmp_path)

    data_dir = tmp_path / "FightControl" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    status_path = data_dir / "round_status.json"
    status_path.write_text(json.dumps({"round": 1, "duration": 90, "rest": 30, "total_rounds": 1, "status": "WAITING"}))

    import paths

    importlib.reload(paths)
    import cyclone_server

    importlib.reload(cyclone_server)

    cyclone_server.app.config["TESTING"] = True
    with cyclone_server.app.test_client() as c:
        yield c

    # Restore environment for subsequent tests
    os.environ["BASE_DIR"] = str(BASE_DIR)


def read_status(tmp_path):
    path = tmp_path / "FightControl" / "data" / "round_status.json"
    with open(path) as f:
        return json.load(f)["status"]


def test_timer_start_active(client, tmp_path):
    resp = client.post("/api/timer/start")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ACTIVE"
    assert read_status(tmp_path) == "ACTIVE"


def test_timer_pause(client, tmp_path):
    client.post("/api/timer/start")
    resp = client.post("/api/timer/pause")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "PAUSED"
    assert read_status(tmp_path) == "PAUSED"


def test_timer_resume(client, tmp_path):
    client.post("/api/timer/start")
    client.post("/api/timer/pause")
    resp = client.post("/api/timer/resume")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ACTIVE"
    assert read_status(tmp_path) == "ACTIVE"


def test_timer_bad_command(client):
    resp = client.post("/api/timer/badcmd")
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_timer_start_missing_values(client, tmp_path):
    path = tmp_path / "FightControl" / "data" / "round_status.json"
    data = json.loads(path.read_text())
    data.pop("duration")
    path.write_text(json.dumps(data))
    resp = client.post("/api/timer/start")
    assert resp.status_code == 400
    assert "error" in resp.get_json()


@pytest.mark.parametrize(
    "field,value",
    [("duration", 0), ("duration", -1), ("rest", 0), ("rest", -1)],
)
def test_timer_start_invalid_values(field, value, client, tmp_path):
    path = tmp_path / "FightControl" / "data" / "round_status.json"
    data = json.loads(path.read_text())
    data[field] = value
    path.write_text(json.dumps(data))
    resp = client.post("/api/timer/start")
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "invalid duration/rest"


def test_enter_fighters_waiting_without_start_time(client, tmp_path, monkeypatch):
    import round_timer

    # Avoid OBS refresh side effects
    monkeypatch.setattr(round_timer, "refresh_obs_overlay", lambda: None)

    resp = client.post(
        "/enter-fighters",
        data={
            "redName": "Red",
            "blueName": "Blue",
            "roundType": "3x2",
            "roundDuration": "120",
            "restDuration": "60",
        },
    )
    assert resp.status_code == 200

    status_path = tmp_path / "FightControl" / "data" / "round_status.json"
    data = json.loads(status_path.read_text())
    assert data["status"] == "WAITING"
    assert not data.get("start_time")

    resp = client.post("/api/timer/start")
    assert resp.status_code == 200
    started = json.loads(status_path.read_text())
    assert started["status"] == "ACTIVE"
    assert started.get("start_time")
