"""Helpers for persisting boot process state.

This lightweight module mirrors the behaviour of :mod:`round_state` but
stores data under :data:`paths.STATE_DIR` using ``boot_state.json``.  The
helpers intentionally perform only minimal validation so they can be used in
unit tests without additional dependencies.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import paths


def _boot_state_path() -> Path:
    """Return the path to the ``boot_state.json`` file."""

    return Path(paths.STATE_DIR) / "boot_state.json"


_BOOT_STATE: Dict[str, Any] = {}


def get_boot_state() -> Dict[str, Any]:
    """Return the in-memory boot state."""

    return _BOOT_STATE


def set_boot_state(state: Dict[str, Any]) -> None:
    """Replace the in-memory boot state with ``state``."""

    _BOOT_STATE.clear()
    _BOOT_STATE.update(state)


def load_boot_state() -> Dict[str, Any]:
    """Load the boot state from ``boot_state.json``.

    Returns an empty dictionary when the file does not exist or contains
    invalid JSON.  The loaded state is also stored in-memory.
    """

    path = _boot_state_path()
    try:
        state = json.loads(path.read_text())
    except Exception:
        state = {}
    set_boot_state(state)
    return state


def save_boot_state(state: Dict[str, Any]) -> None:
    """Persist *state* to ``boot_state.json`` and update memory."""

    set_boot_state(state)
    path = _boot_state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2))


__all__ = ["get_boot_state", "set_boot_state", "load_boot_state", "save_boot_state"]
