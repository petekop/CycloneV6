import importlib
import json
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]


def test_start_round_timer_allows_initial_hr_logging(tmp_path, monkeypatch):
    os.environ["BASE_DIR"] = str(tmp_path)

    data_dir = tmp_path / "FightControl" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    fight = {"red_fighter": "Red", "blue_fighter": "Blue", "fight_date": "2099-01-01"}
    (data_dir / "current_fight.json").write_text(json.dumps(fight))

    import fight_state
    import paths
    import round_timer

    importlib.reload(paths)
    importlib.reload(fight_state)
    importlib.reload(round_timer)

    # Avoid external side effects during the test
    monkeypatch.setattr(round_timer, "refresh_obs_overlay", lambda: None)

    async def _noop():
        return None

    monkeypatch.setattr(round_timer.obs, "stop_record", _noop)
    monkeypatch.setattr(round_timer.obs, "start_record", _noop)
    monkeypatch.setattr(round_timer, "play_audio", lambda *a, **k: None)
    monkeypatch.setattr(round_timer, "save_round_logs", lambda *a, **k: None)
    monkeypatch.setattr(round_timer, "build_session_summary", lambda *a, **k: None)
    monkeypatch.setattr(round_timer, "next_bout_number", lambda *a, **k: 1)
    import sys as _sys
    import types

    m = types.ModuleType("matplotlib")
    m.use = lambda *a, **k: None
    _sys.modules.setdefault("matplotlib", m)
    _sys.modules.setdefault("matplotlib.pyplot", types.ModuleType("pyplot"))
    _sys.modules.setdefault("pandas", types.ModuleType("pandas"))
    import round_summary

    monkeypatch.setattr(round_summary, "generate_round_summaries", lambda *a, **k: None)

    import FightControl.round_manager as rm

    importlib.reload(rm)
    from FightControl.round_manager import log_bpm

    round_timer.arm_round_status(1, 0, 1)
    round_timer.start_round_timer(1, 0)

    status = json.loads((data_dir / "round_status.json").read_text())
    assert status.get("status") in {"ACTIVE", "WAITING"}

    log_bpm("Red", "2099-01-01", "round_1", 80, "ACTIVE")

    log_file = tmp_path / "FightControl" / "fighter_data" / "Red" / "2099-01-01" / "round_1" / "hr_log.csv"
    assert log_file.exists()
    assert log_file.read_text().strip().endswith(",80,ACTIVE,round_1")

    t = round_timer._timer_thread
    if t:
        t.join(timeout=2)

    os.environ["BASE_DIR"] = str(BASE_DIR)
