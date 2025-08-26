from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Dict


def _get_base_dir() -> Path:
    """Return the repository root honoring PyInstaller's runtime hooks."""

    if bool(getattr(sys, "frozen", False)) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)  # pragma: no cover - exercised in tests
    p = os.environ.get("BASE_DIR")
    return Path(p) if p else Path(__file__).resolve().parent


def _compute() -> Dict[str, Path]:
    BASE = _get_base_dir()
    FC = BASE / "FightControl"
    DATA = FC / "data"
    LOGS = FC / "logs"
    TPL = BASE / "templates"
    STAT = FC / "static"
    UPLOADS = STAT / "uploads"
    CFG = BASE / "config"
    STATE = BASE / "state"
    FIGHTS = BASE / "Fights"
    OVER = DATA / "overlay"

    # The original project eagerly created a large directory tree here.  In the
    # test-suite this proved troublesome because several tests expect to create
    # directories themselves and use ``Path.mkdir`` without ``exist_ok=True``.
    # Pre-creating the tree therefore resulted in ``FileExistsError``.  The
    # heavy-handed approach is unnecessary anyway – callers that need a
    # directory can ensure it exists on demand.  We simply compute the paths and
    # leave creation to the consumer.

    return {
        "BASE_DIR": BASE,
        "FIGHTCONTROL_DIR": FC,
        "DATA_DIR": DATA,
        "LOGS_DIR": LOGS,
        "TEMPLATE_DIR": TPL,
        "STATIC_DIR": STAT,
        "UPLOADS_DIR": UPLOADS,
        "CONFIG_DIR": CFG,
        "STATE_DIR": STATE,
        "FIGHTS_DIR": FIGHTS,
        "OVERLAY_DIR": OVER,
        "FIGHTERS_JSON": DATA / "fighters.json",
        "CURRENT_FIGHT_JSON": DATA / "current_fight.json",
        "ROUND_STATUS_JSON": DATA / "round_status.json",
    }


def _apply(d):
    globals().update(d)


def refresh_paths() -> None:
    """Recompute globals after BASE_DIR changes (tests call this)."""
    _apply(_compute())
    # Ensure the module remains registered under the canonical name even if
    # tests or other code manipulate ``sys.modules``.  Some test utilities
    # temporarily replace the ``paths`` entry which causes ``importlib.reload``
    # to fail when the module is missing.  Re‑inserting ourselves makes reloads
    # robust without affecting normal behaviour.
    import sys

    sys.modules.setdefault("paths", sys.modules[__name__])


# initialize on import
_apply(_compute())
