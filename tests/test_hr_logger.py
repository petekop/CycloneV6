import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("requests")
from utils.template_loader import load_template

BASE_DIR = Path(__file__).resolve().parents[1]


def test_get_session_dir_wrapper_resolves(tmp_path, monkeypatch):
    monkeypatch.setenv("BASE_DIR", str(tmp_path))
    import importlib

    import fight_state
    import paths
    import utils_checks

    # Reload modules so they pick up the temporary BASE_DIR
    importlib.reload(paths)
    importlib.reload(fight_state)
    importlib.reload(utils_checks)

    expected = fight_state.get_session_dir("Red Fighter", "2099-01-01", "round_1")
    actual = utils_checks.get_session_dir("Red Fighter", "2099-01-01", "round_1")

    assert actual == expected
    assert actual.is_dir()


def test_save_series_creates_files(tmp_path):
    os.environ["BASE_DIR"] = str(tmp_path)
    data_dir = tmp_path / "FightControl" / "data"
    overlay_dir = data_dir / "overlay"
    overlay_dir.mkdir(parents=True)

    fight = {
        "red_fighter": "Red Fighter",
        "blue_fighter": "Blue Fighter",
        "rounds": 1,
        "fight_date": "2099-01-01",
    }
    (data_dir / "current_fight.json").write_text(json.dumps(fight))
    (data_dir / "round_status.json").write_text(json.dumps({"status": "ENDED", "round": 1}))

    (overlay_dir / "red_bpm.json").write_text(json.dumps({"bpm": 90, "max_hr": 180}))
    (overlay_dir / "blue_bpm.json").write_text(json.dumps({"bpm": 100, "max_hr": 180}))

    env = os.environ.copy()
    env["BASE_DIR"] = str(tmp_path)
    env["TEST_MODE"] = "1"
    subprocess.check_call([sys.executable, str(BASE_DIR / "cyclone_modules" / "HRLogger" / "hr_logger.py")], env=env)

    from FightControl.fight_utils import safe_filename

    safe_red = safe_filename("Red Fighter")
    safe_blue = safe_filename("Blue Fighter")

    red_base = tmp_path / "FightControl" / "fighter_data" / safe_red / "2099-01-01"
    blue_base = tmp_path / "FightControl" / "fighter_data" / safe_blue / "2099-01-01"

    assert any((red_base / d / "hr_data.json").exists() for d in os.listdir(red_base))
    assert any((red_base / d / "graph.png").exists() for d in os.listdir(red_base))
    assert any((blue_base / d / "hr_data.json").exists() for d in os.listdir(blue_base))
    assert any((blue_base / d / "graph.png").exists() for d in os.listdir(blue_base))
    assert blue_base.parent.name == safe_blue

    # Verify hr_data contains status and round fields
    red_hr_file = next(
        (red_base / d / "hr_data.json" for d in os.listdir(red_base) if (red_base / d / "hr_data.json").exists())
    )
    red_series = json.loads(red_hr_file.read_text())
    assert red_series and "status" in red_series[0] and "round" in red_series[0]


def test_load_zone_model_resolves_path(tmp_path, monkeypatch):
    os.environ["BASE_DIR"] = str(tmp_path)
    import importlib

    import paths

    importlib.reload(paths)
    from cyclone_modules.HRLogger import hr_logger

    importlib.reload(hr_logger)

    model_path = tmp_path / "FightControl" / "fighter_data" / "test_fighter" / "zone_model.json"
    model_path.parent.mkdir(parents=True, exist_ok=True)
    model_path.write_text(json.dumps({"foo": "bar"}))

    data = hr_logger.load_zone_model("Test Fighter")
    assert data == {"foo": "bar"}
    assert hr_logger.load_zone_model("Missing") == {}


def test_calc_metrics_zone(tmp_path, monkeypatch):
    os.environ["BASE_DIR"] = str(tmp_path)
    import importlib

    import paths

    importlib.reload(paths)
    from cyclone_modules.HRLogger import hr_logger

    importlib.reload(hr_logger)

    model = {
        "rest_hr": 60,
        "max_hr": 200,
        "zone_thresholds": {"z1": [0, 60], "z2": [60, 80], "z3": [80, 100]},
        "zone_colours": {"z1": "blue", "z2": "yellow", "z3": "red"},
    }
    effort, zone, _ = hr_logger.calc_metrics(160, model, None)
    assert int(effort) == 71
    assert zone == "yellow"


