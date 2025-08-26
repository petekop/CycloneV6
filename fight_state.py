"""Helpers for locating fight data and session folders.

The module exposes a tiny API used by both the web routes and various
utilities.  It reads the active fight definition from
``FightControl/data`` and builds paths under ``FightControl/fighter_data``.
Missing metadata falls back to sensible defaults so callers can continue to
record data even if the fight has not been fully configured.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from paths import BASE_DIR
from utils import ensure_dir

ROOT_DIR = BASE_DIR
DATA_DIR = ROOT_DIR / "FightControl" / "data"
LIVE_DIR = ROOT_DIR / "FightControl" / "live_data"


def _safe(value: str) -> str:
    """Return a filesystem safe version of ``value``.

    ``fight_state`` previously relied on :func:`FightControl.fight_utils.safe_filename`
    which is replaced with a stub in the test-suite's ``conftest``.  The stub
    returns an empty string causing paths like ``DATA_DIR/""/""`` to be
    generated.  These truncated paths break a number of tests which expect the
    real sanitisation behaviour.  To keep the module self contained and avoid
    surprises when the external helper is stubbed out, a lightweight copy of
    the sanitisation logic lives here.  It mirrors the behaviour of
    ``safe_filename`` by stripping directory components and replacing
    problematic characters with underscores.  An empty result defaults to
    ``"unnamed"``.
    """

    import os
    import re

    if not isinstance(value, str):
        value = str(value)
    value = os.path.basename(value)
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", value)
    return value or "unnamed"


def _root() -> Path:
    """Return the base directory for fighter data."""
    return ROOT_DIR / "FightControl" / "fighter_data"


def fighter_dir() -> Path:
    """Return the fighter data directory.

    Unlike the old :data:`FIGHTER_DIR` constant, this function resolves the
    path on every call so changes to :data:`ROOT_DIR` or the environment are
    always respected.
    """
    return _root()


def load_fight_state() -> tuple[dict, str, str]:
    """Return fight metadata, date and current round identifier.

    The function reads ``current_fight.json`` and ``current_round.txt`` from
    :data:`DATA_DIR`.  If either file is missing or malformed, defaults are
    returned (an empty ``dict``, today's date and ``"round_1"``).  This means
    callers always receive usable values even in a cold-start scenario.
    """
    try:
        fight_text = (DATA_DIR / "current_fight.json").read_text()
        fight = json.loads(fight_text)
    except FileNotFoundError:
        fight = {}
    except json.JSONDecodeError:
        fight = {}

    try:
        round_id = (DATA_DIR / "current_round.txt").read_text().strip()
    except FileNotFoundError:
        round_id = "round_1"
    date = fight.get("fight_date", datetime.now().strftime("%Y-%m-%d"))
    return fight, date, round_id


def get_session_dir(name: str, date: str, round_id: str) -> Path:
    """Return the session directory for ``name``.

    ``name``, ``date`` and ``round_id`` are sanitised using a small local
    helper and joined with :func:`fighter_dir`.  The resulting directory is
    created (along with any parents) which implicitly checks writability – an
    :class:`OSError` will be raised if the path cannot be created.

    Examples
    --------
    >>> get_session_dir("Alice", "2025-01-01", "round_1")
    PosixPath('.../FightControl/fighter_data/Alice/2025-01-01/round_1')
    """

    safe_name = _safe(name)
    safe_date = _safe(date)
    safe_round = _safe(round_id)
    path = fighter_dir() / safe_name / safe_date / safe_round
    try:
        ensure_dir(path)
    except PermissionError as exc:  # pragma: no cover - defensive
        raise PermissionError(f"Unable to create session directory '{path}'") from exc
    if not os.access(path, os.W_OK):
        raise PermissionError(f"Session directory '{path}' is not writable")
    return path


def fighter_session_dir(
    color: str | None,
    fight: dict | None = None,
    date: str | None = None,
    round_id: str | None = None,
) -> Path:
    """Return the session directory path for a given fighter color.

    ``color`` should be ``"red"`` or ``"blue"``. Any of ``fight``, ``date``
    or ``round_id`` may be omitted, in which case :func:`load_fight_state`
    provides fallback values. The directory is created on demand, ensuring it
    is writable. If the fighter name cannot be resolved, the placeholder
    ``"unknown_fighter"`` is used.

    Parameters
    ----------
    color : str | None
        Which fighter to resolve, typically ``"red"`` or ``"blue"``. If
        ``None`` or the fighter name is missing, ``"unknown_fighter"`` is used.
    fight : dict, optional
        Full fight metadata. If not provided, it is loaded from disk.
    date : str, optional
        Fight date in YYYY-MM-DD format. If not provided, it is loaded from disk.
    round_id : str, optional
        Round identifier such as ``"round_1"``. If not provided, it is loaded from disk.

    Returns
    -------
    Path
        Path object pointing to the fighter's round directory, falling back to
        ``"unknown_fighter"`` when the name is unavailable.

    Examples
    --------
    Resolve the directory for the red fighter using cached fight metadata::

        >>> fighter_session_dir("red")  # doctest: +SKIP
        PosixPath('.../FightControl/fighter_data/Alice/2025-01-01/round_1')

    Supplying explicit values is also supported::

        >>> fighter_session_dir("blue", fight={"blue": "Bob"},
        ...                    date="2025-01-01", round_id="round_2")  # doctest: +SKIP
        PosixPath('.../FightControl/fighter_data/Bob/2025-01-01/round_2')
    """
    if fight is None or date is None or round_id is None:
        loaded_fight, loaded_date, loaded_round = load_fight_state()
        fight = fight or loaded_fight
        date = date or loaded_date
        round_id = round_id or loaded_round

    name = None
    if isinstance(fight, dict) and color:
        name = fight.get(f"{color}_fighter") or fight.get(color)
    if not name:
        name = "unknown_fighter"

    return get_session_dir(name, date, round_id)


__all__ = [
    "load_fight_state",
    "fighter_session_dir",
    "get_session_dir",
    "ROOT_DIR",
    "DATA_DIR",
    "LIVE_DIR",
    "fighter_dir",
]
