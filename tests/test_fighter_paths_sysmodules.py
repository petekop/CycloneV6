import importlib
import sys


def test_fighter_paths_reload_after_sys_modules_manipulation(tmp_path, monkeypatch):
    monkeypatch.setenv("BASE_DIR", str(tmp_path))
    import paths

    importlib.reload(paths)

    # remove test-suite stub and import real module
    monkeypatch.delitem(sys.modules, "FightControl.fighter_paths", raising=False)
    import FightControl.fighter_paths as fighter_paths

    importlib.reload(fighter_paths)

    # simulate sys.modules manipulation
    monkeypatch.delitem(sys.modules, "FightControl.fighter_paths", raising=False)
    sys.modules["FightControl.fighter_paths"] = fighter_paths

    reloaded = importlib.reload(fighter_paths)
    p = reloaded.bout_dir("A", "2024-01-01", "Main")
    assert p.is_relative_to(tmp_path / "FightControl" / "logs")
    assert sys.modules["FightControl.fighter_paths"] is reloaded
