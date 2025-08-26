"""Simple heart-rate zone tracker placeholder.

This module exposes :class:`ZoneTracker` with a ``stats`` method that
returns heart-rate statistics for the most recently ended round.  The
real application may provide a richer implementation; here we return an
empty mapping so callers can safely include the field.
"""

from __future__ import annotations

from typing import Any, Dict


def build_zone_model(fighter: str | None) -> Dict[str, Any]:
    """Return a basic zone model for ``fighter``.

    The real project generates detailed models based on age and previous
    session data.  For testing we provide sensible defaults so callers can
    continue to calculate effort percentages and zone labels without pulling
    in the heavy HR logger dependency.
    """
    return {
        "fighter_id": fighter or "",
        "max_hr": 180,
        "rest_hr": 60,
        "zone_thresholds": {},
        "zone_colours": {},
    }


class ZoneTracker:
    """Placeholder tracker supplying heart-rate statistics."""

    @staticmethod
    def stats() -> Dict[str, Any]:
        """Return heart-rate statistics for the latest round.

        The default implementation returns an empty mapping.  External
        components can monkeypatch this during tests or replace the module
        with a more featureful version.
        """
        return {}
