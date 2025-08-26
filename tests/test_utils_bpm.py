import importlib
import json
import os
import sys
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")

BASE_DIR = Path(__file__).resolve().parents[1]


def test_read_bpm(tmp_path):
    os.environ["BASE_DIR"] = str(tmp_path)

    data_dir = tmp_path / "FightControl" / "data"
    overlay_dir = data_dir / "overlay"
    overlay_dir.mkdir(parents=True, exist_ok=True)
    (overlay_dir / "red_bpm.json").write_text(json.dumps({"bpm": 90}))
    (overlay_dir / "blue_bpm.json").write_text(json.dumps({"bpm": 110}))

    fighters = [
        {"name": "Red Fighter", "age": "30"},
        {"name": "Blue Fighter", "age": "25"},
    ]
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "fighters.json").write_text(json.dumps(fighters))
    (data_dir / "current_fight.json").write_text(
        json.dumps({"red_fighter": "Red Fighter", "blue_fighter": "Blue Fighter"})
    )

    zdir = tmp_path / "FightControl" / "fighter_data" / "red_fighter"
    zdir.mkdir(parents=True, exist_ok=True)
    (zdir / "zone_model.json").write_text(json.dumps({"fighter_id": "Red Fighter", "age": 30}))

    import paths

    importlib.reload(paths)
    import fighter_utils

    importlib.reload(fighter_utils)
    import utils_bpm

    importlib.reload(utils_bpm)
    utils_bpm.reset_bpm_state()

    red = utils_bpm.read_bpm("red")
    blue = utils_bpm.read_bpm("blue")
    with pytest.raises(ValueError):
        utils_bpm.read_bpm("green")

    assert red["bpm"] == 90
    assert blue["bpm"] == 110
    assert red["max_hr"] == int(211 - 0.64 * 30)
    assert blue["max_hr"] == int(211 - 0.64 * 25)


@pytest.mark.parametrize(
    "smoothing",
    [
        {"method": "invalid", "window": 5},
        {"method": "moving_average", "window": 0},
        {"method": "moving_average", "window": "a"},
        {"method": "savitzky_golay", "window": 3, "polyorder": 2},
    ],
)
def test_read_bpm_invalid_smoothing(tmp_path, smoothing):
    os.environ["BASE_DIR"] = str(tmp_path)

    overlay_dir = tmp_path / "FightControl" / "data" / "overlay"
    overlay_dir.mkdir(parents=True, exist_ok=True)
    (overlay_dir / "red_bpm.json").write_text(json.dumps({"bpm": 90, "max_hr": 180, "smoothing": smoothing}))

    import paths

    importlib.reload(paths)
    import utils_bpm

    importlib.reload(utils_bpm)
    utils_bpm.reset_bpm_state()

    with pytest.raises(ValueError):
        utils_bpm.read_bpm("red")


def test_even_window_savgol_applies_filter(tmp_path):
    os.environ["BASE_DIR"] = str(tmp_path)

    overlay_dir = tmp_path / "FightControl" / "data" / "overlay"
    overlay_dir.mkdir(parents=True, exist_ok=True)

    smoothing = {"method": "savitzky_golay", "window": 4, "polyorder": 2}

    import paths

    importlib.reload(paths)
    import utils_bpm

    importlib.reload(utils_bpm)
    utils_bpm.reset_bpm_state()

    readings = [10, 15, 14, 20, 19]
    for idx, bpm in enumerate(readings, 1):
        (overlay_dir / "red_bpm.json").write_text(json.dumps({"bpm": bpm, "max_hr": 180, "smoothing": smoothing}))
        result = utils_bpm.read_bpm("red")
        if idx < 5:
            assert result["bpm"] == pytest.approx(sum(readings[:idx]) / idx)

    expected = float(np.polyval(np.polyfit(range(5), readings, 2), 4))
    assert result["bpm"] == pytest.approx(expected)
    assert utils_bpm._HISTORY["red"].maxlen == 5


def test_even_window_savgol_sets_history_before_fit(tmp_path):
    os.environ["BASE_DIR"] = str(tmp_path)

    overlay_dir = tmp_path / "FightControl" / "data" / "overlay"
    overlay_dir.mkdir(parents=True, exist_ok=True)

    smoothing = {"method": "savitzky_golay", "window": 4, "polyorder": 2}

    import paths

    importlib.reload(paths)
    import utils_bpm

    importlib.reload(utils_bpm)
    utils_bpm.reset_bpm_state()

    (overlay_dir / "red_bpm.json").write_text(json.dumps({"bpm": 10, "max_hr": 180, "smoothing": smoothing}))
    result = utils_bpm.read_bpm("red")

    assert result["bpm"] == pytest.approx(10)
    assert utils_bpm._HISTORY["red"].maxlen == 5


