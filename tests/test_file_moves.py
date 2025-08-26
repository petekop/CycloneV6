# --- fix conflicted imports (keep both hashlib and shutil) ---
import hashlib
import logging
import shutil
import sys
import time
from pathlib import Path

import pytest

import utils.file_moves as file_moves  # noqa: E402
from utils.file_moves import (  # noqa: E402
    list_new_files,
    move_expected_files,
    move_outputs_for_round,
    safe_move,
    wait_for_stable_file,
)


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def test_list_new_files(tmp_path):
    d = tmp_path / "out"
    d.mkdir()
    f1 = d / "a.mp4"
    f2 = d / "b.mp4"
    f1.write_text("a")
    time.sleep(0.01)
    f2.write_text("b")
    newest = list_new_files(d, [".mp4"])
    assert newest == [f2]


def test_wait_for_stable_file(tmp_path):
    p = tmp_path / "f.txt"
    p.write_text("hi")
    assert wait_for_stable_file(p, stable_seconds=0.1, poll_interval=0.01)


def test_safe_move_adds_suffix_on_collision(tmp_path):
    src = tmp_path / "file.txt"
    src.write_text("hello")
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()
    dest = dest_dir / "file.txt"
    dest.write_text("existing")
    dest2 = safe_move(src, dest)
    assert dest2.name == "file_2.txt"
    assert dest2.read_text() == "hello"


def test_safe_move_multiple_collisions(tmp_path):
    src = tmp_path / "file.txt"
    src.write_text("data")
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()
    # Simulate two existing files: file.txt and file_2.txt
    (dest_dir / "file.txt").write_text("old1")
    (dest_dir / "file_2.txt").write_text("old2")
    dest = safe_move(src, dest_dir / "file.txt")
    assert dest.name == "file_3.txt"
    assert dest.read_text() == "data"


def test_safe_move_missing_src(tmp_path):
    dest = tmp_path / "dest" / "file.txt"
    with pytest.raises(FileNotFoundError):
        safe_move(tmp_path / "missing.txt", dest)


def test_safe_move_retry_on_locked_file(tmp_path, monkeypatch):
    # Arrange
    src = tmp_path / "file.txt"
    data = (b"locked-file-retry-" * 4096) + b"EOF"
    src.write_bytes(data)
    dest = tmp_path / "dest" / "file.txt"
    dest.parent.mkdir()

    orig_checksum = _sha256(src)

    # Patch the exact symbol used inside utils.file_moves: shutil.move
    import utils.file_moves as fm

    real_move = fm.shutil.move
    calls = {"n": 0}

    def flaky_move(s, d, *a, **k):
        if calls["n"] == 0:
            calls["n"] += 1
            raise PermissionError("Simulated lock on first attempt")
        return real_move(s, d, *a, **k)

    monkeypatch.setattr(fm.shutil, "move", flaky_move, raising=True)

    # Act: single call should internally retry and succeed
    moved = fm.safe_move(src, dest)

    # Assert: exactly one failure occurred and then a retry
    assert calls["n"] == 1, "safe_move should retry after first PermissionError"
    assert moved == dest
    assert moved.exists() and not src.exists()

    moved_checksum = _sha256(moved)
    assert moved_checksum == orig_checksum, "Checksum must match after move with retry"


def test_move_outputs_for_round(tmp_path):
    output_dir = tmp_path / "staging"
    dest_dir = tmp_path / "final"
    output_dir.mkdir()
    (output_dir / "red_cam.mkv").write_text("r")
    (output_dir / "blue_cam.mkv").write_text("b")
    (output_dir / "neutral.mkv").write_text("n")

    obs_cfg = {
        "output_dir": output_dir,
        "exts": [".mkv"],
        "cameras": ["red", "blue"],
        "stable_seconds": 0,
    }
    round_meta = {
        "date": "2025-07-30",
        "fight": "Fight1",
        "round": 1,
        "dest_dir": dest_dir,
        "hr_stats": {},
    }

    moved = move_outputs_for_round(obs_cfg, round_meta)
    base = dest_dir / "2025-07-30" / "Fight1" / "round_1"
    red_path = base / "red" / "red_cam.mkv"
    blue_path = base / "blue" / "blue_cam.mkv"
    misc_path = base / "misc" / "neutral.mkv"

    assert set(moved) == {red_path, blue_path, misc_path}
    for p in [red_path, blue_path, misc_path]:
        assert p.exists()
    assert not (output_dir / "neutral.mkv").exists()
    assert (base / "misc").exists()


