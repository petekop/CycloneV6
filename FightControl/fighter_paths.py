from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import paths
from FightControl.fight_utils import safe_filename

# ``importlib.reload`` requires modules to have a ``__spec__`` attribute and for
# the parent package's ``__path__`` to include this file's directory.  Some
# lightweight test setups replace the ``FightControl`` package with a minimal
# stub that lacks these details which breaks reloading.  The following safeguards
# ensure both attributes are populated.
if globals().get("__spec__") is None:  # pragma: no cover - defensive
    __spec__ = importlib.util.spec_from_file_location(__name__, __file__)

parent = sys.modules.get("FightControl")  # pragma: no cover - defensive
if parent is not None and not getattr(parent, "__path__", None):
    parent.__path__ = [str(Path(__file__).resolve().parent)]


def _base_dir() -> Path:
    """Return the current base directory."""

    return Path(paths.BASE_DIR)


BASE_DIR = _base_dir()


def refresh_base_dir() -> None:
    """Refresh the exported :data:`BASE_DIR` constant."""

    global BASE_DIR
    BASE_DIR = _base_dir()


def bout_dir(fighter_name: str, date: str, bout_name: str) -> Path:
    """Return the session directory for ``bout_name`` on ``date``.

    ``fighter_name`` is accepted for API compatibility but is not used when
    constructing the directory.  The returned directory lives beneath
    ``FightControl/logs`` and is created if required.
    """

    safe_date = safe_filename(date)
    safe_bout = safe_filename(bout_name)
    base_dir = _base_dir()
    path = base_dir / "FightControl" / "logs" / safe_date / safe_bout
    path.mkdir(parents=True, exist_ok=True)
    return path


def round_dir(fighter_name: str, date: str, bout_name: str, round_id: str) -> Path:
    """Return the directory for ``round_id`` within a bout.

    ``fighter_name`` is accepted for API compatibility only.  The directory
    is created on demand beneath :func:`bout_dir`.
    """

    base = bout_dir(fighter_name, date, bout_name)
    path = base / safe_filename(round_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def summary_dir(fighter_name: str, date: str, bout_name: str) -> Path:
    """Return directory for storing session summaries for a fighter."""

    safe_name = safe_filename(fighter_name)
    safe_bout = safe_filename(bout_name)
    base_dir = _base_dir()
    path = base_dir / "FightControl" / "fighter_data" / safe_name / date / safe_bout
    return path


def fight_bout_dir(fighter_name: str, bout_name: str) -> Path:
    """Return ``{BASE}/Fights/<Fighter>/<Bout>`` creating it on demand."""

    safe_name = safe_filename(fighter_name)
    safe_bout = safe_filename(bout_name)
    base_dir = _base_dir()
    path = base_dir / "Fights" / safe_name / safe_bout
    path.mkdir(parents=True, exist_ok=True)
    return path


def fight_round_dir(fighter_name: str, bout_name: str, round_id: str) -> Path:
    """Return ``{BASE}/Fights/<Fighter>/<Bout>/<RoundN>`` directory."""

    base = fight_bout_dir(fighter_name, bout_name)
    path = base / safe_filename(round_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


__all__ = [
    "BASE_DIR",
    "bout_dir",
    "round_dir",
    "summary_dir",
    "fight_bout_dir",
    "fight_round_dir",
    "refresh_base_dir",
]
