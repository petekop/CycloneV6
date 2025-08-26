import sys
import types
from pathlib import Path

# Ensure repository root on path

# Minimal stubs to satisfy round_outputs dependencies
fight_utils_stub = types.ModuleType("fight_utils")
fight_utils_stub.safe_filename = lambda x: str(x).replace("/", "_")
FightControl_pkg = types.ModuleType("FightControl")
FightControl_pkg.fight_utils = fight_utils_stub
sys.modules.setdefault("FightControl", FightControl_pkg)
sys.modules.setdefault("FightControl.fight_utils", fight_utils_stub)

fight_state_stub = types.ModuleType("fight_state")
fight_state_stub.load_fight_state = lambda: ({}, "", "")
sys.modules.setdefault("fight_state", fight_state_stub)

psutil_stub = types.SimpleNamespace(
    process_iter=lambda *a, **k: [],
    NoSuchProcess=Exception,
    AccessDenied=Exception,
)
sys.modules.setdefault("psutil", psutil_stub)

import round_outputs


def test_make_filename_formats_and_ext(monkeypatch):
    monkeypatch.setattr(round_outputs, "safe_filename", lambda x: str(x).replace("/", "_"))
    assert round_outputs.make_filename(3, 2, "Over-Head") == "B03_R02_Over-Head.mkv"
    assert round_outputs.make_filename(1, 1, "Right/Cam", "mp4") == "B01_R01_Right_Cam.mp4"


def test_make_filename_defaults_to_unnamed_when_camera_missing():
    assert round_outputs.make_filename(1, 1, "") == "B01_R01_unnamed.mkv"


def test_round_folder_creates_directory(tmp_path, monkeypatch):
    monkeypatch.setattr(round_outputs.settings, "BASE_DIR", tmp_path)
    path = round_outputs.round_folder(2, 5)
    expected = tmp_path / "round_outputs" / "B02" / "R05"
    assert path == expected
    assert path.is_dir()
