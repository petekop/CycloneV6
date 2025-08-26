import pytest

from FightControl.round_manager import to_overlay


@pytest.mark.parametrize(
    "state,expected",
    [
        ("LIVE", "ACTIVE"),
        ("REST", "RESTING"),
        ("IDLE", "READY"),
        ("PAUSED", "PAUSED"),
        ("ENDED", "ENDED"),
    ],
)
def test_to_overlay_known_mappings(state, expected):
    assert to_overlay(state) == expected


def test_to_overlay_unknown_passthrough():
    assert to_overlay("UNKNOWN") == "UNKNOWN"
