import sys
import types
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

fight_utils_stub = types.ModuleType("fight_utils")
fight_utils_stub.safe_filename = lambda x: x
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

import round_outputs  # noqa: E402
from utils.file_moves import move_outputs_for_round  # noqa: E402


def make_mock_obs(calls):
    async def _request(request_type, request_data=None):
        calls.append((request_type, request_data))
        return {"d": {"requestStatus": {"result": True}}}

    return types.SimpleNamespace(request=AsyncMock(side_effect=_request))


def test_starts_all_outputs_on_round_start(monkeypatch):
    calls = []
    monkeypatch.setattr(round_outputs, "OUTPUTS", ["out1", "out2"])
    monkeypatch.setattr(round_outputs, "OBS", make_mock_obs(calls))
    monkeypatch.setattr(round_outputs, "OVERLAY_WARMUP_MS", 0)
    monkeypatch.setattr(round_outputs, "ALSO_RECORD_PROGRAM", False)

    import asyncio

    asyncio.run(round_outputs.round_start())

    started = [c for c in calls if c[0] == "StartOutput"]
    assert {c[1]["outputName"] for c in started} == {"out1", "out2"}


def test_stops_all_outputs_on_round_end(monkeypatch):
    calls = []
    monkeypatch.setattr(round_outputs, "OUTPUTS", ["out1", "out2"])
    monkeypatch.setattr(round_outputs, "OBS", make_mock_obs(calls))
    monkeypatch.setattr(round_outputs, "ALSO_RECORD_PROGRAM", False)

    def dummy_load():
        return ({"red_fighter": "A", "blue_fighter": "B"}, "2025-01-01", "round_1")

    async def dummy_move(meta):
        pass

    monkeypatch.setattr(round_outputs, "load_fight_state", dummy_load)
    monkeypatch.setattr(round_outputs, "move_outputs_for_round", dummy_move)
    round_outputs._round_start_ts = None

    import asyncio

    asyncio.run(round_outputs.round_end())

    stopped = [c for c in calls if c[0] == "StopOutput"]
    assert {c[1]["outputName"] for c in stopped} == {"out1", "out2"}


def test_moves_latest_files_to_correct_folders(tmp_path):
    obs_dir = tmp_path / "obs"
    obs_dir.mkdir()
    (obs_dir / "blue_cam.mp4").write_text("b")
    (obs_dir / "red_cam.mp4").write_text("r")
    obs_cfg = {
        "output_dir": obs_dir,
        "exts": [".mp4"],
        "cameras": ["blue", "red"],
        "stable_seconds": 0,
    }
    round_meta = {
        "date": "2025-07-30",
        "fight": "Foo_vs_Bar",
        "round": 1,
        "dest_dir": tmp_path / "camserver",
        "hr_stats": {},
    }
    moved = move_outputs_for_round(obs_cfg, round_meta)
    blue_path = tmp_path / "camserver" / "2025-07-30" / "Foo_vs_Bar" / "round_1" / "blue" / "blue_cam.mp4"
    red_path = tmp_path / "camserver" / "2025-07-30" / "Foo_vs_Bar" / "round_1" / "red" / "red_cam.mp4"
    assert blue_path in moved and red_path in moved


def test_neutral_output_ignored(tmp_path):
    obs_dir = tmp_path / "obs"
    obs_dir.mkdir()
    (obs_dir / "neutral.mp4").write_text("n")
    obs_cfg = {
        "output_dir": obs_dir,
        "exts": [".mp4"],
        "cameras": ["red", "blue"],
        "stable_seconds": 0,
    }
    round_meta = {
        "date": "2025-07-30",
        "fight": "Foo_vs_Bar",
        "round": 1,
        "dest_dir": tmp_path / "camserver",
        "hr_stats": {},
    }
    moved = move_outputs_for_round(obs_cfg, round_meta)
    base = tmp_path / "camserver" / "2025-07-30" / "Foo_vs_Bar" / "round_1"
    misc_path = base / "misc" / "neutral.mp4"
    assert moved == [misc_path]
    assert misc_path.exists()
    assert not (obs_dir / "neutral.mp4").exists()


def test_missing_directory_logs_warning(tmp_path, caplog):
    obs_cfg = {
        "output_dir": tmp_path / "obs",  # directory does not exist
        "exts": [".mp4"],
        "cameras": ["red"],
        "stable_seconds": 0,
    }
    round_meta = {"date": "2025", "fight": "F1", "round": 1, "dest_dir": tmp_path, "hr_stats": {}}
    with caplog.at_level("WARNING"):
        moved = move_outputs_for_round(obs_cfg, round_meta)
    assert moved == []
    assert "Directory not found" in caplog.text
    assert "No files moved for round" in caplog.text


def test_empty_directory_logs_warning(tmp_path, caplog):
    obs_dir = tmp_path / "obs"
    obs_dir.mkdir()
    obs_cfg = {
        "output_dir": obs_dir,
        "exts": [".mp4"],
        "cameras": ["red"],
        "stable_seconds": 0,
    }
    round_meta = {"date": "2025", "fight": "F1", "round": 1, "dest_dir": tmp_path, "hr_stats": {}}
    with caplog.at_level("WARNING"):
        moved = move_outputs_for_round(obs_cfg, round_meta)
    assert moved == []
    assert "No matching files in" in caplog.text
    assert "No files moved for round" in caplog.text


def test_program_recording_flag(monkeypatch):
    calls = []
    monkeypatch.setattr(round_outputs, "OUTPUTS", [])
    monkeypatch.setattr(round_outputs, "OBS", make_mock_obs(calls))
    monkeypatch.setattr(round_outputs, "OVERLAY_WARMUP_MS", 0)
    monkeypatch.setattr(round_outputs, "ALSO_RECORD_PROGRAM", True)

    def dummy_load():
        return ({"red_fighter": "A", "blue_fighter": "B"}, "2025-01-01", "round_1")

    async def dummy_move(meta):
        pass

    monkeypatch.setattr(round_outputs, "load_fight_state", dummy_load)
    monkeypatch.setattr(round_outputs, "move_outputs_for_round", dummy_move)

    import asyncio

    asyncio.run(round_outputs.round_start())
    asyncio.run(round_outputs.round_end())

    request_types = [c[0] for c in calls]
    assert request_types.count("StartRecord") == 1
    assert request_types.count("StopRecord") == 1
