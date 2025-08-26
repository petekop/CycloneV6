import importlib
import json
import os
import sys
from pathlib import Path

import pytest

from FightControl.common.states import RoundState, to_overlay


def _reload_rm(tmp_path: Path):
    os.environ["BASE_DIR"] = str(tmp_path)
    import paths

    importlib.reload(paths)
    # Ensure the real FightControl helpers are loaded rather than the lightweight stubs
    sys.modules.pop("FightControl.fighter_paths", None)
    sys.modules.pop("FightControl.fight_utils", None)
    fighter_paths = pytest.importorskip("FightControl.fighter_paths")
    importlib.reload(fighter_paths)
    import fight_state

    importlib.reload(fight_state)
    import FightControl.round_manager as rm

    importlib.reload(rm)
    return rm


def test_round_status_reads_file_when_no_manager(tmp_path):
    rm = _reload_rm(tmp_path)
    status_path = tmp_path / "FightControl" / "data" / "round_status.json"
    status_path.parent.mkdir(parents=True, exist_ok=True)
    status = {"status": to_overlay(RoundState.REST.value), "round": 2}
    status_path.write_text(json.dumps(status))
    assert rm.round_status() == status


def test_log_bpm_creates_csv(tmp_path):
    rm = _reload_rm(tmp_path)
    rm.log_bpm("Red", "2024-01-01", "round_1", 80, RoundState.LIVE.value)

    log_path = (
        tmp_path
        / "FightControl"
        / "fighter_data"
        / "Red"
        / "2024-01-01"
        / "round_1"
        / "hr_log.csv"
    )

    assert log_path.exists()
    assert log_path.read_text().strip() == "0,80,ACTIVE,round_1"


def test_log_bpm_writes_overlay(tmp_path):
    """Overlay json should be written alongside the CSV log."""

    rm = _reload_rm(tmp_path)
    manager = rm.RoundManager()
    manager.round = 2
    manager.transition(rm.RoundState.LIVE)

    rm.log_bpm("Red", "2024-01-01", "round_1", 90, RoundState.LIVE.value)

    overlay_path = tmp_path / "FightControl" / "data" / "overlay" / "red_bpm.json"
    assert overlay_path.exists()
    data = json.loads(overlay_path.read_text())
    assert data["bpm"] == 90
    assert data["status"] == "ACTIVE"
    assert data["round"] == 2


def test_get_state_reflects_persisted_round(tmp_path, monkeypatch):
    """``get_state`` combines fight and round information."""

    rm = _reload_rm(tmp_path)
    manager = rm.RoundManager()
    manager.round = 3
    manager.transition(rm.RoundState.LIVE)

    monkeypatch.setattr(rm, "load_fight_state", lambda: ({"bout": "Test"}, None, None))
    state = rm.get_state()
    assert state.round == 3
    assert state.status == "LIVE"
    assert state.bout == {"bout": "Test"}
