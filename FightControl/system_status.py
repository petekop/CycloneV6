"""Controller detection utilities for FightControl."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from utils.files import open_utf8

try:
    import pygame
except Exception:  # pragma: no cover - pygame optional in tests
    pygame = None  # type: ignore

try:
    from inputs import devices
except Exception:  # pragma: no cover - inputs optional in tests
    devices = None  # type: ignore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_STATUS_PATH = Path(__file__).resolve().parent / "data" / "system_status.json"

_DEFAULT_STATUS = {
    "status": "OFFLINE",
    "controllers": {
        "red": {"connected": False, "name": None, "id": None},
        "blue": {"connected": False, "name": None, "id": None},
    },
}


def write_status(data: dict) -> None:
    """Write ``data`` to the status JSON file."""
    _STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open_utf8(_STATUS_PATH, "w") as f:
        json.dump(data, f, indent=2)


def get_status() -> dict:
    """Return the current system status."""
    try:
        with open_utf8(_STATUS_PATH) as f:
            return json.load(f)
    except Exception:
        return _DEFAULT_STATUS.copy()


def detect_controllers() -> dict:
    """Detect connected controllers and update ``system_status.json``.

    The function prefers ``pygame`` for joystick detection but will fall back to
    the ``inputs`` library if ``pygame`` isn't installed. Device index ``0`` is
    mapped to the red fighter, while index ``1`` maps to blue.
    """

    controllers = {
        "red": {"connected": False, "name": None, "id": None},
        "blue": {"connected": False, "name": None, "id": None},
    }

    online = False

    if pygame is not None:
        pygame.init()
        pygame.joystick.init()
        count = pygame.joystick.get_count()
        for idx in range(count):
            js = pygame.joystick.Joystick(idx)
            js.init()
            info = {"connected": True, "name": js.get_name(), "id": idx}
            logger.info("Controller connected: %s (id=%s)", js.get_name(), idx)
            if idx == 0:
                controllers["red"] = info
            elif idx == 1:
                controllers["blue"] = info
            online = True
    elif devices is not None:
        gamepads = devices.gamepads
        for idx, dev in enumerate(gamepads):
            info = {"connected": True, "name": dev.name, "id": idx}
            logger.info("Controller connected: %s (id=%s)", dev.name, idx)
            if idx == 0:
                controllers["red"] = info
            elif idx == 1:
                controllers["blue"] = info
            online = True

    status = {
        "status": "ONLINE" if online else "OFFLINE",
        "controllers": controllers,
    }
    write_status(status)
    return status
