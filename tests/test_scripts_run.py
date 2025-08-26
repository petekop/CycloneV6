import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytest.skip("requires data/current_round.txt", allow_module_level=True)

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "FightControl" / "data"


def run_script(name: str, base: Path) -> None:
    env = os.environ.copy()
    env["BASE_DIR"] = str(base)

    data_dir = base / "FightControl" / "data"
    fighter_dir = base / "FightControl" / "fighter_data"
    data_dir.mkdir(parents=True)
    fighter_dir.mkdir(parents=True)

    shutil.copy(DATA_DIR / "current_fight.json", data_dir / "current_fight.json")
    shutil.copy(DATA_DIR / "current_round.txt", data_dir / "current_round.txt")

    script_path = BASE_DIR / "FightControl" / name
    proc = subprocess.run(
        [sys.executable, str(script_path)],
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )
    output = proc.stdout + proc.stderr
    assert "ModuleNotFoundError" not in output


@pytest.mark.parametrize("script", ["create_fighter_round_folders.py", "hr_logger.py"])
def test_scripts_no_module_error(tmp_path, script):
    run_script(script, tmp_path)
