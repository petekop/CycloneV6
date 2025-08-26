import importlib
import importlib.util
import json
import sys
import types
from datetime import datetime, timedelta
from pathlib import Path

import pytest

matplotlib = pytest.importorskip("matplotlib")
matplotlib.use("Agg")
from matplotlib import pyplot as plt
from matplotlib.collections import LineCollection

# Manually load helpers without importing heavy FightControl package
BASE_DIR = Path(__file__).resolve().parents[1]
fu_spec = importlib.util.spec_from_file_location(
    "FightControl.fight_utils", BASE_DIR / "FightControl" / "fight_utils.py"
)
fight_utils = importlib.util.module_from_spec(fu_spec)
fu_spec.loader.exec_module(fight_utils)
fc_pkg = types.ModuleType("FightControl")
fc_pkg.fight_utils = fight_utils
sys.modules.setdefault("FightControl", fc_pkg)
sys.modules.setdefault("FightControl.fight_utils", fight_utils)


def _load_fighter_paths():
    fp_spec = importlib.util.spec_from_file_location(
        "FightControl.fighter_paths", BASE_DIR / "FightControl" / "fighter_paths.py"
    )
    module = importlib.util.module_from_spec(fp_spec)
    fp_spec.loader.exec_module(module)
    fc_pkg.fighter_paths = module
    sys.modules["FightControl.fighter_paths"] = module
    return module


safe_filename = fight_utils.safe_filename


def test_generate_round_summaries_renders_tags(tmp_path, monkeypatch):
    """Tags from ``tag_log.csv`` should render as vertical lines for both fighters."""

    monkeypatch.setenv("BASE_DIR", str(tmp_path))

    # Reload paths with monkeypatched base
    import paths

    importlib.reload(paths)
    fighter_paths = _load_fighter_paths()
    import round_summary

    importlib.reload(round_summary)

    date = "2099-01-01"
    red = "Red Fighter"
    blue = "Blue Fighter"
    bout = f"{safe_filename(red)}_vs_{safe_filename(blue)}"

    red_dir = fighter_paths.bout_dir(red, date, bout)
    blue_dir = fighter_paths.bout_dir(blue, date, bout)

    # 10s of heart rate data
    start = datetime(2025, 1, 1)
    hr_data = [{"timestamp": (start + timedelta(seconds=i)).isoformat(), "bpm": 100 + i} for i in range(10)]

    (red_dir / "hr_continuous.json").write_text(json.dumps(hr_data))
    (blue_dir / "hr_continuous.json").write_text(json.dumps(hr_data))

    # Tag events
    tags = [
        "timestamp,fighter,tag",
        f"{(start + timedelta(seconds=1)).isoformat()},red,Jab",
        f"{(start + timedelta(seconds=4)).isoformat()},red,Cross",
        f"{(start + timedelta(seconds=2)).isoformat()},blue,Kick",
    ]
    tag_data = "\n".join(tags)
    (red_dir / "tag_log.csv").write_text(tag_data)
    # ``generate_round_summaries`` reads from ``events.csv`` so mirror the data.
    (red_dir / "events.csv").write_text(tag_data)

    fight = {
        "red_fighter": red,
        "blue_fighter": blue,
        "fight_date": date,
        "round_type": "1x1",
        "round_duration": 10,
        "rest_duration": 0,
    }

    captured = {}
    real_subplots = plt.subplots

    def fake_subplots(*args, **kwargs):
        fig, axes = real_subplots(*args, **kwargs)
        captured["axes"] = axes
        return fig, axes

    monkeypatch.setattr(plt, "subplots", fake_subplots)
    monkeypatch.setattr(plt, "close", lambda fig: None)

    round_summary.generate_round_summaries(fight)

    red_ax, blue_ax = captured["axes"]

    # Count LineCollections to confirm tag markers are drawn
    assert sum(isinstance(c, LineCollection) for c in red_ax.collections) >= 1
    assert sum(isinstance(c, LineCollection) for c in blue_ax.collections) >= 1
