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


def test_load_fighters_preserves_age(tmp_path):
    fu = _reload_utils(tmp_path)
    data_dir = tmp_path / "FightControl" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    fighters = [
        {"name": "No Age"},
        {
            "name": "Has Age",
            "age": "33",
            "sessions": [{"date": "2024-01-01", "performance": {"speed": 1}}],
        },
    ]
    (data_dir / "fighters.json").write_text(json.dumps(fighters))
    loaded = fu.load_fighters()
    assert loaded[0]["age"] is None
    assert loaded[1]["age"] == "33"
    assert loaded[0]["sessions"] == []
    assert loaded[1]["sessions"] == [{"date": "2024-01-01", "performance": {"speed": 1}}]
    # Newly added performance metrics should default to ``None`` or an empty
    # list when absent in the source data.
    for f in loaded:
        assert f["sex"] == ""
        assert f["body_fat_pct"] is None
        assert f["broadJump"] is None
        assert f["sprint40m"] is None
        assert f["pressUps"] is None
        assert f["chinUps"] is None
        assert f["benchPress"] is None
        assert f["frontSquat"] is None
        assert f["wingate"] == []
    assert [f["id"] for f in loaded] == [0, 1]

    # Ensure later tests reload modules with their own environments
    sys.modules.pop("fighter_utils", None)
    sys.modules.pop("paths", None)
    sys.modules.pop("cyclone_modules.HRLogger.hr_logger", None)