def test_move_outputs_for_round_mixed_case_cam(tmp_path):
    output_dir = tmp_path / "staging"
    dest_dir = tmp_path / "final"
    output_dir.mkdir()
    # Camera prefix is mixed-case while config uses lowercase names
    (output_dir / "Red_CAM.mp4").write_text("r")

    obs_cfg = {
        "output_dir": output_dir,
        "exts": [".mp4"],
        "cameras": ["red", "blue"],
        "stable_seconds": 0,
    }
    round_meta = {
        "date": "2025-07-30",
        "fight": "Fight1",
        "round": 1,
        "dest_dir": dest_dir,
        "hr_stats": {},
    }

    moved = move_outputs_for_round(obs_cfg, round_meta)
    base = dest_dir / "2025-07-30" / "Fight1" / "round_1"
    red_path = base / "red" / "Red_CAM.mp4"
    misc_path = base / "misc" / "Red_CAM.mp4"

    assert red_path in moved
    assert red_path.exists()
    assert misc_path not in moved
    assert not misc_path.exists()


def test_move_outputs_for_round_non_prefixed_camera_ignored(tmp_path):
    output_dir = tmp_path / "staging"
    dest_dir = tmp_path / "final"
    output_dir.mkdir()
    # Name contains camera but does not start with it
    (output_dir / "fight_red_cam.mkv").write_text("r")

    obs_cfg = {
        "output_dir": output_dir,
        "exts": [".mkv"],
        "cameras": ["red", "blue"],
        "stable_seconds": 0,
    }
    round_meta = {
        "date": "2025-07-30",
        "fight": "Fight1",
        "round": 1,
        "dest_dir": dest_dir,
        "hr_stats": {},
    }

    moved = move_outputs_for_round(obs_cfg, round_meta)

    assert moved == []
    assert (output_dir / "fight_red_cam.mkv").exists()
    assert not dest_dir.exists()


def test_move_outputs_for_round_skips_none(tmp_path, caplog, monkeypatch):
    output_dir = tmp_path / "staging"
    dest_dir = tmp_path / "final"
    output_dir.mkdir()
    (output_dir / "red_cam.mkv").write_text("r")
    (output_dir / "blue_cam.mkv").write_text("b")

    obs_cfg = {
        "output_dir": output_dir,
        "exts": [".mkv"],
        "cameras": ["red", "blue"],
        "stable_seconds": 0,
    }
    round_meta = {
        "date": "2025-07-30",
        "fight": "Fight1",
        "round": 1,
        "dest_dir": dest_dir,
        "hr_stats": {},
    }

    orig_safe_move = file_moves.safe_move

    def fake_safe_move(src, dst):
        src_path = Path(src)
        if src_path.name == "red_cam.mkv":
            return None
        return orig_safe_move(src_path, dst)

    monkeypatch.setattr(file_moves, "safe_move", fake_safe_move)

    with caplog.at_level(logging.WARNING):
        moved = file_moves.move_outputs_for_round(obs_cfg, round_meta)

    base = dest_dir / "2025-07-30" / "Fight1" / "round_1"
    blue_path = base / "blue" / "blue_cam.mkv"
    assert moved == [blue_path]
    assert any("safe_move returned None for" in r.message and "red_cam.mkv" in r.message for r in caplog.records)
    assert (output_dir / "red_cam.mkv").exists()


def test_safe_move_retries_and_size_check(tmp_path, monkeypatch):
    src = tmp_path / "a.txt"
    src.write_text("data")
    dest = tmp_path / "dest" / "a.txt"
    dest.parent.mkdir()

    calls = {"count": 0}
    orig_move = shutil.move

    def flaky_move(s, d):
        calls["count"] += 1
        if calls["count"] < 3:
            raise OSError("boom")
        return orig_move(s, d)

    monkeypatch.setattr(shutil, "move", flaky_move)

    moved = safe_move(src, dest)
    assert calls["count"] == 3
    assert moved.read_text() == "data"


def test_move_expected_files_reports_missing(tmp_path):
    src = tmp_path / "hr_log.csv"
    src.write_text("log")
    missing = tmp_path / "missing.csv"
    dest = tmp_path / "round"
    moved, missing_list = move_expected_files([src, missing], dest)
    assert (dest / "hr_log.csv").exists()
    assert moved and moved[0].read_text() == "log"
    assert missing_list == ["missing.csv"]
