"""Compatibility wrapper for fight timer utilities.

The module simply re-exports helpers from :mod:`round_timer` and
``fighter_utils`` while keeping their paths stable for older code.  It also
provides a minimal session-directory helper used by scripts that pre-date the
new :mod:`fight_state` helpers.
"""

import importlib
from pathlib import Path

import round_timer
from fight_state import fighter_session_dir
from FightControl.fight_utils import safe_filename  # re-exported helper  # noqa: F401
from fighter_utils import load_fighters, save_fighter  # re-exported helpers  # noqa: F401

round_timer = importlib.reload(round_timer)
arm_round_status = round_timer.arm_round_status
start_round_timer = round_timer.start_round_timer
# Re-export round control helpers for legacy callers
pause_round = round_timer.pause_round
resume_round = round_timer.resume_round


# -------------------------------------------------
# Session helpers
# -------------------------------------------------


def get_session_dir(
    color: str,
    fight: dict | None = None,
    date: str | None = None,
    round_id: str | None = None,
) -> Path:
    """Return the directory for a fighter's session.

    This is a thin wrapper around :func:`fight_state.fighter_session_dir`.

    It resolves the fighter name for ``color`` and ensures the nested
    ``fighter_data/<fighter>/<date>/<round>`` directory structure exists.
    Optional ``fight``, ``date`` and ``round_id`` parameters mirror
    :func:`fight_state.fighter_session_dir`'s API so callers can override
    metadata when needed.

    ``fighter`` and ``corner`` are uppercased and sanitised before being
    joined into the ``fighter_data`` hierarchy. The directory is created if
    necessary, checking writability and ensuring later file writes will
    succeed.

    Examples
    --------
    >>> get_session_dir("red", fight={"red": "Alice"}, date="2024-01-01", round_id="1")
    PosixPath('.../fighter_data/ALICE/2024-01-01/1')
    """

    return fighter_session_dir(color, fight=fight, date=date, round_id=round_id)


__all__ = [
    "arm_round_status",
    "start_round_timer",
    "pause_round",
    "resume_round",
    "load_fighters",
    "save_fighter",
    "safe_filename",
]
