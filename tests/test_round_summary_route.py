import importlib
import json
import sys
from pathlib import Path

import pytest

from tests.helpers import use_tmp_base_dir

BASE_DIR = Path(__file__).resolve().parents[1]

pytest.importorskip("flask")
pytest.importorskip("pandas")


def setup_app(tmp_path):
    paths = use_tmp_base_dir(tmp_path)

    data_dir = paths.BASE_DIR / "FightControl" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    fight = {
        "red_fighter": "Red Fighter",
        "blue_fighter": "Blue Fighter",
        "fight_date": "2099-01-01",
        "round_type": "3x2",
    }
    (data_dir / "current_fight.json").write_text(json.dumps(fight))

    import types

    stub = types.ModuleType("fight_state")

    def load_fight_state():
        return fight, fight["fight_date"], "round_1"

    def fighter_session_dir(color, fight=fight, date=fight["fight_date"], round_id="round_1"):
        return tmp_path

    def get_session_dir(*args, **kwargs):
        return tmp_path

    stub.load_fight_state = load_fight_state
    stub.fighter_session_dir = fighter_session_dir
    stub.get_session_dir = get_session_dir
    sys.modules["fight_state"] = stub

    stub_rs = types.ModuleType("round_summary")
    stub_rs.generate_round_summaries = lambda *a, **k: []
    sys.modules["round_summary"] = stub_rs

    import routes.api_routes as api_routes

    importlib.reload(api_routes)
    from flask import Flask

    app = Flask(__name__)
    app.register_blueprint(api_routes.api_routes)
    app.config["TESTING"] = True
    return app, api_routes, paths


def test_round_summary_returns_info(monkeypatch, tmp_path):
    app, api_routes, paths = setup_app(tmp_path)
    client = app.test_client()

    red_dir = paths.BASE_DIR / "red"
    blue_dir = paths.BASE_DIR / "blue"
    red_dir.mkdir()
    blue_dir.mkdir()
    (red_dir / "round_meta.json").write_text(json.dumps({"missing": ["hr_log.csv"]}))
    (blue_dir / "round_meta.json").write_text(json.dumps({"missing": []}))

    def fake_session_dir(color):
        return red_dir if color == "red" else blue_dir

    monkeypatch.setattr(api_routes, "_session_dir_for_fighter", fake_session_dir)

    resp = client.get("/api/round/summary")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["Red Fighter"]["missing"] == ["hr_log.csv"]
    assert data["Blue Fighter"]["missing"] == []


def test_round_summary_missing_image(monkeypatch, tmp_path):
    app, api_routes, paths = setup_app(tmp_path)
    client = app.test_client()

    session_dir = tmp_path / "session"
    resp = client.get(
        "/api/round/summary",
        query_string={"session": str(session_dir), "image": "missing.png"},
    )
    assert resp.status_code == 404
    data = resp.get_json()
    assert data["status"] == "error"
    assert "image not found" in data["message"]


def test_stream_round_summary(monkeypatch, tmp_path):
    app, api_routes, paths = setup_app(tmp_path)
    client = app.test_client()

    session_dir = paths.BASE_DIR / "session"

    def fake_current_session_dir():
        return session_dir

    monkeypatch.setattr(api_routes, "_current_session_dir", fake_current_session_dir)

    captured = {}

    def fake_send_from_directory(directory, filename):
        captured["dir"] = directory
        captured["fn"] = filename
        return "ok"

    monkeypatch.setattr(api_routes, "send_from_directory", fake_send_from_directory)

    resp = client.get("/api/round/summary/example.png")
    assert resp.status_code == 200
    assert session_dir.exists()
    assert captured["dir"] == session_dir
    assert captured["fn"] == "example.png"
