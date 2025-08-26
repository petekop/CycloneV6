import importlib
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

pytest.importorskip("pandas")

from tests.helpers import use_tmp_base_dir


def test_load_tag_events_from_tag_log(tmp_path, monkeypatch):
    """_load_tag_events should read tag_log.csv when no per-round tags exist."""

    use_tmp_base_dir(tmp_path)

    import round_summary

    importlib.reload(round_summary)

    fp = round_summary.fighter_paths

    date = "2099-01-01"
    bout = "test_bout"
    session_dir = fp.bout_dir("Red Fighter", date, bout)

    start = datetime(2025, 1, 1)
    hr_data = [{"timestamp": (start + timedelta(seconds=i)).isoformat(), "bpm": 100 + i} for i in range(5)]
    (session_dir / "hr_continuous.json").write_text(json.dumps(hr_data))

    tag_lines = [
        "timestamp,fighter,tag",
        f"{(start + timedelta(seconds=1)).isoformat()},red,Jab",
        f"{(start + timedelta(seconds=3)).isoformat()},red,Cross",
    ]
    (session_dir / "tag_log.csv").write_text("\n".join(tag_lines))

    events = round_summary._load_tag_events(session_dir, "red")
    assert events == [(1.0, "Jab"), (3.0, "Cross")]
