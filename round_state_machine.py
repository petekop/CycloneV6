"""Simple round state machine persisting state to disk."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from paths import BASE_DIR

STATE_PATH: Path = BASE_DIR / "state" / "round_state.json"


@dataclass
class RoundStateMachine:
    """State machine tracking bout round transitions.

    Parameters
    ----------
    total_rounds:
        Total number of rounds in the bout.
    round:
        Current round number (1-indexed).
    state:
        Current state string. One of ``WAITING``, ``ACTIVE``, ``RESTING`` or
        ``ENDED``.
    path:
        Location of ``round_state.json``. Defaults to
        ``BASE_DIR/state/round_state.json``.
    persist:
        When ``True`` (default) the state is written to ``path`` on
        construction.
    """

    total_rounds: int
    round: int = 1
    state: str = "WAITING"
    path: Path = STATE_PATH
    persist: bool = True

    def __post_init__(self) -> None:  # pragma: no cover - trivial
        if self.persist:
            self._persist()

    # ------------------------ Persistence helpers -------------------------
    def _persist(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "round": self.round,
            "total_rounds": self.total_rounds,
            "status": self.state,
        }
        self.path.write_text(json.dumps(data, indent=2))

    @classmethod
    def load(cls, path: Path = STATE_PATH) -> "RoundStateMachine":
        data = json.loads(path.read_text())
        return cls(
            total_rounds=int(data.get("total_rounds", 1)),
            round=int(data.get("round", 1)),
            state=data.get("status", "WAITING"),
            path=path,
            persist=False,
        )

    # --------------------------- State helpers ----------------------------
    def start_round(self) -> None:
        """Transition to ``ACTIVE`` state."""
        if self.state not in {"WAITING", "RESTING"}:
            raise ValueError(f"cannot start round from {self.state}")
        if self.state == "RESTING":
            self.round += 1
        if self.round > self.total_rounds:
            raise ValueError("no more rounds available")
        self.state = "ACTIVE"
        self._persist()

    def end_round(self) -> None:
        """End the current round, transitioning to rest or ended."""
        if self.state != "ACTIVE":
            raise ValueError(f"cannot end round from {self.state}")
        if self.round >= self.total_rounds:
            self.state = "ENDED"
        else:
            self.state = "RESTING"
        self._persist()
