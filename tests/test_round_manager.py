import importlib
import json
from pathlib import Path

import pytest

from tests.helpers import use_tmp_base_dir

pytest.importorskip("vlc")

BASE_DIR = Path(__file__).resolve().parents[1]


def test_read_bpm_parses_various_formats(tmp_path):
    paths = use_tmp_base_dir(tmp_path)

    live_dir = paths.BASE_DIR / "FightControl" / "live_data"
    live_dir.mkdir(parents=True, exist_ok=True)
    (live_dir / "red_bpm.txt").write_text("85")
    (live_dir / "blue_bpm.txt").write_text("85 BPM")

    import FightControl.round_manager as rm

    importlib.reload(rm)

    assert rm.read_bpm("red") == 85
    assert rm.read_bpm("blue") == 85


def test_prepare_round_dirs_on_arm(tmp_path, monkeypatch):
    paths = use_tmp_base_dir(tmp_path)
    import FightControl.round_manager as rm

    importlib.reload(rm)

    monkeypatch.setattr(rm.platform, "machine", lambda: "arm64")
    rm._prepare_round_dirs("Bout", "round_1", "Red", "Blue")
    assert (paths.BASE_DIR / "Fights" / "Red" / "Bout" / "round_1").exists()
    assert (paths.BASE_DIR / "Fights" / "Blue" / "Bout" / "round_1").exists()


def test_finalize_round_dirs_writes_meta(tmp_path, monkeypatch):
    paths = use_tmp_base_dir(tmp_path)
    import FightControl.round_manager as rm

    importlib.reload(rm)

    date = "2025-01-01"
    bout = "Bout"
    fight_slug = "Bout"

    # Prepare source hr log for Red only
    red_src = rm.round_dir("Red", date, bout, "round_1")
    red_src.mkdir(parents=True, exist_ok=True)
    (red_src / "hr_log.csv").write_text("log")

    rm._finalise_round_dirs(fight_slug, bout, date, 1, "Red", "Blue")

    red_dest = rm.fight_round_dir("Red", fight_slug, "round_1")
    blue_dest = rm.fight_round_dir("Blue", fight_slug, "round_1")

    red_meta = json.loads((red_dest / "round_meta.json").read_text())
    blue_meta = json.loads((blue_dest / "round_meta.json").read_text())

    assert red_meta["missing"] == []
    assert (red_dest / "hr_log.csv").exists()
    assert blue_meta["missing"] == ["hr_log.csv"]
