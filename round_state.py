"""Utilities for persisting round state information."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from paths import BASE_DIR

DATA_DIR = BASE_DIR / "FightControl" / "data"
ROUND_STATE_JSON = DATA_DIR / "round_state.json"

DEFAULT_STATE: Dict[str, Any] = {
    "state": "offline",
    "round": 0,
    "fighter_id_red": None,
    "fighter_id_blue": None,
    "started_at": None,
    "updated_at": None,
    "timer": 0,
}


def load_round_state() -> Dict[str, Any]:
    """Return the current round state, falling back to defaults."""

    try:
        data = json.loads(ROUND_STATE_JSON.read_text())
        if isinstance(data, dict):
            return {**DEFAULT_STATE, **data}
    except Exception:
        pass
    return DEFAULT_STATE.copy()


def save_round_state(state: Dict[str, Any]) -> None:
    """Persist ``state`` to :data:`ROUND_STATE_JSON`."""

    merged = {**DEFAULT_STATE, **state}
    merged["updated_at"] = datetime.utcnow().isoformat()
    ROUND_STATE_JSON.parent.mkdir(parents=True, exist_ok=True)
    ROUND_STATE_JSON.write_text(json.dumps(merged, indent=2))


__all__ = [
    "load_round_state",
    "save_round_state",
    "ROUND_STATE_JSON",
    "DATA_DIR",
]
