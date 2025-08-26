import importlib
import json
import logging
import sys
import types
from pathlib import Path

import pytest

pytest.importorskip("requests")

BASE_DIR = Path(__file__).resolve().parents[1]


def _stub_round_manager():
    """Create a minimal ``FightControl.round_manager`` stub.

    The real ``round_manager`` pulls in a large dependency graph which is not
    needed for these tests.  We replace it with a light-weight module exposing
    ``log_bpm`` and ``_load_fight_state``.  ``log_bpm`` persists data to a
    ``hr_log.csv`` file including the current round status so tests can assert
    on the recorded values.
    """

    from config.settings import Settings

    base_dir = Settings().BASE_DIR
    dummy = types.ModuleType("FightControl.round_manager")
    calls: list[tuple[tuple, dict]] = []

    def log_bpm(name, date, round_id, bpm, status, bout_name=None, sample_dict=None):
        status_path = base_dir / "FightControl" / "data" / "round_status.json"
        rs = json.loads(status_path.read_text())
        round_no = rs.get("round")

        safe = name.lower().replace(" ", "_")
        path = base_dir / "FightControl" / "fighter_data" / safe / date / round_id / "hr_log.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a") as f:
            f.write(f"0,{bpm},{status},{round_no}\n")

        calls.append(((name, date, round_id, bpm, status, bout_name, sample_dict), {}))

    def _load_fight_state():
        return {"red_fighter": "Red"}, "2024-01-01", "round_1"

    dummy.log_bpm = log_bpm
    dummy._load_fight_state = _load_fight_state
    dummy.start_round_sequence = lambda *a, **k: None

    def round_status():
        status_path = base_dir / "FightControl" / "data" / "round_status.json"
        try:
            return json.loads(status_path.read_text())
        except Exception:
            return {}

    dummy.round_status = round_status
    dummy.calls = calls
    sys.modules["FightControl.round_manager"] = dummy
    return dummy


def _import_daemon(rm_stub=None):
    """Stub lightweight dependencies and import the unified HR daemon."""

    if rm_stub is None:
        rm_stub = _stub_round_manager()
    else:
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

    if "matplotlib" not in sys.modules:
        mpl = types.ModuleType("matplotlib")
        mpl.use = lambda *a, **k: None
        plt_mod = types.ModuleType("pyplot")
        mpl.pyplot = plt_mod
        sys.modules["matplotlib"] = mpl
        sys.modules["matplotlib.pyplot"] = plt_mod
    if "psutil" not in sys.modules:
        psutil_mod = types.SimpleNamespace(process_iter=lambda *a, **k: [])
        sys.modules["psutil"] = psutil_mod

    if "cyclone_server" not in sys.modules:
        server = types.ModuleType("cyclone_server")
        server._load_fight_state = lambda: ({}, "2024-01-01", "round_1")
        server.setup_logging = lambda *a, **k: None
        sys.modules["cyclone_server"] = server

    sys.modules.pop("FightControl.heartrate_mon.daemon", None)
    module = importlib.import_module("FightControl.heartrate_mon.daemon")
    return module, rm_stub


def _set_env(monkeypatch, base: Path) -> None:
    monkeypatch.setenv("BASE_DIR", str(base))
    monkeypatch.setenv("OBS_WS_URL", "ws://localhost:4455")
    monkeypatch.setenv("OBS_WS_PASSWORD", "secret")
    monkeypatch.setenv("MEDIAMTX_PATH", str(base / "mediamtx"))
    monkeypatch.setenv("HR_RED_MAC", "AA:BB:CC:DD:EE:FF")
    monkeypatch.setenv("HR_BLUE_MAC", "11:22:33:44:55:66")

    from config.settings import reset_settings

    reset_settings()


