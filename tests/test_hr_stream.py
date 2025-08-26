import importlib
import json
import os
import sys
import types
from pathlib import Path

import pytest

pytest.importorskip("requests")

BASE_DIR = Path(__file__).resolve().parents[1]


def _import_hr_daemon():
    """Import hr_red with lightweight stubs."""
    rm_stub = types.ModuleType("FightControl.round_manager")
    rm_stub.log_bpm = lambda *a, **k: None
    rm_stub._load_fight_state = lambda: ({"red_fighter": "Red"}, "2024-01-01", "round_1")
    rm_stub.start_round_sequence = lambda *a, **k: None

    def round_status():
        base = Path(os.environ.get("BASE_DIR", str(BASE_DIR)))
        status_path = base / "FightControl" / "data" / "round_status.json"
        try:
            return json.loads(status_path.read_text())
        except Exception:
            return {}

    rm_stub.round_status = round_status
    sys.modules["FightControl.round_manager"] = rm_stub

    if "bleak" not in sys.modules:
        bleak = types.ModuleType("bleak")
        bleak.BleakClient = object

        class _Scanner:
            @staticmethod
            async def discover(timeout: float = 1.0):
                return []

        bleak.BleakScanner = _Scanner
        sys.modules["bleak"] = bleak

    if "cyclone_server" not in sys.modules:
        server = types.ModuleType("cyclone_server")
        server._load_fight_state = lambda: ({}, "2024-01-01", "round_1")
        sys.modules["cyclone_server"] = server

    if "psutil" not in sys.modules:
        sys.modules["psutil"] = types.SimpleNamespace(process_iter=lambda *a, **k: [])

    hr_red = importlib.import_module("FightControl.heartrate_mon.hr_red")
    return hr_red


def _setup_session_summary(tmp_path, monkeypatch):
    monkeypatch.setenv("BASE_DIR", str(tmp_path))
    monkeypatch.syspath_prepend(str(BASE_DIR))
    import types as _types

    mock_utils = _types.ModuleType("utils_checks")
    mock_utils.load_tags = lambda *_a, **_k: []
    monkeypatch.setitem(sys.modules, "utils_checks", mock_utils)
    import importlib

    import session_summary

    importlib.reload(session_summary)
    return session_summary


def _configure_base(tmp_path):
    base = Path(tmp_path) / "FightControl"
    (base / "live_data").mkdir(parents=True, exist_ok=True)
    (base / "cache").mkdir(parents=True, exist_ok=True)
    (base / "data" / "overlay").mkdir(parents=True, exist_ok=True)
    return base


def test_ewma_smoothing_output(tmp_path, monkeypatch):
    monkeypatch.setenv("BASE_DIR", str(tmp_path))
    monkeypatch.syspath_prepend(str(BASE_DIR))
    base = _configure_base(tmp_path)
    (base / "data" / "round_status.json").write_text(json.dumps({"status": "ACTIVE", "round": 1}))

    hr_red = _import_hr_daemon()
    hr_red.ZONE_MODEL = {
        "rest_hr": 60,
        "max_hr": 180,
        "zone_thresholds": {"z1": [0, 60], "z2": [60, 80], "z3": [80, 100]},
        "zone_colours": {"z1": "blue", "z2": "yellow", "z3": "red"},
        "smoothing": {"method": "ewma", "window": 3},
    }
    hr_red.EMA_VALUE = None
    hr_red.SMOOTH_BUFFER = []

    hr_red.handle_data(None, [0, 100])
    hr_red.handle_data(None, [0, 160])

    overlay_path = base / "data" / "overlay" / "red_bpm.json"
    overlay = json.loads(overlay_path.read_text())
    assert overlay["effort_percent"] == 58
    assert overlay["zone"] == "blue"


def test_zone_durations_sum_round_length(tmp_path, monkeypatch):
    session_summary = _setup_session_summary(tmp_path, monkeypatch)
    data_dir = tmp_path / "FightControl" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    duration = 5
    (data_dir / "round_status.json").write_text(json.dumps({"duration": duration}))

    hr_series = [{"zone": "blue", "bpm": 100} for _ in range(duration)]
    zones = session_summary.calc_time_in_zones(hr_series)
    assert sum(zones.values()) == duration
