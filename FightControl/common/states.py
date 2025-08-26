"""Round state enumeration and helpers.

This module centralises the round state values used throughout the
application.  It also provides a mapping to translate internal state
names to the values expected by overlay components.
"""

from __future__ import annotations

from enum import Enum


class RoundState(str, Enum):
    """Enumeration of round states."""

    IDLE = "IDLE"
    LIVE = "LIVE"
    REST = "REST"
    PAUSED = "PAUSED"
    ENDED = "ENDED"


# Mapping from internal :class:`RoundState` values to overlay strings.
OVERLAY_STATE_MAP: dict[RoundState, str] = {
    RoundState.IDLE: "WAITING",
    RoundState.LIVE: "ACTIVE",
    RoundState.REST: "RESTING",
    RoundState.PAUSED: "PAUSED",
    RoundState.ENDED: "ENDED",
}


def to_overlay(state: str) -> str:
    """Translate internal ``state`` name to overlay representation.

    Parameters
    ----------
    state:
        Name of the internal round state.  Comparison is case-insensitive.

    Returns
    -------
    str
        Corresponding overlay state name.  Unknown states are uppercased and
        returned unchanged.
    """

    try:
        enum_state = RoundState[state.upper()]
    except Exception:
        return state.upper()
    return OVERLAY_STATE_MAP.get(enum_state, enum_state.value)


__all__ = ["RoundState", "OVERLAY_STATE_MAP", "to_overlay"]
