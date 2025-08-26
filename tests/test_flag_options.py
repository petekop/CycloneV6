import importlib
import sys
from pathlib import Path

import pytest

pytest.importorskip("flask")

BASE_DIR = Path(__file__).resolve().parents[1]


def _get_flag_options(monkeypatch):
    monkeypatch.setenv("BASE_DIR", str(BASE_DIR))
    import cyclone_server

    importlib.reload(cyclone_server)
    return cyclone_server.get_flag_options


def test_get_flag_options_resolves_scotland(monkeypatch):
    get_flag_options = _get_flag_options(monkeypatch)
    options = get_flag_options()
    mapping = {opt["code"]: opt["name"] for opt in options}
    assert mapping.get("sco") == "Scotland"
    assert mapping.get("gb-sct") == "Scotland"
