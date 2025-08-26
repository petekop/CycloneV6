import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
os.environ["BASE_DIR"] = str(BASE_DIR)

from utils import ensure_dir_permissions


def test_ensure_dir_permissions_creates_directory(tmp_path):
    target = tmp_path / "new_dir"
    mode = 0o700
    result = ensure_dir_permissions(target, mode)
    assert target.is_dir()
    if os.name != "nt":
        assert result == mode
