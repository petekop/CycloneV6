import importlib
import json
import os
import sys
from pathlib import Path

import pytest

from utils.template_loader import load_template

pytest.importorskip("vlc")

BASE_DIR = Path(__file__).resolve().parents[1]


def setup_app(tmp_path, monkeypatch):
    os.environ["BASE_DIR"] = str(tmp_path)

    data_dir = tmp_path / "FightControl" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    # Minimal template required by cyclone_server startup check
    boot = tmp_path / "templates" / "boot.html"
    boot.parent.mkdir(parents=True, exist_ok=True)
    boot.write_text(load_template("boot.html"))

    fighters = [
        {"name": "Red Fighter", "age": "30", "hr_max": "200"},
        {"name": "Blue Fighter", "age": "25"},
    ]
    (data_dir / "fighters.json").write_text(json.dumps(fighters))

    import paths

    importlib.reload(paths)
    import cyclone_server

    importlib.reload(cyclone_server)

    monkeypatch.setattr(cyclone_server, "ensure_hr_logger_running", lambda: None)

    cyclone_server.app.config["TESTING"] = True
    client = cyclone_server.app.test_client()

    # Restore environment for other tests
    os.environ["BASE_DIR"] = str(BASE_DIR)
    return client


def test_zone_model_created(tmp_path, monkeypatch):
    client = setup_app(tmp_path, monkeypatch)
    resp = client.post(
        "/enter-fighters",
        data={
            "redName": "Red Fighter",
            "blueName": "Blue Fighter",
            "roundType": "3x2",
            "restDuration": "60",
        },
    )
    assert resp.status_code == 200
    from FightControl.fight_utils import safe_filename

    base = tmp_path / "FightControl" / "fighter_data"
    red_path = base / safe_filename("Red Fighter") / "zone_model.json"
    blue_path = base / safe_filename("Blue Fighter") / "zone_model.json"

    assert red_path.exists()
    assert blue_path.exists()

    red_data = json.loads(red_path.read_text())
    blue_data = json.loads(blue_path.read_text())

    assert red_data["fighter_id"] == "Red Fighter"
    assert red_data["max_hr"] == 200
    assert blue_data["max_hr"] == 195
    assert red_data.get("smoothing", {}).get("method") == "moving_average"
    assert red_data.get("smoothing", {}).get("window") == 5
