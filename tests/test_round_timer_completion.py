import importlib
import json
import os
import sys
import time
from pathlib import Path

import pytest

pytest.importorskip("matplotlib")

BASE_DIR = Path(__file__).resolve().parents[1]


def test_default_on_complete_builds_summaries(tmp_path, monkeypatch):
    os.environ["BASE_DIR"] = str(tmp_path)

    data_dir = tmp_path / "FightControl" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    fight = {"red_fighter": "Red", "blue_fighter": "Blue", "fight_date": "2099-01-01"}
    (data_dir / "current_fight.json").write_text(json.dumps(fight))
    (data_dir / "current_round.txt").write_text("round_1")
    (data_dir / "round_status.json").write_text(
        json.dumps(
            {
                "round": 1,
                "duration": 0,
                "rest": 0,
                "total_rounds": 1,
                "status": "ACTIVE",
            }
        )
    )

    import fight_state
    import paths
    import round_timer

    importlib.reload(paths)
    importlib.reload(fight_state)
    importlib.reload(round_timer)

    calls = {"summaries": 0, "sessions": []}

    monkeypatch.setattr(round_timer, "refresh_obs_overlay", lambda: None)

    async def _noop():
        return None

    monkeypatch.setattr(round_timer.obs, "stop_record", _noop)
    monkeypatch.setattr(round_timer.obs, "start_record", _noop)
    monkeypatch.setattr(round_timer, "play_audio", lambda *a, **k: None)
    monkeypatch.setattr(round_timer, "save_round_logs", lambda *a, **k: None)
    monkeypatch.setattr(round_timer, "next_bout_number", lambda *a, **k: 1)

    def fake_generate_round_summaries(meta):
        calls["summaries"] += 1

    def fake_build_session_summary(session_dir):
        calls["sessions"].append(session_dir)

    import round_summary

    monkeypatch.setattr(round_summary, "generate_round_summaries", fake_generate_round_summaries)
    monkeypatch.setattr(round_timer, "build_session_summary", fake_build_session_summary)

    round_timer.start_round_timer(0, 0)
    t = round_timer._timer_thread
    if t:
        t.join(timeout=1)
    time.sleep(0.05)

    assert calls["summaries"] == 1
    assert len(calls["sessions"]) == 2

    os.environ["BASE_DIR"] = str(BASE_DIR)
