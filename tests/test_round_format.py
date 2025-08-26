from pathlib import Path

import pytest

from tests.helpers import use_tmp_base_dir

BASE_DIR = Path(__file__).resolve().parents[1]


def _load_fight_utils():
    """Load the real FightControl.fight_utils module."""
    import importlib.util
    import sys
    import types

    root = Path(__file__).resolve().parents[1]
    pkg = sys.modules.get("FightControl")
    if pkg is None:
        pkg = types.ModuleType("FightControl")
        sys.modules["FightControl"] = pkg
    pkg.__path__ = [str(root / "FightControl")]

    spec = importlib.util.spec_from_file_location("FightControl.fight_utils", root / "FightControl" / "fight_utils.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    sys.modules["FightControl.fight_utils"] = module
    return module


def load_create_folders(tmp_path):
    use_tmp_base_dir(tmp_path)
    fu = _load_fight_utils()

    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "FightControl.create_folders", BASE_DIR / "FightControl" / "create_folders.py"
    )
    create_folders = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(create_folders)
    return create_folders


def test_create_fight_structure_invalid_round_format(tmp_path):
    create_folders = load_create_folders(tmp_path)
    status, message = create_folders.create_fight_structure("red", "blue", "invalid")
    assert status == "❌ Invalid round format"
    assert "<rounds>x<minutes>" in message


@pytest.mark.parametrize(
    "fmt, expected",
    [
        ("3x1", (3, 60)),
        ("3x2", (3, 120)),
        ("5x1", (5, 60)),
        ("5x2", (5, 120)),
        ("3x0.25", (3, 15)),
        ("5x1.5", (5, 90)),
        ("3 X 2", (3, 120)),
        ("3 x 2", (3, 120)),
        ("3×2", (3, 120)),
        ("3 × 2", (3, 120)),
    ],
)
def test_parse_round_format_valid(fmt, expected):
    fu = _load_fight_utils()
    assert fu.parse_round_format(fmt) == expected


def test_parse_round_format_invalid():
    fu = _load_fight_utils()
    with pytest.raises(ValueError):
        fu.parse_round_format("abc")
