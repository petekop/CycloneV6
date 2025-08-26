import importlib
import json
import os
import sys
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).resolve().parents[1]

pytest.importorskip("flask")


def setup_app(tmp_path):
    os.environ["BASE_DIR"] = str(tmp_path)

    import paths

    importlib.reload(paths)
    import routes.api_routes as api_routes

    importlib.reload(api_routes)
    import FightControl.fighter_paths as fighter_paths

    importlib.reload(fighter_paths)
    from flask import Flask

    app = Flask(__name__)
    app.register_blueprint(api_routes.api_routes)
    app.config["TESTING"] = True
    return app


def _create_bout(tmp_path):
    fighter = "Red"
    date = "2099-01-01"
    bout = "red_vs_blue"
    session_dir = tmp_path / "FightControl" / "logs" / date / bout
    session_dir.mkdir(parents=True, exist_ok=True)

    (session_dir / "bout.json").write_text(json.dumps({"winner": "red"}))
    (session_dir / "events.csv").write_text("time,tag\n1,start\n")
    (session_dir / "hr_continuous.json").write_text(json.dumps([{"bpm": 123}]))
    return fighter, date, bout


def test_bout_endpoints(tmp_path):
    app = setup_app(tmp_path)
    client = app.test_client()

    fighter, date, bout = _create_bout(tmp_path)
    base = f"{fighter}/{date}/{bout}"

    resp = client.get(f"/api/bout/{base}/meta")
    assert resp.status_code == 200
    assert resp.get_json() == {"winner": "red"}

    resp = client.get(f"/api/bout/{base}/events?format=json")
    assert resp.status_code == 200
    assert resp.get_json() == [{"time": "1", "tag": "start"}]

    resp = client.get(f"/api/bout/{base}/hr")
    assert resp.status_code == 200
    assert resp.get_json() == [{"bpm": 123}]
