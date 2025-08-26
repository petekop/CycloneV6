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

    importlib.reload(paths)
    importlib.reload(fighter_utils)
    importlib.reload(cyclone_server)
    cyclone_server.app.config["TESTING"] = True
    client = cyclone_server.app.test_client()

    os.environ["BASE_DIR"] = str(BASE_DIR)
    return client, data_dir


def test_parse_row_converts_units():
    from utils.csv_parser import parse_row

    row = {
        "Name": "Alice",
        "Weight (lbs)": "220",
        "Height (in)": "70",
        "Distance (miles)": "5",
        "Range (in)": "",
        "Age": "30",
        "Sex": "female",
        "% Body Fat": "15",
    }
    parsed = parse_row(row)
    assert parsed["weight"] == pytest.approx(99.79024, rel=1e-5)
    assert parsed["height"] == pytest.approx(177.8, rel=1e-5)
    assert parsed["distance"] == pytest.approx(8.0467, rel=1e-4)
    assert parsed["range"] is None
    assert parsed["age"] == 30
    assert parsed["sex"] == "female"
    assert parsed["body_fat_pct"] == 15


def test_parse_row_gender_alias():
    from utils.csv_parser import parse_row

    row = {"Gender": "female"}
    parsed = parse_row(row)
    assert parsed["sex"] == "female"


def test_post_fighter_uses_parser(tmp_path):
    client, data_dir = setup_app(tmp_path)
    payload = {
        "Name": "Bob",
        "Weight (lbs)": "200",
        "Height (in)": "72",
        "Gender": "male",
        "% Body Fat": "12",
    }
    resp = client.post("/fighters", json=payload)
    assert resp.status_code == 201

    fighters = json.loads((data_dir / "fighters.json").read_text())
    fighter = fighters[0]
    assert fighter["weight"] == pytest.approx(90.7184, rel=1e-5)
    assert fighter["height"] == pytest.approx(182.88, rel=1e-5)
    assert fighter["sex"] == "male"
    assert fighter["body_fat_pct"] == 12
