"""Tests for dynamic round state file location."""

import importlib
import importlib.util
import json
import os
import sys
import types
from pathlib import Path

settings_module = importlib.import_module("config.settings")


def _load_round_manager() -> object:
    """Load the real ``FightControl.round_manager`` module from source."""

    root = Path(__file__).resolve().parents[1]

    # Ensure the real FightControl package and fighter_paths module are loaded
    pkg = types.ModuleType("FightControl")
    pkg.__path__ = [str(root / "FightControl")]
    sys.modules.setdefault("FightControl", pkg)

    fp_path = root / "FightControl" / "fighter_paths.py"
    fp_spec = importlib.util.spec_from_file_location(
        "FightControl.fighter_paths", fp_path
    )
    fp_mod = importlib.util.module_from_spec(fp_spec)
    assert fp_spec.loader is not None
    fp_spec.loader.exec_module(fp_mod)
    sys.modules["FightControl.fighter_paths"] = fp_mod

    rm_path = root / "FightControl" / "round_manager.py"
    spec = importlib.util.spec_from_file_location("FightControl.round_manager", rm_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_round_manager_uses_updated_base_dir(tmp_path):
    """RoundManager should honour changes to ``settings.BASE_DIR`` at runtime."""

    rm = _load_round_manager()

    settings_module.settings.BASE_DIR = tmp_path
    os.environ["BASE_DIR"] = str(tmp_path)
    import paths as paths_module

    paths_module.refresh_paths()
    rm = _load_round_manager()
    manager = rm.RoundManager()
    manager.transition(rm.RoundState.LIVE)

    expected = tmp_path / "FightControl" / "data" / "round_status.json"
    assert manager.path == expected
    assert json.loads(expected.read_text())["status"] == rm.RoundState.LIVE.value
    assert rm.round_status()["status"] == rm.RoundState.LIVE.value

    # Changing BASE_DIR should move subsequent state files
    new_base = tmp_path / "second"
    settings_module.settings.BASE_DIR = new_base
    os.environ["BASE_DIR"] = str(new_base)
    paths_module.refresh_paths()
    rm = _load_round_manager()
    manager2 = rm.RoundManager()
    assert manager2.path == new_base / "FightControl" / "data" / "round_status.json"

    # Re-importing the module should also pick up the new BASE_DIR
    rm = _load_round_manager()
    assert rm.STATE_FILE == new_base / "FightControl" / "data" / "round_status.json"


def test_round_manager_load_does_not_persist_if_state_unchanged(tmp_path):
    """Instantiating ``RoundManager`` should not rewrite an up-to-date file."""

    rm = _load_round_manager()

    state_path = tmp_path / "round_status.json"
    initial = {
        "status": rm.RoundState.IDLE.value,
        "timestamps": {rm.RoundState.IDLE.value: "2000-01-01T00:00:00"},
    }
    state_path.write_text(json.dumps(initial, indent=2))
    before = state_path.stat().st_mtime_ns

    rm.RoundManager(path=state_path)

    after = state_path.stat().st_mtime_ns
    assert before == after, "state file was unexpectedly modified"
