import importlib
import io
import json
import os
import sys
from pathlib import Path

import pytest

from utils.template_loader import load_template

BASE_DIR = Path(__file__).resolve().parents[1]

pytest.importorskip("flask")


def setup_app(tmp_path):
    """Configure a temporary Flask app exposing the fighters blueprint.

    The production application auto-registers the route on the global
    ``cyclone_server.app``, but for isolation the tests create a fresh Flask
    instance and explicitly register the blueprint.
    """
    os.environ["BASE_DIR"] = str(tmp_path)
    data_dir = tmp_path / "FightControl" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    boot = tmp_path / "templates" / "boot.html"
    boot.parent.mkdir(parents=True, exist_ok=True)
    boot.write_text(load_template("boot.html"))
    from flask import Flask

    import fighter_utils
    import paths
    import routes.fighters as fighters

    importlib.reload(paths)
    importlib.reload(fighter_utils)
    importlib.reload(fighters)
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(fighters.fighters_bp)
    client = app.test_client()

    def cleanup():
        os.environ["BASE_DIR"] = str(BASE_DIR)
        importlib.reload(paths)
        importlib.reload(fighter_utils)
        importlib.reload(fighters)

    return client, data_dir, cleanup


def test_add_fighter_with_metrics(tmp_path):
    client, data_dir, cleanup = setup_app(tmp_path)
    csv_content = "Speed,Power,Endurance,BPM,Extra\n5,6,7,120,foo\n"
    data = {
        "name": "CSV Fighter",
        "metrics": (io.BytesIO(csv_content.encode("utf-8")), "metrics.csv", "text/csv"),
    }
    resp = client.post("/fighters", data=data, content_type="multipart/form-data")
    assert resp.status_code == 201
    payload = resp.get_json()
    perf = {"speed": 5.0, "power": 6.0, "endurance": 7.0, "bpm": 120.0}
    assert payload["fighter"]["performance"] == perf
    fighters = json.loads((data_dir / "fighters.json").read_text())
    assert fighters[0]["performance"] == perf
    perf_log = json.loads((data_dir / "performance_results.json").read_text())
    assert {"fighter_name": "CSV Fighter", "performance": perf} in perf_log
    cleanup()


def test_add_fighter_with_csvfile(tmp_path):
    client, _, cleanup = setup_app(tmp_path)
    csv_content = "Speed,Power,Endurance,BPM\n5,6,7,120\n"
    data = {
        "name": "Legacy CSV Fighter",
        "csvFile": (io.BytesIO(csv_content.encode("utf-8")), "metrics.csv", "text/csv"),
    }
    resp = client.post("/fighters", data=data, content_type="multipart/form-data")
    assert resp.status_code == 201
    payload = resp.get_json()
    perf = {"speed": 5.0, "power": 6.0, "endurance": 7.0, "bpm": 120.0}
    assert payload["fighter"]["performance"] == perf
    cleanup()


def test_add_fighter_missing_header(tmp_path):
    client, _, cleanup = setup_app(tmp_path)
    csv_content = "Speed,Power,BPM\n5,6,120\n"
    data = {
        "name": "BadCSV",
        "metrics": (io.BytesIO(csv_content.encode("utf-8")), "metrics.csv", "text/csv"),
    }
    resp = client.post("/fighters", data=data, content_type="multipart/form-data")
    assert resp.status_code == 400
    cleanup()


def test_add_fighter_bad_encoding(tmp_path):
    client, _, cleanup = setup_app(tmp_path)
    bad_bytes = b"\xff\xfe\xff"
    data = {
        "name": "BadEnc",
        "metrics": (io.BytesIO(bad_bytes), "metrics.csv", "text/csv"),
    }
    resp = client.post("/fighters", data=data, content_type="multipart/form-data")
    assert resp.status_code == 400
    cleanup()


def test_csv_header_aliases_normalised(tmp_path):
    client, _, cleanup = setup_app(tmp_path)
    # legacy lowercase headers should map to canonical snake_case keys
    # include an extra header ("Reaction") to ensure it is ignored after normalisation
    csv_content = "hrMax,deadlift,jump,Yoyo,Reaction\n180,200,30,15,3\n"
    data = {
        "name": "AliasCSV",
        "metrics": (io.BytesIO(csv_content.encode("utf-8")), "metrics.csv", "text/csv"),
    }
    resp = client.post("/fighters", data=data, content_type="multipart/form-data")
    assert resp.status_code == 201
    # Aliases are normalized to the canonical performance keys. Unknown headers
    # such as `Reaction` are ignored.
    perf = {"bpm": 180.0, "power": 200.0, "speed": 30.0, "endurance": 15.0}
    payload = resp.get_json()["fighter"]
    assert payload["performance"] == perf
    cleanup()


def test_alias_headers_missing_required(tmp_path):
    client, _, cleanup = setup_app(tmp_path)
    # missing ``jump`` header should trigger error even with alias headers
    csv_content = "hrMax,deadlift\n180,200\n"
    data = {
        "name": "MissingAlias",
        "metrics": (io.BytesIO(csv_content.encode("utf-8")), "metrics.csv", "text/csv"),
    }
    resp = client.post("/fighters", data=data, content_type="multipart/form-data")
    assert resp.status_code == 400
    cleanup()


def test_unknown_fields_are_ignored(tmp_path):
    client, data_dir, cleanup = setup_app(tmp_path)
    # ``distance`` is a recognised CSV header but not an allowed fighter field
    resp = client.post("/fighters", json={"name": "Filtered", "distance": 99})
    assert resp.status_code == 201
    payload = resp.get_json()
    assert payload["fighter"] == {"name": "Filtered"}
    fighters = json.loads((data_dir / "fighters.json").read_text())
    assert fighters == [{"name": "Filtered"}]
    cleanup()


def test_add_fighter_manual_metrics(tmp_path):
    client, data_dir, cleanup = setup_app(tmp_path)
    payload = {
        "name": "Manual",
        "speed": 5,
        "power": 6,
        "endurance": 7,
        "bpm": 120,
    }
    resp = client.post("/fighters", json=payload)
    assert resp.status_code == 201
    data = resp.get_json()["fighter"]
    expected = {"speed": 5.0, "power": 6.0, "endurance": 7.0, "bpm": 120.0}
    assert data["performance"] == expected
    fighters = json.loads((data_dir / "fighters.json").read_text())
    assert fighters[0]["performance"] == expected
    cleanup()
