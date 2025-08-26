from __future__ import annotations

import pytest

import paths
from boot_state import load_boot_state, save_boot_state


@pytest.fixture(autouse=True)
def clear_state(tmp_path, monkeypatch):
    """Ensure ``boot_state.json`` is isolated per test."""

    monkeypatch.setattr(paths, "STATE_DIR", tmp_path)
    state_file = tmp_path / "boot_state.json"
    if state_file.exists():
        state_file.unlink()
    yield
    if state_file.exists():
        state_file.unlink()


def test_boot_state_round_trip():
    """``save_boot_state`` and ``load_boot_state`` should persist data."""

    payload = {
        "ready": True,
        "services": {
            "hr_daemon": "READY",
            "mediamtx": "WAIT",
            "obs": "ERROR",
        },
    }

    save_boot_state(payload)
    assert load_boot_state() == payload
