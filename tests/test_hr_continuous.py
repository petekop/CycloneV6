import importlib
import json
import os
import sys
from pathlib import Path

import pytest

from tests.helpers import use_tmp_base_dir

BASE_DIR = Path(__file__).resolve().parents[1]


def _setup(tmp_path: Path):
    """Return a reloaded RoundManager using a temporary base directory.

    The test-suite installs lightweight stubs for ``FightControl`` modules to
    avoid heavy dependencies.  These stubs omit functionality needed by the
    heart-rate tests which exercise the real ``fighter_paths`` helpers.  Ensure
    any existing stubs are removed so the genuine modules are imported.
    """

    use_tmp_base_dir(tmp_path)
    # Ensure we load the real modules rather than the lightweight stubs from
    # ``conftest``.
    sys.modules.pop("FightControl.fighter_paths", None)
    sys.modules.pop("FightControl.fight_utils", None)

    fighter_paths = pytest.importorskip("FightControl.fighter_paths")
    importlib.reload(fighter_paths)

    import fight_state

    importlib.reload(fight_state)

    rm = importlib.import_module("FightControl.round_manager")
    importlib.reload(rm)
    return rm


def test_update_hr_continuous_respects_base_dir(tmp_path):
    rm = _setup(tmp_path)

    rm.update_hr_continuous(
        "Red",
        "2024-01-01",
        "Red_vs_Blue",
        {"bpm": 120, "status": "ACTIVE", "round": 1},
    )

    session_dir = tmp_path / "FightControl" / "logs" / "2024-01-01" / "Red_vs_Blue"
    data_path = session_dir / "hr_continuous.json"
    assert data_path.exists()
    data = json.loads(data_path.read_text())
    assert data and data[0]["bpm"] == 120
    assert data[0]["status"] == "ACTIVE"
    assert data[0]["round"] == 1


def test_update_hr_continuous_tracks_status(tmp_path):
    rm = _setup(tmp_path)

    rm.update_hr_continuous(
        "Red",
        "2024-01-01",
        "Red_vs_Blue",
        {
            "bpm": 130,
            "status": "ACTIVE",
            "round": 1,
            "timestamp": "2024-01-01T00:00:00",
        },
    )
    rm.update_hr_continuous(
        "Red",
        "2024-01-01",
        "Red_vs_Blue",
        {
            "bpm": 90,
            "status": "RESTING",
            "round": 1,
            "timestamp": "2024-01-01T00:00:05",
        },
    )

    session_dir = tmp_path / "FightControl" / "logs" / "2024-01-01" / "Red_vs_Blue"
    data_path = session_dir / "hr_continuous.json"
    data = json.loads(data_path.read_text())
    assert [d["status"] for d in data] == ["ACTIVE", "RESTING"]
    assert data[1]["seconds"] > data[0]["seconds"]