def test_savgol_small_history_buffer(tmp_path):
    pytest.importorskip("scipy")
    from scipy.signal import savgol_filter

    os.environ["BASE_DIR"] = str(tmp_path)

    data_dir = tmp_path / "FightControl" / "data"
    overlay_dir = data_dir / "overlay"
    overlay_dir.mkdir(parents=True, exist_ok=True)

    # Zone model provides smoothing configuration
    zdir = tmp_path / "FightControl" / "fighter_data" / "red_fighter"
    zdir.mkdir(parents=True, exist_ok=True)
    (zdir / "zone_model.json").write_text(
        json.dumps(
            {
                "max_hr": 180,
                "smoothing": {
                    "method": "savitzky_golay",
                    "window": 3,
                    "polyorder": 1,
                },
            }
        )
    )

    (data_dir / "current_fight.json").write_text(
        json.dumps({"red_fighter": "Red Fighter", "blue_fighter": "Blue Fighter"})
    )

    import paths

    importlib.reload(paths)
    import utils_bpm

    importlib.reload(utils_bpm)
    utils_bpm.reset_bpm_state()

    readings = [100, 120, 110]
    expected = savgol_filter(readings, 3, 1)[-1]
    for bpm in readings:
        (overlay_dir / "red_bpm.json").write_text(json.dumps({"bpm": bpm}))
        result = utils_bpm.read_bpm("red")

    assert result["bpm"] == pytest.approx(expected)
    assert utils_bpm._HISTORY["red"].maxlen == 3


def test_reset_bpm_state(tmp_path):
    os.environ["BASE_DIR"] = str(tmp_path)
    import paths

    importlib.reload(paths)
    import utils_bpm

    importlib.reload(utils_bpm)

    # Populate the module level caches
    utils_bpm._HISTORY["red"] = [1]
    utils_bpm._PEAKS["red"] = 200
    utils_bpm._RECOVERY_LOGGED.add("red")

    # Ensure the helper clears everything
    utils_bpm.reset_bpm_state()
    assert utils_bpm._HISTORY == {}
    assert utils_bpm._PEAKS == {}
    assert utils_bpm._RECOVERY_LOGGED == set()


def test_peak_resets_between_rounds(tmp_path):
    os.environ["BASE_DIR"] = str(tmp_path)

    data_dir = tmp_path / "FightControl" / "data"
    overlay_dir = data_dir / "overlay"
    overlay_dir.mkdir(parents=True, exist_ok=True)
    status_path = data_dir / "round_status.json"

    import paths

    importlib.reload(paths)
    import utils_bpm

    importlib.reload(utils_bpm)
    utils_bpm.reset_bpm_state()

    # Round 1 active
    (overlay_dir / "red_bpm.json").write_text(json.dumps({"bpm": 100}))
    status_path.write_text(json.dumps({"status": "ACTIVE", "start_time": "1"}))
    utils_bpm.read_bpm("red")
    assert utils_bpm._PEAKS["red"] == 100

    # Peak rises within same round
    (overlay_dir / "red_bpm.json").write_text(json.dumps({"bpm": 150}))
    status_path.write_text(json.dumps({"status": "ACTIVE", "start_time": "1"}))
    utils_bpm.read_bpm("red")
    assert utils_bpm._PEAKS["red"] == 150

    # Transition to rest
    status_path.write_text(json.dumps({"status": "REST", "start_time": "1"}))
    utils_bpm.read_bpm("red")
    assert utils_bpm._PEAKS["red"] == 150

    # New round becomes active
    (overlay_dir / "red_bpm.json").write_text(json.dumps({"bpm": 120}))
    status_path.write_text(json.dumps({"status": "ACTIVE", "start_time": "2"}))
    utils_bpm.read_bpm("red")
    assert utils_bpm._PEAKS["red"] == 120


def test_second_round_peak_independent(tmp_path):
    os.environ["BASE_DIR"] = str(tmp_path)

    data_dir = tmp_path / "FightControl" / "data"
    overlay_dir = data_dir / "overlay"
    overlay_dir.mkdir(parents=True, exist_ok=True)
    status_path = data_dir / "round_status.json"

    import paths

    importlib.reload(paths)
    import utils_bpm

    importlib.reload(utils_bpm)
    utils_bpm.reset_bpm_state()

    # Round 1 active with a peak
    (overlay_dir / "red_bpm.json").write_text(json.dumps({"bpm": 100}))
    status_path.write_text(json.dumps({"status": "ACTIVE", "start_time": "1"}))
    utils_bpm.read_bpm("red")
    (overlay_dir / "red_bpm.json").write_text(json.dumps({"bpm": 150}))
    status_path.write_text(json.dumps({"status": "ACTIVE", "start_time": "1"}))
    utils_bpm.read_bpm("red")

    # Recovery phase logs and resets peak
    status_path.write_text(json.dumps({"status": "RECOVERY", "start_time": "1"}))
    utils_bpm.read_bpm("red")
    assert utils_bpm._PEAKS["red"] == 0

    # Second round starts fresh
    (overlay_dir / "red_bpm.json").write_text(json.dumps({"bpm": 120}))
    status_path.write_text(json.dumps({"status": "ACTIVE", "start_time": "2"}))
    utils_bpm.read_bpm("red")
    assert utils_bpm._PEAKS["red"] == 120
    (overlay_dir / "red_bpm.json").write_text(json.dumps({"bpm": 180}))
    status_path.write_text(json.dumps({"status": "ACTIVE", "start_time": "2"}))
    utils_bpm.read_bpm("red")
    assert utils_bpm._PEAKS["red"] == 180
