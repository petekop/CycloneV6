import os
import sys
from pathlib import Path

import pytest

from FightControl.fight_utils import safe_filename

pytest.importorskip("obsws_python")

BASE_DIR = Path(__file__).resolve().parents[1]
os.environ["BASE_DIR"] = str(BASE_DIR)


def test_safe_filename_does_not_escape_base_dir(tmp_path):
    """safe_filename should strip path traversal components."""
    sanitized = safe_filename("../evil")
    assert "/" not in sanitized and ".." not in sanitized
    full = (BASE_DIR / sanitized).resolve()
    assert str(full).startswith(str(BASE_DIR.resolve()))