def test_hr_logger_updates_overlay(tmp_path):
    os.environ["BASE_DIR"] = str(tmp_path)
    data_dir = tmp_path / "FightControl" / "data"
    overlay_dir = data_dir / "overlay"
    fighter_dir = tmp_path / "FightControl" / "fighter_data"
    overlay_dir.mkdir(parents=True)

    fight = {
        "red_fighter": "Red Fighter",
        "blue_fighter": "Blue Fighter",
        "rounds": 1,
        "fight_date": "2099-01-01",
    }
    (data_dir / "current_fight.json").write_text(json.dumps(fight))
    (data_dir / "round_status.json").write_text(json.dumps({"status": "ENDED", "round": 1}))

    red_model = {
        "rest_hr": 60,
        "max_hr": 180,
        "zone_thresholds": {"z1": [0, 60], "z2": [60, 80], "z3": [80, 100]},
        "zone_colours": {"z1": "blue", "z2": "yellow", "z3": "red"},
        "smoothing": None,
    }
    blue_model = red_model
    rpath = fighter_dir / "red_fighter" / "zone_model.json"
    bpath = fighter_dir / "blue_fighter" / "zone_model.json"
    rpath.parent.mkdir(parents=True, exist_ok=True)
    bpath.parent.mkdir(parents=True, exist_ok=True)
    rpath.write_text(json.dumps(red_model))
    bpath.write_text(json.dumps(blue_model))

    # Pre-existing overlay files with differing status/round should be
    # overwritten by hr_logger using values from ``round_status.json``
    (overlay_dir / "red_bpm.json").write_text(json.dumps({"bpm": 150, "status": "ACTIVE", "round": 99}))
    (overlay_dir / "blue_bpm.json").write_text(json.dumps({"bpm": 90, "status": "REST", "round": 2}))

    env = os.environ.copy()
    env["BASE_DIR"] = str(tmp_path)
    env["TEST_MODE"] = "1"
    subprocess.check_call([sys.executable, str(BASE_DIR / "cyclone_modules" / "HRLogger" / "hr_logger.py")], env=env)

    red_out = json.loads((overlay_dir / "red_bpm.json").read_text())
    blue_out = json.loads((overlay_dir / "blue_bpm.json").read_text())
    assert red_out["effort_percent"] == 75
    assert red_out["zone"] == "yellow"
    assert blue_out["effort_percent"] == 25
    assert blue_out["zone"] == "blue"
    # status/round should reflect ``round_status.json`` data, not the original overlay
    assert red_out["status"] == "ENDED"
    assert red_out["round"] == 1
    assert blue_out["status"] == "ENDED"
    assert blue_out["round"] == 1

    # Ensure hr_data entries include status and round
    from FightControl.fight_utils import safe_filename

    red_base = fighter_dir / safe_filename("Red Fighter") / "2099-01-01"
    hr_file = next(
        (red_base / d / "hr_data.json" for d in os.listdir(red_base) if (red_base / d / "hr_data.json").exists())
    )
    series = json.loads(hr_file.read_text())
    assert series and series[0]["status"] == "ENDED" and series[0]["round"] == 1


def test_hr_daemons_write_time_field(tmp_path, monkeypatch):
    monkeypatch.setenv("BASE_DIR", str(tmp_path))
    overlay_dir = tmp_path / "FightControl" / "data" / "overlay"

    import types

    dummy_bleak = types.SimpleNamespace(BleakClient=object, BleakScanner=object)
    monkeypatch.setitem(sys.modules, "bleak", dummy_bleak)

    dummy_server = types.ModuleType("cyclone_server")
    dummy_server._load_fight_state = lambda: ({}, "2024-01-01", "round_1")
    dummy_server.setup_logging = lambda *a, **k: None
    monkeypatch.setitem(sys.modules, "cyclone_server", dummy_server)

    # Minimal template required by ``cyclone_server`` during import
    boot = tmp_path / "templates" / "boot.html"
    boot.parent.mkdir(parents=True, exist_ok=True)
    boot.write_text(load_template("boot.html"))

    import importlib

    import paths

    importlib.reload(paths)
    from FightControl.heartrate_mon.daemon import HRDaemon

    blue = HRDaemon("blue")
    red = HRDaemon("red")
    blue.write_overlay_json(111, "REST", 2)
    red.write_overlay_json(222, "PAUSED", 2)

    blue_data = json.loads((overlay_dir / "blue_bpm.json").read_text())
    red_data = json.loads((overlay_dir / "red_bpm.json").read_text())

    from datetime import datetime

    assert isinstance(blue_data.get("time"), str)
    assert isinstance(red_data.get("time"), str)
    # Ensure the values are ISO formatted timestamps
    datetime.fromisoformat(blue_data["time"])
    datetime.fromisoformat(red_data["time"])
    assert blue_data["status"] == "REST"
    assert blue_data["round"] == 2
    assert red_data["status"] == "PAUSED"
    assert red_data["round"] == 2

    # Changing BASE_DIR after instantiation should redirect overlay output
    new_base = tmp_path / "alt"
    new_overlay = new_base / "FightControl" / "data" / "overlay" / "blue_bpm.json"
    assert not new_overlay.exists()
    monkeypatch.setenv("BASE_DIR", str(new_base))
    blue.write_overlay_json(333, "ACTIVE", 3)
    assert new_overlay.exists()
    latest = json.loads(new_overlay.read_text())
    assert latest["bpm"] == 333
    assert latest["status"] == "ACTIVE"
    assert latest["round"] == 3
