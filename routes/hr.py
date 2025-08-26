"""Heart rate status routes used in the tests.

The real project exposes a rather feature rich API for querying heart rate
monitors.  For the unit tests we only need a small slice of that behaviour: a
``/status`` endpoint which reports the contents of two text files and a helper
function used by ``cyclone_server`` to register websocket handlers.  The
implementation below intentionally keeps the behaviour extremely small and
dependency free.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict

from flask import Blueprint, jsonify

from paths import BASE_DIR as _BASE_DIR

# ``BASE_DIR`` is exposed as a module level variable so tests can monkeypatch it
# to a temporary directory.
BASE_DIR = _BASE_DIR


hr_bp = Blueprint("hr", __name__)


def _status_from_file(path: Path) -> str:
    try:
        return path.read_text().strip() or "UNKNOWN"
    except FileNotFoundError:
        return "UNKNOWN"


@hr_bp.get("/status")
def hr_status() -> object:
    """Return connection status for the red and blue heart rate sensors."""

    live = Path(BASE_DIR) / "FightControl" / "live_data"
    data: Dict[str, str] = {
        "red": _status_from_file(live / "red_status.txt"),
        "blue": _status_from_file(live / "blue_status.txt"),
    }
    return jsonify(data)


def register_hr_socketio(_socketio) -> None:  # pragma: no cover - trivial
    """Placeholder used by ``cyclone_server``.

    The real project wires Socket.IO events here.  The tests simply need the
    function to exist so the implementation is a no-op.
    """

    return None


__all__ = ["hr_bp", "register_hr_socketio"]
