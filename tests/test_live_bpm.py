import importlib
import json
import os
import sys
from pathlib import Path

import pytest

from utils.template_loader import load_template

pytest.importorskip("flask")

BASE_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture()
def client(tmp_path):
    os.environ["BASE_DIR"] = str(tmp_path)

    overlay_dir = tmp_path / "FightControl" / "data" / "overlay"
    overlay_dir.mkdir(parents=True, exist_ok=True)
    (overlay_dir / "red_bpm.json").write_text(
        json.dumps({"bpm": 99, "max_hr": 185, "zone": "None", "effort_percent": 0})
    )
    (overlay_dir / "blue_bpm.json").write_text(
        json.dumps({"bpm": 77, "max_hr": 185, "zone": "None", "effort_percent": 0})
    )

    # Minimal template required by cyclone_server startup check
    boot = tmp_path / "templates" / "boot.html"
    boot.parent.mkdir(parents=True, exist_ok=True)
    boot.write_text(load_template("boot.html"))

    import paths

    importlib.reload(paths)
    import cyclone_modules.HRLogger.hr_logger as hr_logger

    importlib.reload(hr_logger)
    import utils_bpm

    importlib.reload(utils_bpm)
    import cyclone_server

    importlib.reload(cyclone_server)

    cyclone_server.app.config["TESTING"] = True
    with cyclone_server.app.test_client() as c:
        yield c

    # restore global state for other tests
    os.environ["BASE_DIR"] = str(BASE_DIR)
    importlib.reload(paths)
    importlib.reload(hr_logger)
    importlib.reload(utils_bpm)
    importlib.reload(cyclone_server)


def test_live_bpm_red(client):
    resp = client.get("/live-json/red_bpm")
    assert resp.status_code == 200
    assert resp.get_json() == {
        "bpm": 99,
        "max_hr": 185,
        "zone": "None",
        "effort_percent": 0,
        "status": None,
    }


def test_live_bpm_blue(client):
    resp = client.get("/live-json/blue_bpm")
    assert resp.status_code == 200
    assert resp.get_json() == {
        "bpm": 77,
        "max_hr": 185,
        "zone": "None",
        "effort_percent": 0,
        "status": None,
    }
