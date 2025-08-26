import importlib
import json
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]


def _reload_utils(tmp_path):
    os.environ["BASE_DIR"] = str(tmp_path)

    import fighter_utils
    import paths

    importlib.reload(paths)
    importlib.reload(fighter_utils)
    return fighter_utils


def test_save_fighter_returns_stored_entry(tmp_path):
    fu = _reload_utils(tmp_path)
    data_dir = tmp_path / "FightControl" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    fighter = {"name": "Tester", "division": "middleweight"}
    saved = fu.save_fighter(fighter)

    assert saved["id"] == 0
    assert saved["division"] == "middleweight"
    assert saved["age"] is None
    assert saved["sex"] == ""
    assert saved["body_fat_pct"] is None
    # Performance metrics should be initialised to defaults
    assert saved["broadJump"] is None
    assert saved["sprint40m"] is None
    assert saved["pressUps"] is None
    assert saved["chinUps"] is None
    assert saved["benchPress"] is None
    assert saved["frontSquat"] is None
    assert saved["wingate"] == []

    fighters_path = data_dir / "fighters.json"
    on_disk = json.loads(fighters_path.read_text())
    assert on_disk == [fighter]

    # Second save should return existing fighter without duplicating
    saved_again = fu.save_fighter(fighter)
    assert saved_again == saved
    on_disk_again = json.loads(fighters_path.read_text())
    assert len(on_disk_again) == 1

    # Ensure later tests reload modules with their own environments
    sys.modules.pop("fighter_utils", None)
    sys.modules.pop("paths", None)
    sys.modules.pop("cyclone_modules.HRLogger.hr_logger", None)
    os.environ["BASE_DIR"] = str(BASE_DIR)
