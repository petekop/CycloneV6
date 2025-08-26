import importlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest

pytest.importorskip("obsws_python")

BASE_DIR = Path(__file__).resolve().parents[1]


def test_create_round_folder_script():
    env = os.environ.copy()
    env["BASE_DIR"] = str(BASE_DIR)
    code = (
        "import sys, pathlib;"
        "from FightControl.create_fighter_round_folders import create_round_folder_for_fighter;"
        "create_round_folder_for_fighter('UnitTester','../2099-01-01','round_x')"
    )
    subprocess.check_call([sys.executable, "-c", code], env=env)

    path = BASE_DIR / "FightControl" / "fighter_data" / "UnitTester" / "2099-01-01" / "round_x"
    assert path.is_dir()
    assert (path / "hr_log.csv").exists()
    shutil.rmtree(path)


def test_main_creates_round_dirs(tmp_path):
    os.environ["BASE_DIR"] = str(tmp_path)

    import paths

    importlib.reload(paths)
    import FightControl.create_fighter_round_folders as cff

    importlib.reload(cff)

    data_dir = tmp_path / "FightControl" / "data"
    data_dir.mkdir(parents=True)
    fight = {
        "red_fighter": "TesterRed",
        "blue_fighter": "TesterBlue",
        "round_type": "2x1",
        "fight_date": "2099-01-01",
    }
    (data_dir / "current_fight.json").write_text(json.dumps(fight))

    cff.main()

    for fighter in ("TesterRed", "TesterBlue"):
        for i in range(1, 3):
            p = tmp_path / "FightControl" / "fighter_data" / fighter / "2099-01-01" / f"round_{i}"
            assert p.is_dir()
            assert (p / "hr_log.csv").exists()


def test_create_fight_structure_creates_hr_logs(tmp_path):
    os.environ["BASE_DIR"] = str(tmp_path)

    import paths

    importlib.reload(paths)
    import FightControl.create_fighter_round_folders as cff

    importlib.reload(cff)
    import FightControl.create_folders as create_folders

    importlib.reload(create_folders)

    date = datetime.now().strftime("%Y-%m-%d")
    create_folders.create_fight_structure("TesterRed", "TesterBlue", "2x1")

    for fighter in ("TesterRed", "TesterBlue"):
        for i in range(1, 3):
            p = tmp_path / "FightControl" / "fighter_data" / fighter / date / f"round_{i}"
            assert (p / "hr_log.csv").exists()


def test_existing_hr_log_preserved(tmp_path):
    os.environ["BASE_DIR"] = str(tmp_path)

    import paths

    importlib.reload(paths)
    import FightControl.create_fighter_round_folders as cff

    importlib.reload(cff)

    fighter = "UnitTester"
    date = "2099-01-01"
    round_id = "round_x"
    hr_path = tmp_path / "FightControl" / "fighter_data" / fighter / date / round_id
    hr_path.mkdir(parents=True)
    log_file = hr_path / "hr_log.csv"
    log_file.write_text("existing data")
    mtime = log_file.stat().st_mtime

    cff.create_round_folder_for_fighter(fighter, date, round_id)

    assert log_file.read_text() == "existing data"
    assert log_file.stat().st_mtime == mtime
