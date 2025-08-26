import importlib
import json
import logging
import os
import sys
from pathlib import Path

import pytest

pytest.importorskip("flask")

BASE_DIR = Path(__file__).resolve().parents[1]


def setup_env(tmp_path):
    os.environ["BASE_DIR"] = str(tmp_path)
    import paths

    importlib.reload(paths)
    (tmp_path / "templates").mkdir(parents=True, exist_ok=True)
    (tmp_path / "FightControl" / "static").mkdir(parents=True, exist_ok=True)
    (tmp_path / "FightControl" / "data").mkdir(parents=True, exist_ok=True)
    (tmp_path / "FightControl" / "live_data").mkdir(parents=True, exist_ok=True)
    (tmp_path / "CAMSERVER" / "overlay").mkdir(parents=True, exist_ok=True)


def test_setup_paths_registers_blueprint(tmp_path):
    setup_env(tmp_path)

    import setup_paths

    importlib.reload(setup_paths)

    assert "launch" not in setup_paths.app.blueprints
    assert setup_paths.DATA_DIR.is_dir()


def test_round_timer_arm_round_status(tmp_path, caplog):
    setup_env(tmp_path)

    import setup_paths

    importlib.reload(setup_paths)
    import round_timer

    importlib.reload(round_timer)

    with caplog.at_level(logging.INFO):
        round_timer.arm_round_status(60, 30, 3)

    status_file = setup_paths.DATA_DIR / "round_status.json"
    assert status_file.exists()
    data = json.loads(status_file.read_text())
    assert data["status"] == "WAITING"
    assert data["duration"] == 60
    assert data["rest"] == 30
    assert data["total_rounds"] == 3
    assert "start_time" not in data

    assert any("round_status armed" in r.getMessage() for r in caplog.records)
    import fighter_utils

    importlib.reload(fighter_utils)
    assert fighter_utils.load_fighters() == []
    round_file = setup_paths.DATA_DIR / "current_round.txt"
    assert round_file.exists()
    assert round_file.read_text() == "round_1"


def test_start_next_round_updates_current_round(tmp_path, monkeypatch):
    setup_env(tmp_path)

    import setup_paths

    importlib.reload(setup_paths)
    import round_timer

    importlib.reload(round_timer)

    # Prevent side effects during the test
    monkeypatch.setattr(round_timer, "play_audio", lambda *a, **k: None)
    async def _noop(*_a, **_k):
        return None

    monkeypatch.setattr(round_timer.obs, "start_record", _noop)
    monkeypatch.setattr(round_timer.obs, "stop_record", _noop)
    monkeypatch.setattr(round_timer, "refresh_obs_overlay", lambda *a, **k: None)

    class DummyTimer:
        def __init__(self, delay, func):
            self.func = func

        def start(self):
            self.func()

    monkeypatch.setattr(round_timer.threading, "Timer", DummyTimer)

    round_timer.arm_round_status(60, 0, 3)
    round_timer.start_round_timer(0, 0)
    round_timer._timer_thread.join()

    round_file = setup_paths.DATA_DIR / "current_round.txt"
    assert round_file.read_text() == "round_2"
