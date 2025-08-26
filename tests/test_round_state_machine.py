import importlib
import json
import os
import sys
from pathlib import Path

import pytest


def _reload_rm(tmp_path: Path):
    os.environ["BASE_DIR"] = str(tmp_path)
    import paths

    importlib.reload(paths)
    sys.modules.pop("FightControl.fighter_paths", None)
    sys.modules.pop("FightControl.fight_utils", None)
    fighter_paths = pytest.importorskip("FightControl.fighter_paths")
    importlib.reload(fighter_paths)
    import fight_state

    importlib.reload(fight_state)
    import FightControl.round_manager as rm

    importlib.reload(rm)
    return rm


def test_state_transitions_persist(tmp_path):
    rm = _reload_rm(tmp_path)
    manager = rm.RoundManager()
    assert manager.state is rm.RoundState.IDLE

    manager.transition(rm.RoundState.LIVE)
    path = tmp_path / "FightControl" / "data" / "round_status.json"
    data = json.loads(path.read_text())
    assert data["status"] == rm.RoundState.LIVE.value

    # Create a new instance to ensure the state was persisted
    new_manager = rm.RoundManager()
    assert new_manager.state is rm.RoundState.LIVE
