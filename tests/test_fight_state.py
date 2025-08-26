import importlib
import json
import sys
from datetime import datetime
from pathlib import Path

import pytest

# Ensure the repository root is on ``sys.path`` so tests can import modules.
ROOT = Path(__file__).resolve().parents[1]


def _reload_modules(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Reload ``paths`` and ``fight_state`` using a temporary base directory."""
    monkeypatch.setenv("BASE_DIR", str(tmp_path))

    import fight_state  # noqa: F401 - imported for reload
    import paths  # noqa: F401 - imported for reload

    importlib.reload(paths)
    return importlib.reload(fight_state)


def test_load_fight_state_defaults_missing_files(tmp_path, monkeypatch):
    fs = _reload_modules(tmp_path, monkeypatch)

    fight, date, round_id = fs.load_fight_state()

    assert fight == {}
    assert date == datetime.now().strftime("%Y-%m-%d")
    assert round_id == "round_1"


def test_load_fight_state_defaults_malformed_json(tmp_path, monkeypatch):
    data_dir = tmp_path / "FightControl" / "data"
    data_dir.mkdir(parents=True)
    (data_dir / "current_fight.json").write_text("{")  # malformed JSON
    (data_dir / "current_round.txt").write_text("round_2")

    fs = _reload_modules(tmp_path, monkeypatch)

    fight, date, round_id = fs.load_fight_state()

    assert fight == {}
    assert date == datetime.now().strftime("%Y-%m-%d")
    assert round_id == "round_2"


def test_fighter_session_dir_uses_placeholder_when_name_missing(tmp_path, monkeypatch):
    fs = _reload_modules(tmp_path, monkeypatch)

    path = fs.fighter_session_dir("red")
    today = datetime.now().strftime("%Y-%m-%d")
    expected = tmp_path / "FightControl" / "fighter_data" / "unknown_fighter" / today / "round_1"

    assert path == expected
    assert path.is_dir()


def test_fighter_session_dir_handles_none_color(tmp_path, monkeypatch):
    fs = _reload_modules(tmp_path, monkeypatch)

    path = fs.fighter_session_dir(None)
    today = datetime.now().strftime("%Y-%m-%d")
    expected = tmp_path / "FightControl" / "fighter_data" / "unknown_fighter" / today / "round_1"

    assert path == expected
    assert path.is_dir()


def test_fighter_session_dir_handles_none_fight(tmp_path, monkeypatch):
    fs = _reload_modules(tmp_path, monkeypatch)
    fs.DATA_DIR.mkdir(parents=True)
    fight = {"red_fighter": "Alice", "fight_date": "2099-01-01"}
    (fs.DATA_DIR / "current_fight.json").write_text(json.dumps(fight))
    (fs.DATA_DIR / "current_round.txt").write_text("round_3")

    path = fs.fighter_session_dir("red", fight=None)

    expected = tmp_path / "FightControl" / "fighter_data" / "Alice" / "2099-01-01" / "round_3"

    assert path == expected
    assert path.is_dir()


def test_load_fight_state_parses_files(tmp_path, monkeypatch):
    fs = _reload_modules(tmp_path, monkeypatch)

    fs.DATA_DIR.mkdir(parents=True)
    fight_data = {"red_fighter": "R", "fight_date": "2099-01-01"}
    (fs.DATA_DIR / "current_fight.json").write_text(json.dumps(fight_data))
    (fs.DATA_DIR / "current_round.txt").write_text("round_5")

    fight, date, round_id = fs.load_fight_state()

    assert fight == fight_data
    assert date == "2099-01-01"
    assert round_id == "round_5"


def test_fighter_session_dir_creates_directory(tmp_path, monkeypatch):
    fs = _reload_modules(tmp_path, monkeypatch)
    fs.DATA_DIR.mkdir(parents=True)
    fight = {"red_fighter": "Alice", "fight_date": "2099-01-01"}
    (fs.DATA_DIR / "current_fight.json").write_text(json.dumps(fight))
    (fs.DATA_DIR / "current_round.txt").write_text("round_2")

    path = fs.fighter_session_dir("red")

    expected = tmp_path / "FightControl" / "fighter_data" / "Alice" / "2099-01-01" / "round_2"

    assert path == expected
    assert path.is_dir()


def test_get_session_dir_raises_when_unwritable(tmp_path, monkeypatch):
    fs = _reload_modules(tmp_path, monkeypatch)

    target = fs.fighter_dir() / "Alice" / "2099-01-01" / "round_1"
    target.mkdir(parents=True)

    original = fs.os.access

    def fake_access(p, mode):
        if Path(p) == target:
            return False
        return original(p, mode)

    monkeypatch.setattr(fs.os, "access", fake_access)

    with pytest.raises(PermissionError):
        fs.get_session_dir("Alice", "2099-01-01", "round_1")
