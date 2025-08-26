import importlib
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]


def _reload_modules(tmp_path):
    os.environ["BASE_DIR"] = str(tmp_path)
    import fighter_utils
    import paths

    importlib.reload(paths)
    importlib.reload(fighter_utils)
    return fighter_utils


def test_map_asset_paths_resolves_flag_and_style(monkeypatch, tmp_path):
    fu = _reload_modules(tmp_path)
    meta = {"name": "Tester", "flag": "gb", "styleIcon": "muay.png"}
    mapped = fu.map_asset_paths(meta)

    flag_path = tmp_path / "FightControl" / "static" / "images" / "flags" / "gb.svg"
    style_path = tmp_path / "FightControl" / "static" / "styles" / "muay.png"

    assert mapped["flag"] == str(flag_path.resolve())
    assert mapped["styleIcon"] == str(style_path.resolve())
    assert mapped["name"] == "Tester"

    # Ensure other tests load modules with their own environment
    sys.modules.pop("fighter_utils", None)
    sys.modules.pop("paths", None)
