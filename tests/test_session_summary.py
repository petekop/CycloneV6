import importlib
import json
from pathlib import Path

import pytest

from tests.helpers import use_tmp_base_dir

BASE_DIR = Path(__file__).resolve().parents[1]


def _setup(tmp_path, monkeypatch):
    """Configure environment and reload modules for testing."""
    paths = use_tmp_base_dir(tmp_path)
    monkeypatch.syspath_prepend(str(BASE_DIR))

    # Provide lightweight stubs for modules with heavy dependencies
    import sys
    import types

    mock_utils_checks = types.ModuleType("utils_checks")
    mock_utils_checks.load_tags = lambda *_args, **_kwargs: []
    monkeypatch.setitem(sys.modules, "utils_checks", mock_utils_checks)

    mock_round_summary = types.ModuleType("round_summary")
    mock_round_summary._round_boundaries = lambda total, dur, rest: [
        (i * (dur + rest), i * (dur + rest) + dur) for i in range(total)
    ]
    monkeypatch.setitem(sys.modules, "round_summary", mock_round_summary)

    import session_summary

    importlib.reload(session_summary)
    return session_summary, paths


@pytest.mark.parametrize("rest", [60, 30])
def test_round_metrics(tmp_path, monkeypatch, rest):
    ss, paths = _setup(tmp_path, monkeypatch)
    session_dir = paths.BASE_DIR / "session"
    session_dir.mkdir()

    duration = 5
    recovery_time = duration + rest
    hr_series = [
        {"seconds": 0, "bpm": 100, "zone": "yellow"},
        {"seconds": 1, "bpm": 110, "zone": "yellow"},
        {"seconds": 2, "bpm": 120, "zone": "red"},
        {"seconds": 3, "bpm": 130, "zone": "red"},
        {"seconds": 4, "bpm": 140, "zone": "red"},
        {"seconds": recovery_time, "bpm": 80, "zone": "blue"},
    ]
    (session_dir / "hr_data.json").write_text(json.dumps(hr_series))

    data_dir = paths.BASE_DIR / "FightControl" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    round_status = {"duration": duration, "rest": rest, "total_rounds": 1}
    (data_dir / "round_status.json").write_text(json.dumps(round_status))

    summary = ss.build_session_summary(session_dir)
    metrics = summary["round_metrics"]["round_1"]

    assert metrics["peak_hr"] == 140
    assert metrics["recovery_hr"] == 80
    assert metrics["zone_percentages"]["yellow"] == pytest.approx(0.4)
    assert metrics["zone_percentages"]["red"] == pytest.approx(0.6)


def test_round_metrics_no_round_status(tmp_path, monkeypatch):
    ss, paths = _setup(tmp_path, monkeypatch)
    session_dir = paths.BASE_DIR / "session"
    session_dir.mkdir()

    hr_series = [
        {"seconds": 0, "bpm": 100, "zone": "yellow"},
        {"seconds": 1, "bpm": 110, "zone": "yellow"},
        {"seconds": 2, "bpm": 120, "zone": "red"},
        {"seconds": 3, "bpm": 130, "zone": "red"},
        {"seconds": 4, "bpm": 140, "zone": "red"},
    ]
    (session_dir / "hr_data.json").write_text(json.dumps(hr_series))

    summary = ss.build_session_summary(session_dir)
    metrics = summary["round_metrics"]["round_1"]

    assert metrics["peak_hr"] == 140
    assert metrics["recovery_hr"] == 0
    assert metrics["zone_percentages"]["yellow"] == pytest.approx(0.4)
    assert metrics["zone_percentages"]["red"] == pytest.approx(0.6)


def test_round_metrics_with_status(tmp_path, monkeypatch):
    ss, paths = _setup(tmp_path, monkeypatch)
    session_dir = paths.BASE_DIR / "session"
    session_dir.mkdir()

    # Enriched HR data includes round and status fields
    hr_series = [
        {"seconds": 0, "bpm": 100, "zone": "yellow", "round": 1, "status": "ACTIVE"},
        {"seconds": 1, "bpm": 110, "zone": "yellow", "round": 1, "status": "ACTIVE"},
        {"seconds": 2, "bpm": 120, "zone": "red", "round": 1, "status": "ACTIVE"},
        {"seconds": 3, "bpm": 130, "zone": "red", "round": 1, "status": "ACTIVE"},
        {"seconds": 4, "bpm": 140, "zone": "red", "round": 1, "status": "ACTIVE"},
        {"seconds": 5, "bpm": 90, "round": 1, "status": "RESTING"},
        {"seconds": 55, "bpm": 85, "round": 1, "status": "RESTING"},
        # Next round begins before the 60s recovery mark
        {"seconds": 65, "bpm": 160, "round": 2, "status": "ACTIVE"},
    ]
    (session_dir / "hr_data.json").write_text(json.dumps(hr_series))

    summary = ss.build_session_summary(session_dir)
    metrics = summary["round_metrics"]["round_1"]

    assert metrics["peak_hr"] == 140
    # Recovery should use last RESTING sample, not the next round's ACTIVE sample
    assert metrics["recovery_hr"] == 85
    assert metrics["zone_percentages"]["yellow"] == pytest.approx(0.4)
    assert metrics["zone_percentages"]["red"] == pytest.approx(0.6)


def test_calc_time_in_zones(tmp_path, monkeypatch):
    ss, _ = _setup(tmp_path, monkeypatch)
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


def test_calc_bpm_stats(tmp_path, monkeypatch):
    ss, _ = _setup(tmp_path, monkeypatch)
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


def test_calc_time_in_zones_all_missing(tmp_path, monkeypatch):
    ss, _ = _setup(tmp_path, monkeypatch)
    hr_series = [
        {"bpm": 100},  # missing zone
        {"bpm": 110},  # missing zone
        {},  # missing both
    ]

    assert ss.calc_time_in_zones(hr_series) == {}


def test_calc_bpm_stats_no_bpm_values(tmp_path, monkeypatch):
    ss, _ = _setup(tmp_path, monkeypatch)
    hr_series = [
        {"zone": "blue"},  # missing bpm
        {"zone": "yellow"},  # missing bpm
        {},  # missing both
    ]

    assert ss.calc_bpm_stats(hr_series) == {"min": 0, "avg": 0, "max": 0}
