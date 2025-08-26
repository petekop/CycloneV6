"""FightControl package.

Modules are imported lazily to avoid side effects during test runs.  Submodules
such as :mod:`round_manager` and :mod:`fighter_paths` can be imported directly
without triggering heavyweight initialisation here.  These submodules include
safeguards so they remain reloadable even when entries in ``sys.modules`` are
manipulated by tests.
"""

__all__: list[str] = []

from .common.states import RoundState
from .round_manager import RoundManager, round_status

__all__ = ["RoundManager", "RoundState", "round_status"]
