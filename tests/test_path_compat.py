import importlib
import os
import pathlib
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]


def test_create_fight_structure_without_is_relative_to(tmp_path, monkeypatch):
    os.environ["BASE_DIR"] = str(tmp_path)

    import paths

    importlib.reload(paths)
    import FightControl.create_folders as create_folders

    importlib.reload(create_folders)

    with monkeypatch.context() as m:
        m.delattr(pathlib.PurePath, "is_relative_to", raising=False)
        base, msg = create_folders.create_fight_structure("red", "blue", "1x1")
    assert Path(base).exists()
    assert msg == "✅ Folder Structure Created"


def test_create_fight_structure_sanitizes_names_without_is_relative_to(tmp_path, monkeypatch):
    os.environ["BASE_DIR"] = str(tmp_path)

    import paths

    importlib.reload(paths)
    import FightControl.create_folders as create_folders

    importlib.reload(create_folders)

    with monkeypatch.context() as m:
        m.delattr(pathlib.PurePath, "is_relative_to", raising=False)
        base, msg = create_folders.create_fight_structure("../red", "../blue", "1x1")
    assert Path(base).exists()
    assert str(Path(base)).startswith(str(tmp_path))