def test_overlay_json_includes_time(tmp_path, monkeypatch):
    _set_env(monkeypatch, tmp_path)

    base = Path(tmp_path) / "FightControl"
    (base / "live_data").mkdir(parents=True, exist_ok=True)
    (base / "cache").mkdir(parents=True, exist_ok=True)
    (base / "data" / "overlay").mkdir(parents=True, exist_ok=True)
    status_path = base / "data" / "round_status.json"
    status_path.write_text(json.dumps({"status": "ACTIVE", "round": 1}))

    # Ensure the daemons are imported fresh so they pick up the stubbed module
    module, rm_stub = _import_daemon()
    from FightControl.fight_utils import safe_filename

    red = module.HRDaemon("red")
    blue = module.HRDaemon("blue")

    red.handle_data(None, [0, 123])
    blue.handle_data(None, [0, 95])

    red_series = json.loads((base / "cache" / "red_bpm_series.json").read_text())
    blue_series = json.loads((base / "cache" / "blue_bpm_series.json").read_text())

    from datetime import datetime

    assert isinstance(red_series[0]["time"], str)
    assert isinstance(blue_series[0]["time"], str)
    # Ensure times are ISO formatted strings
    datetime.fromisoformat(red_series[0]["time"])
    datetime.fromisoformat(blue_series[0]["time"])
    red_overlay = json.loads((base / "data" / "overlay" / "red_bpm.json").read_text())
    blue_overlay = json.loads((base / "data" / "overlay" / "blue_bpm.json").read_text())
    assert red_overlay["status"] == "ACTIVE"
    assert red_overlay["round"] == 1
    assert blue_overlay["status"] == "ACTIVE"
    assert blue_overlay["round"] == 1
    assert len(rm_stub.calls) == 2
    red_call, blue_call = rm_stub.calls
    assert red_call[0][:5] == ("Red", "2024-01-01", "round_1", 123, "ACTIVE")
    assert blue_call[0][:5] == ("Blue", "2024-01-01", "round_1", 95, "ACTIVE")
    expected_bout = f"{safe_filename('Red')}_vs_{safe_filename('blue')}"
    assert red_call[0][5] == blue_call[0][5] == expected_bout
    assert red_call[0][6]["bpm"] == 123
    assert blue_call[0][6]["bpm"] == 95


def test_bpm_persists_through_rest_and_paused(tmp_path, monkeypatch):
    _set_env(monkeypatch, tmp_path)

    base = Path(tmp_path) / "FightControl"
    (base / "live_data").mkdir(parents=True, exist_ok=True)
    (base / "cache").mkdir(parents=True, exist_ok=True)
    (base / "data" / "overlay").mkdir(parents=True, exist_ok=True)
    status_path = base / "data" / "round_status.json"

    status_path.write_text(json.dumps({"status": "ACTIVE", "round": 1}))

    module, rm_stub = _import_daemon()
    hr = module.HRDaemon("red")

    # ACTIVE
    hr.handle_data(None, [0, 100])
    # REST
    status_path.write_text(json.dumps({"status": "REST", "round": 1}))
    hr.handle_data(None, [0, 110])
    # PAUSED
    status_path.write_text(json.dumps({"status": "PAUSED", "round": 1}))
    hr.handle_data(None, [0, 120])

    overlay = json.loads((base / "data" / "overlay" / "red_bpm.json").read_text())
    assert overlay["bpm"] == 120
    assert overlay["status"] == "PAUSED"
    assert overlay["round"] == 1

    log_path = base / "fighter_data" / "red" / "2024-01-01" / "round_1" / "hr_log.csv"
    lines = log_path.read_text().strip().splitlines()
    assert len(lines) == 3
    parts = [line.split(",") for line in lines]
    assert parts[0][1] == "100"
    assert parts[0][2] == "ACTIVE"
    assert parts[1][1] == "110"
    assert parts[1][2] == "REST"
    assert parts[2][1] == "120"
    assert parts[2][2] == "PAUSED"
    assert parts[0][3] == parts[1][3] == parts[2][3] == "1"


def test_handle_data_handles_string_values_without_type_error(tmp_path, monkeypatch, caplog):
    _set_env(monkeypatch, tmp_path)

    base = Path(tmp_path) / "FightControl"
    (base / "live_data").mkdir(parents=True, exist_ok=True)
    (base / "cache").mkdir(parents=True, exist_ok=True)
    (base / "data" / "overlay").mkdir(parents=True, exist_ok=True)

    status_path = base / "data" / "round_status.json"
    status_path.write_text(json.dumps({"status": "ACTIVE", "round": 1}))

    module, rm_stub = _import_daemon()
    hr = module.HRDaemon("red")

    hr.zone_model = {
        "rest_hr": "60",
        "max_hr": "180",
        "zone_thresholds": {"easy": ["0", "50"], "hard": ["50", "100"]},
        "zone_colours": {"easy": "Blue", "hard": "Red"},
    }

    with caplog.at_level(logging.ERROR):
        hr.handle_data(None, [0, "100"])

    assert "TypeError" not in caplog.text
