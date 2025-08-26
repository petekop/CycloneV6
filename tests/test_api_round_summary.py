import json
import os
import sys
from pathlib import Path

import pytest

pytest.importorskip("flask")
from flask import Flask

BASE_DIR = Path(__file__).resolve().parents[1]
os.environ["BASE_DIR"] = str(BASE_DIR)

from routes.api_routes import api_routes


def test_round_summary_streams_image_and_creates_session_dir(tmp_path, monkeypatch):
    app = Flask(__name__)
    app.register_blueprint(api_routes)

    session_dir = tmp_path / "session"
    session_dir.mkdir()
    image_path = session_dir / "round_1.png"
    image_path.write_bytes(b"image")

    original_mkdir = Path.mkdir
    calls = []

    def spy_mkdir(self, *args, **kwargs):
        if self == session_dir:
            calls.append((args, kwargs))
        return original_mkdir(self, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", spy_mkdir)

    client = app.test_client()
    resp = client.get(
        "/api/round/summary",
        query_string={"session": str(session_dir), "image": image_path.name},
    )
    assert resp.status_code == 200
    assert resp.data == b"image"
    assert any(kwargs == {"parents": True, "exist_ok": True} for _, kwargs in calls)


def test_round_missing_summary_reports_missing(tmp_path, monkeypatch):
    app = Flask(__name__)
    app.register_blueprint(api_routes)

    monkeypatch.setattr(api_routes, "BASE_DIR", tmp_path)

    red_dir = tmp_path / "Fights" / "Red" / "Bout" / "round_1"
    blue_dir = tmp_path / "Fights" / "Blue" / "Bout" / "round_1"
    red_dir.mkdir(parents=True)
    blue_dir.mkdir(parents=True)

    (red_dir / "round_meta.json").write_text(json.dumps({"round": 1, "expected": ["hr_log.csv"], "missing": []}))
    (blue_dir / "round_meta.json").write_text(
        json.dumps({"round": 1, "expected": ["hr_log.csv"], "missing": ["hr_log.csv"]})
    )

    data_dir = tmp_path / "FightControl" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "current_fight.json").write_text(json.dumps({"red_fighter": "Red", "blue_fighter": "Blue"}))

    client = app.test_client()
    resp = client.get("/api/round/summary")
    assert resp.status_code == 200
    info = resp.get_json()
    assert info["Red"]["missing"] == []
    assert info["Blue"]["missing"] == ["hr_log.csv"]
