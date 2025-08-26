import importlib
import json
import os
import sys
from pathlib import Path

import pytest

from utils.template_loader import load_template

pytest.importorskip("flask")

BASE_DIR = Path(__file__).resolve().parents[1]


def setup_app(tmp_path):
    os.environ["BASE_DIR"] = str(tmp_path)

    data_dir = tmp_path / "FightControl" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    boot = tmp_path / "templates" / "boot.html"
    boot.parent.mkdir(parents=True, exist_ok=True)
    boot.write_text(load_template("boot.html"))

    import cyclone_server
    import fighter_utils
    import paths
    import routes.api_routes as api_routes

    importlib.reload(paths)
    importlib.reload(fighter_utils)
    importlib.reload(api_routes)
    importlib.reload(cyclone_server)

    cyclone_server.app.config["TESTING"] = True
    client = cyclone_server.app.test_client()

    os.environ["BASE_DIR"] = str(BASE_DIR)
    return client, data_dir


def test_create_fighter_success(tmp_path):
    client, data_dir = setup_app(tmp_path)
    payload = {
        "name": "Tester",
        "division": "lightweight",
        "age_class": "adult",
        "performance": {"speed": 80},
    }
    resp = client.post("/api/create_fighter", json=payload)
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["status"] == "success"
    fighter = data["fighter"]
    assert fighter["division"] == "lightweight"
    assert fighter["age_class"] == "adult"
    assert fighter["id"] == 0

    fighters = json.loads((data_dir / "fighters.json").read_text())
    assert any(f["name"] == "Tester" and f["division"] == "lightweight" for f in fighters)

    perf = json.loads((data_dir / "performance_results.json").read_text())
    expected_perf = {"fighter_name": fighter["name"], "performance": {"speed": 80}}
    assert expected_perf in perf


def test_create_fighter_missing_name(tmp_path):
    client, _ = setup_app(tmp_path)
    resp = client.post("/api/create_fighter", json={"speed": 80})
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["status"] == "error"
    assert "name" in data["error"].lower()


def test_create_fighter_malformed_performance(tmp_path):
    client, _ = setup_app(tmp_path)
    payload = {"name": "BadPerf", "performance": '{"speed": 80'}  # Malformed JSON
    resp = client.post("/api/create_fighter", json=payload)
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["status"] == "error"
    assert "performance" in data["error"].lower()


def test_reach_inferred_from_height(tmp_path):
    client, _ = setup_app(tmp_path)
    payload = {"name": "HeightOnly", "height": 180}
    resp = client.post("/api/create_fighter", json=payload)
    assert resp.status_code == 201
    fighter = resp.get_json()["fighter"]
    assert fighter["reach"] == 180 * 1.02


def test_reach_override_respected(tmp_path):
    client, _ = setup_app(tmp_path)
    payload = {"name": "CustomReach", "height": 180, "reach": 190}
    resp = client.post("/api/create_fighter", json=payload)
    assert resp.status_code == 201
    fighter = resp.get_json()["fighter"]
    assert fighter["reach"] == 190
