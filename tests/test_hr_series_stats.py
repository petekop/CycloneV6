import importlib
import sys
import types
from pathlib import Path

import pytest


@pytest.fixture
def ss(monkeypatch):
    mock_utils_checks = types.ModuleType("utils_checks")
    mock_utils_checks.load_tags = lambda *_args, **_kwargs: []
    monkeypatch.setitem(sys.modules, "utils_checks", mock_utils_checks)
    base_dir = Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(base_dir))
    import session_summary

    importlib.reload(session_summary)
    return session_summary


def test_calc_time_in_zones(ss):
    hr_series = [
        {"zone": "blue", "bpm": 100},
        {"zone": "yellow", "bpm": 110},
        {"bpm": 120},  # missing zone
        {"zone": "yellow", "bpm": 130},
        {"zone": "red"},  # missing bpm
        {},  # missing both
    ]

    assert ss.calc_time_in_zones(hr_series) == {
        "blue": 1,
        "yellow": 2,
        "red": 1,
    }
    assert ss.calc_time_in_zones([]) == {}


def test_calc_bpm_stats(ss):
    hr_series = [
        {"zone": "blue", "bpm": 100},
        {"zone": "yellow", "bpm": 110},
        {"bpm": 120},  # missing zone
        {"zone": "yellow", "bpm": 130},
        {"zone": "red"},  # missing bpm
        {},  # missing both
    ]

    assert ss.calc_bpm_stats(hr_series) == {
        "min": 100,
        "avg": 115,
        "max": 130,
    }
    assert ss.calc_bpm_stats([]) == {"min": 0, "avg": 0, "max": 0}

    hr_series_missing = [
        {"zone": "blue"},  # missing bpm
        {"zone": "yellow"},  # missing bpm
        {},  # missing both
    ]
    assert ss.calc_bpm_stats(hr_series_missing) == {"min": 0, "avg": 0, "max": 0}
