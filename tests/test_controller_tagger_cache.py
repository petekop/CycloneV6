import importlib
import os
from pathlib import Path

from FightControl.fight_utils import safe_filename


def setup_env(tmp_path):
    os.environ["BASE_DIR"] = str(tmp_path)
    os.environ["OBS_WS_URL"] = "ws://localhost:4455"
    os.environ["OBS_WS_PASSWORD"] = "secret"
    os.environ["MEDIAMTX_PATH"] = str(tmp_path / "mediamtx")
    os.environ["HR_RED_MAC"] = "AA:BB:CC:DD:EE:FF"
    os.environ["HR_BLUE_MAC"] = "11:22:33:44:55:66"
    from config.settings import reset_settings

    reset_settings()
    paths = importlib.import_module("paths")
    paths.refresh_paths()
    getattr(paths, "ensure_paths", lambda: None)()
    return paths


def test_log_tag_caches_modules(tmp_path, monkeypatch):
    paths = setup_env(tmp_path)
    from FightControl import controller_tagger as ct

    reload_calls = []

    def fake_reload(mod):
        reload_calls.append(mod.__name__)
        return mod

    monkeypatch.setattr(ct.importlib, "reload", fake_reload)

    path_refresh_calls = []
    monkeypatch.setattr(ct.paths, "refresh_paths", lambda: path_refresh_calls.append(True))
    fighter_refresh_calls = []
    monkeypatch.setattr(ct.fighter_paths, "refresh_base_dir", lambda: fighter_refresh_calls.append(True))

    state_calls = []

    def fake_state():
        state_calls.append(True)
        fight = {"red_fighter": "Red Fighter", "blue_fighter": "Blue Fighter"}
        return fight, "2099-01-01", "round_1"

    monkeypatch.setattr(ct.fight_state, "load_fight_state", fake_state)

    bout_calls = []
    monkeypatch.setattr(ct, "next_bout_number", lambda *a, **kw: bout_calls.append(True) or 1)

    ct.requests = None

    ct.log_tag("red", "One")
    ct.log_tag("red", "Two")

    assert reload_calls.count("paths") == 0
    assert reload_calls.count("fight_state") == 1
    assert len(path_refresh_calls) == 1
    assert len(fighter_refresh_calls) == 1
    assert len(state_calls) == 1
    assert len(bout_calls) == 1

    safe_red = safe_filename("Red Fighter").upper()
    safe_blue = safe_filename("Blue Fighter").upper()
    bout = f"2099-01-01_{safe_red}_vs_{safe_blue}_BOUT0"
    tag_path = Path(paths.BASE_DIR) / "FightControl" / "logs" / "2099-01-01" / bout / "round_1" / "tags.csv"
    lines = tag_path.read_text().strip().splitlines()
    assert lines[0] == "timestamp,fighter,tag"
    assert [line.split(",")[2] for line in lines[1:]] == ["One", "Two"]
