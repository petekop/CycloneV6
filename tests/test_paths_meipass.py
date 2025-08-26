import importlib
import sys
from pathlib import Path

import pytest

pytest.importorskip("flask")


def reload_module(name):
    if name in sys.modules:
        return importlib.reload(sys.modules[name])
    return importlib.import_module(name)


@pytest.fixture(autouse=True)
def _reset_modules():
    """Reload path helpers after each test to avoid cross-test pollution."""
    yield
    if "paths" in sys.modules:
        importlib.reload(sys.modules["paths"])
    if "setup_paths" in sys.modules:
        importlib.reload(sys.modules["setup_paths"])
    if "config.settings" in sys.modules:
        importlib.reload(sys.modules["config.settings"])


@pytest.fixture(autouse=True)
def _ensure_repo_root(monkeypatch):
    """Make sure the repository root is importable during tests."""
    repo_root = Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(repo_root))


def test_base_dir_dev(monkeypatch):
    monkeypatch.delenv("BASE_DIR", raising=False)
    monkeypatch.delattr(sys, "frozen", raising=False)
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    module = reload_module("paths")
    assert module.BASE_DIR == Path(__file__).resolve().parents[1]


def test_base_dir_frozen(tmp_path, monkeypatch):
    monkeypatch.delenv("BASE_DIR", raising=False)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    module = reload_module("paths")
    assert module.BASE_DIR == tmp_path


def test_base_dir_ignores_settings(tmp_path, monkeypatch):
    monkeypatch.delenv("BASE_DIR", raising=False)
    monkeypatch.delattr(sys, "frozen", raising=False)
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)

    settings_mod = reload_module("config.settings")
    settings_mod.settings.BASE_DIR = tmp_path

    module = reload_module("paths")
    repo_root = Path(__file__).resolve().parents[1]
    assert module.BASE_DIR == repo_root


def test_setup_paths_dev(monkeypatch):
    monkeypatch.delenv("BASE_DIR", raising=False)
    monkeypatch.delattr(sys, "frozen", raising=False)
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    monkeypatch.setattr(sys, "path", sys.path.copy())
    module = reload_module("setup_paths")
    repo_root = Path(__file__).resolve().parents[1]
    assert module.TEMPLATE_DIR == repo_root / "templates"
    assert module.STATIC_DIR == repo_root / "FightControl" / "static"


def test_setup_paths_frozen(tmp_path, monkeypatch):
    monkeypatch.setenv("BASE_DIR", str(tmp_path))
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    monkeypatch.setattr(sys, "path", sys.path.copy())
    reload_module("config.settings")
    module = reload_module("setup_paths")
    assert module.TEMPLATE_DIR == tmp_path / "templates"
    assert module.STATIC_DIR == tmp_path / "FightControl" / "static"
