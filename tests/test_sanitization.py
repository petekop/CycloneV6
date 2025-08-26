import importlib
import importlib.util
import os
import sys
from pathlib import Path

import pytest

pytest.importorskip("obsws_python")

# Path to repository root so modules can be imported
BASE_DIR = Path(__file__).resolve().parents[1]


def test_create_fight_structure_does_not_escape_base_dir(tmp_path):
    os.environ["BASE_DIR"] = str(tmp_path)

    import paths

    importlib.reload(paths)
    import FightControl.create_folders as create_folders

    importlib.reload(create_folders)

    base, _ = create_folders.create_fight_structure("../red", "../blue", "1x1")
    assert str(Path(base).resolve()).startswith(str(tmp_path.resolve()))


def test_create_round_folder_for_fighter_does_not_escape_base_dir(tmp_path):
    os.environ["BASE_DIR"] = str(tmp_path)

    import paths

    importlib.reload(paths)

    file_path = BASE_DIR / "FightControl" / "create_fighter_round_folders.py"
    spec = importlib.util.spec_from_file_location("create_fighter_round_folders", file_path)
    module = importlib.util.module_from_spec(spec)
    module.__package__ = "FightControl"
    module.paths = importlib.import_module("paths")
    module.safe_filename = importlib.import_module("FightControl.fight_utils").safe_filename
    spec.loader.exec_module(module)

    module.create_round_folder_for_fighter("../name", "../2099-01-01", "../round")
    expected = tmp_path / "FightControl" / "fighter_data" / "name" / "2099-01-01" / "round"
    assert expected.exists()
