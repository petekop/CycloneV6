import importlib
import json
import os
import re
import sys
import types
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).resolve().parents[1]


def safe_filename(name: str) -> str:
    if not isinstance(name, str):
        name = str(name)
    name = os.path.basename(name)
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
    return name or "unnamed"


def next_bout_number(date: str, red: str, blue: str) -> int:
    from config.settings import Settings

    base_dir = Path(Settings().BASE_DIR)
    fighter_dir = base_dir / "FightControl" / "fighter_data"
    bout_re = re.compile(r"_BOUT(\d+)$", re.I)

    def scan(fighter: str) -> int:
        base = fighter_dir / safe_filename(fighter) / date
        if not base.exists():
            return 0
        mx = 0
        for d in base.iterdir():
            if not d.is_dir():
                continue
            m = bout_re.search(d.name)
            if m:
                try:
                    idx = int(m.group(1))
                    mx = max(mx, idx)
                except Exception:
                    pass
        return mx

    return max(scan(red), scan(blue)) + 1


def load_controller_tagger():
    saved = {
        name: sys.modules.get(name)
        for name in [
            "FightControl",
            "FightControl.fight_utils",
            "FightControl.fighter_paths",
            "FightControl.round_manager",
            "utils_checks",
            "requests",
        ]
    }

    fc_pkg = types.ModuleType("FightControl")

    fu_spec = importlib.util.spec_from_file_location(
        "FightControl.fight_utils", BASE_DIR / "FightControl" / "fight_utils.py"
    )
    fight_utils = importlib.util.module_from_spec(fu_spec)
    fu_spec.loader.exec_module(fight_utils)
    fc_pkg.fight_utils = fight_utils
    sys.modules["FightControl.fight_utils"] = fight_utils

    fp_spec = importlib.util.spec_from_file_location(
        "FightControl.fighter_paths", BASE_DIR / "FightControl" / "fighter_paths.py"
    )
    fighter_paths = importlib.util.module_from_spec(fp_spec)
    fp_spec.loader.exec_module(fighter_paths)
    fc_pkg.fighter_paths = fighter_paths
    sys.modules["FightControl.fighter_paths"] = fighter_paths

    fc_pkg.round_manager = types.SimpleNamespace(
        get_state=lambda: types.SimpleNamespace(bout={}, round=1),
        round_status=lambda: {},
    )
    sys.modules["FightControl.round_manager"] = fc_pkg.round_manager

    sys.modules["FightControl"] = fc_pkg

    utils_checks = types.ModuleType("utils_checks")
    utils_checks.next_bout_number = next_bout_number
    sys.modules["utils_checks"] = utils_checks

    sys.modules.setdefault("requests", types.SimpleNamespace(post=lambda *a, **kw: None))

    ct_spec = importlib.util.spec_from_file_location(
        "controller_tagger", BASE_DIR / "FightControl" / "controller_tagger.py"
    )
    ct_module = importlib.util.module_from_spec(ct_spec)
    ct_spec.loader.exec_module(ct_module)

    def cleanup():
        for name, mod in saved.items():
            if mod is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = mod

    return ct_module, fighter_paths, cleanup


def test_tag_writer_handles_rapid_posts(tmp_path):
    os.environ["BASE_DIR"] = str(tmp_path)
    os.environ["OBS_WS_URL"] = "ws://localhost:4455"
    os.environ["OBS_WS_PASSWORD"] = "secret"
    os.environ["MEDIAMTX_PATH"] = str(tmp_path / "mediamtx")
    os.environ["HR_RED_MAC"] = "AA:BB:CC:DD:EE:FF"
    os.environ["HR_BLUE_MAC"] = "11:22:33:44:55:66"

    from config.settings import reset_settings

    reset_settings()

    import paths

    importlib.reload(paths)
    getattr(paths, "ensure_paths", lambda: None)()

    data_dir = tmp_path / "FightControl" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    fight = {
        "red_fighter": "Red Fighter",
        "blue_fighter": "Blue Fighter",
        "fight_date": "2099-01-01",
    }
    (data_dir / "current_fight.json").write_text(json.dumps(fight))
    (data_dir / "current_round.txt").write_text("round_1")

    ct_module, fighter_paths, cleanup = load_controller_tagger()
    try:
        for i in range(20):
            ct_module.log_tag("red", f"Tag{i}")

        bout = f"2099-01-01_{safe_filename('Red Fighter').upper()}_vs_{safe_filename('Blue Fighter').upper()}_BOUT0"
        tag_path = Path(paths.BASE_DIR) / "FightControl" / "logs" / "2099-01-01" / bout / "round_1" / "tags.csv"
        lines = tag_path.read_text().strip().splitlines()
        assert lines[0] == "timestamp,fighter,tag"
        assert len(lines) == 21
        tags = [line.split(",")[2] for line in lines[1:]]
        assert tags == [f"Tag{i}" for i in range(20)]
    finally:
        cleanup()


@pytest.mark.timeout(15)
def test_tag_writer_stress_accumulates_entries(tmp_path):
    os.environ["BASE_DIR"] = str(tmp_path)
    os.environ["OBS_WS_URL"] = "ws://localhost:4455"
    os.environ["OBS_WS_PASSWORD"] = "secret"
    os.environ["MEDIAMTX_PATH"] = str(tmp_path / "mediamtx")
    os.environ["HR_RED_MAC"] = "AA:BB:CC:DD:EE:FF"
    os.environ["HR_BLUE_MAC"] = "11:22:33:44:55:66"

    from config.settings import reset_settings

    reset_settings()

    import paths

    importlib.reload(paths)
    getattr(paths, "ensure_paths", lambda: None)()

    data_dir = tmp_path / "FightControl" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    fight = {
        "red_fighter": "Red Fighter",
        "blue_fighter": "Blue Fighter",
        "fight_date": "2099-01-01",
    }
    (data_dir / "current_fight.json").write_text(json.dumps(fight))
    (data_dir / "current_round.txt").write_text("round_1")

    ct_module, fighter_paths, cleanup = load_controller_tagger()
    try:
        for i in range(100):
            ct_module.log_tag("red", f"Tag{i}")

        bout = f"2099-01-01_{safe_filename('Red Fighter').upper()}_vs_{safe_filename('Blue Fighter').upper()}_BOUT0"
        tag_path = Path(paths.BASE_DIR) / "FightControl" / "logs" / "2099-01-01" / bout / "round_1" / "tags.csv"
        lines = tag_path.read_text().strip().splitlines()
        assert lines[0] == "timestamp,fighter,tag"
        assert len(lines) == 101
        tags = [line.split(",")[2] for line in lines[1:]]
        assert tags == [f"Tag{i}" for i in range(100)]
    finally:
        cleanup()
