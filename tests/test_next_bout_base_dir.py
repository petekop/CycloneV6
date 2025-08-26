import importlib.util
import os
from pathlib import Path

import paths
from tests.helpers import use_tmp_base_dir


def _load_utils_checks():
    """Load the real utils_checks module regardless of stubs."""
    repo_root = Path(__file__).resolve().parents[1]
    import importlib.util
    import sys
    import types

    fs = types.ModuleType("fight_state")
    fs.get_session_dir = lambda: repo_root / "session"
    sys.modules["fight_state"] = fs

    spec_fu = importlib.util.spec_from_file_location(
        "FightControl.fight_utils", repo_root / "FightControl" / "fight_utils.py"
    )
    fight_utils = importlib.util.module_from_spec(spec_fu)
    assert spec_fu.loader is not None
    spec_fu.loader.exec_module(fight_utils)
    sys.modules["FightControl.fight_utils"] = fight_utils

    spec = importlib.util.spec_from_file_location("utils_checks", repo_root / "utils_checks.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_use_tmp_base_dir_idempotent(tmp_path):
    paths1 = use_tmp_base_dir(tmp_path)
    paths2 = use_tmp_base_dir(tmp_path)
    assert paths1.BASE_DIR == paths2.BASE_DIR == tmp_path


def test_next_bout_number_multiple_base_dir_updates(tmp_path, monkeypatch):
    utils_checks = _load_utils_checks()
    from FightControl.fight_utils import safe_filename

    orig_env = os.getenv("BASE_DIR")

    date = "2099-01-01"
    red = "Red Fighter"
    blue = "Blue Fighter"

    safe_red = safe_filename(red)

    base1 = tmp_path / "base1"
    base2 = tmp_path / "base2"
    base3 = tmp_path / "base3"

    monkeypatch.setenv("BASE_DIR", str(base1))
    paths.refresh_paths()
    (base1 / "FightControl" / "fighter_data" / safe_red / date / "dummy_BOUT2").mkdir(parents=True)
    assert utils_checks.next_bout_number(date, red, blue) == 3

    monkeypatch.setenv("BASE_DIR", str(base2))
    paths.refresh_paths()
    (base2 / "FightControl" / "fighter_data" / safe_red / date / "dummy_BOUT7").mkdir(parents=True)
    assert utils_checks.next_bout_number(date, red, blue) == 8

    monkeypatch.setenv("BASE_DIR", str(base3))
    paths.refresh_paths()
    assert utils_checks.next_bout_number(date, red, blue) == 1

    if orig_env is None:
        monkeypatch.delenv("BASE_DIR", raising=False)
    else:
        monkeypatch.setenv("BASE_DIR", orig_env)
    paths.refresh_paths()
