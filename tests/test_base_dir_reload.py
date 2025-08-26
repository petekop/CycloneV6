"""Regression tests for dynamically refreshed ``BASE_DIR``."""

import importlib
import json
import sys
from pathlib import Path


def test_map_asset_paths_uses_updated_base_dir(tmp_path, monkeypatch):
    base1 = tmp_path / "one"
    base1.mkdir()
    base2 = tmp_path / "two"
    base2.mkdir()

    monkeypatch.setenv("BASE_DIR", str(base1))
    import fighter_utils
    import paths

    importlib.reload(paths)
    importlib.reload(fighter_utils)

    monkeypatch.setenv("BASE_DIR", str(base2))
    importlib.reload(paths)
    fu = importlib.reload(fighter_utils)

    meta = {"flag": "gb", "styleIcon": "muay.png"}
    mapped = fu.map_asset_paths(meta)

    flag_expected = base2 / "FightControl" / "static" / "images" / "flags" / "gb.svg"
    style_expected = base2 / "FightControl" / "static" / "styles" / "muay.png"

    assert fu.BASE_DIR == base2
    assert mapped["flag"] == str(flag_expected.resolve())
    assert mapped["styleIcon"] == str(style_expected.resolve())

    # ensure other tests reload modules with their own environment
    sys.modules.pop("fighter_utils", None)
    sys.modules.pop("paths", None)


def test_load_fighters_uses_updated_base_dir(tmp_path, monkeypatch):
    base1 = tmp_path / "old"
    data1 = base1 / "FightControl" / "data"
    data1.mkdir(parents=True)
    (data1 / "fighters.json").write_text(json.dumps([{"name": "Old"}]))

    base2 = tmp_path / "new"
    data2 = base2 / "FightControl" / "data"
    data2.mkdir(parents=True)
    (data2 / "fighters.json").write_text(json.dumps([{"name": "New"}]))

    monkeypatch.setenv("BASE_DIR", str(base1))
    import fighter_utils
    import paths

    importlib.reload(paths)
    importlib.reload(fighter_utils)
    assert fighter_utils.load_fighters()[0]["name"] == "Old"

    monkeypatch.setenv("BASE_DIR", str(base2))
    importlib.reload(paths)
    fu = importlib.reload(fighter_utils)
    loaded = fu.load_fighters()
    assert loaded[0]["name"] == "New"
    assert fu.BASE_DIR == base2
    assert fu.FIGHTERS_JSON == data2 / "fighters.json"

    sys.modules.pop("fighter_utils", None)
    sys.modules.pop("paths", None)
