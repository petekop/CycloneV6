import importlib
import os
import sys
from pathlib import Path

import pytest

pd = pytest.importorskip("pandas")

from FightControl.fight_utils import safe_filename

BASE_DIR = Path(__file__).resolve().parents[1]


def test_load_hr_includes_first_sample(tmp_path):
    os.environ["BASE_DIR"] = str(tmp_path)

    import paths

    importlib.reload(paths)
    import round_summary

    importlib.reload(round_summary)

    fighter = "Tester"
    date = "2024-01-01"
    round_id = "round_1"
    log_dir = tmp_path / "FightControl" / "fighter_data" / safe_filename(fighter) / date / round_id
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "hr_log.csv"
    log_file.write_text("2024-01-01 00:00:00,70,ACTIVE,round_1\n" "2024-01-01 00:00:01,75,ACTIVE,round_1\n")

    df = round_summary._load_hr(fighter, date, round_id)
    assert list(df["bpm"]) == [70, 75]
    assert list(df["round_id"]) == ["round_1", "round_1"]


def test_generate_fight_summary_includes_first_sample(tmp_path, monkeypatch):
    os.environ["BASE_DIR"] = str(tmp_path)

    import paths

    importlib.reload(paths)
    import FightControl.round_manager as rm

    fighter = "Tester"
    date = "2024-01-01"
    bout_name = "test_bout"
    log_file = rm.round_dir(fighter, date, bout_name, "round_1") / "hr_log.csv"
    log_file.write_text("2024-01-01 00:00:00,80,ACTIVE,round_1\n" "2024-01-01 00:00:01,85,ACTIVE,round_1\n")

    captured = {}
    real_read_csv = pd.read_csv

    def capturing_read_csv(*args, **kwargs):
        df = real_read_csv(*args, **kwargs)
        captured["df"] = df
        captured["header"] = kwargs.get("header", "infer")
        return df

    monkeypatch.setattr(rm.pd, "read_csv", capturing_read_csv)

    rm.generate_fight_summary(fighter, date, total_rounds=1, bout_name=bout_name)

    assert captured["header"] is None
    assert list(captured["df"]["bpm"]) == [80, 85]
    assert list(captured["df"]["round_id"]) == ["round_1", "round_1"]
