import importlib
import sys
import types
from datetime import datetime
from pathlib import Path

import pytest

# Ensure repository root is on sys.path
ROOT = Path(__file__).resolve().parents[1]


def _reload_modules(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Reload modules using a temporary base directory."""
    monkeypatch.setenv("BASE_DIR", str(tmp_path))

    stub = types.ModuleType("round_timer")
    stub.arm_round_status = lambda *a, **k: None
    stub.start_round_timer = lambda *a, **k: None
    stub.pause_round = lambda *a, **k: None
    stub.resume_round = lambda *a, **k: None
    monkeypatch.setitem(sys.modules, "round_timer", stub)

    orig_reload = importlib.reload

    def fake_reload(module):
        if module.__name__ == "round_timer":
            return module
        return orig_reload(module)

    monkeypatch.setattr(importlib, "reload", fake_reload)

    import fight_state  # noqa: F401 - imported for reload
    import paths  # noqa: F401 - imported for reload
    import utils_fight  # noqa: F401 - imported for reload

    importlib.reload(paths)
    importlib.reload(fight_state)
    return importlib.reload(utils_fight)


def test_get_session_dir_returns_nested_path(tmp_path, monkeypatch):
    uf = _reload_modules(tmp_path, monkeypatch)

    fight = {"red_fighter": "Alice", "fight_date": "2099-01-01"}
    path = uf.get_session_dir("red", fight=fight, date="2099-01-01", round_id="round_2")

    expected = tmp_path / "FightControl" / "fighter_data" / "Alice" / "2099-01-01" / "round_2"
    assert path == expected
    assert path.is_dir()


def test_get_session_dir_defaults_missing_metadata(tmp_path, monkeypatch):
    uf = _reload_modules(tmp_path, monkeypatch)

    fight = {"red_fighter": "Bob"}
    path = uf.get_session_dir("red", fight=fight)

    today = datetime.now().strftime("%Y-%m-%d")
    expected = tmp_path / "FightControl" / "fighter_data" / "Bob" / today / "round_1"
    assert path == expected
    assert path.is_dir()


def test_get_session_dir_raises_when_unwritable(tmp_path, monkeypatch):
    uf = _reload_modules(tmp_path, monkeypatch)

    target = tmp_path / "FightControl" / "fighter_data" / "Alice" / "2099-01-01" / "round_1"
    target.mkdir(parents=True)

    import fight_state as fs

    original = fs.os.access

    def fake_access(p, mode):
        if Path(p) == target:
            return False
        return original(p, mode)

    monkeypatch.setattr(fs.os, "access", fake_access)

    fight = {"red_fighter": "Alice", "fight_date": "2099-01-01"}
    with pytest.raises(PermissionError):
        uf.get_session_dir("red", fight=fight, date="2099-01-01", round_id="round_1")
