import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path


def setup_logging(level: int = logging.INFO) -> None:
    """Configure basic logging for standalone execution.

    When this module is imported, logging configuration is left to the
    application.  Scripts invoking the HR logger directly can call this helper
    to initialise logging with a sensible default level.
    """

    logging.basicConfig(level=level)


logger = logging.getLogger(__name__)

try:
    import matplotlib

    matplotlib.use("Agg")  # Use non-GUI backend for PNG generation
    import matplotlib.pyplot as plt
except Exception as e:
    import traceback

    traceback.print_exc()
    print(f"[HRLogger] Matplotlib import failed: {e}")
    plt = None

# Ensure the project root is on sys.path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from FightControl.fight_utils import safe_filename
from FightControl.round_manager import round_status
from paths import BASE_DIR
from utils_checks import get_session_dir, next_bout_number

FIGHTER_DIR = BASE_DIR / "FightControl" / "fighter_data"
FIGHT_JSON = BASE_DIR / "FightControl" / "data" / "current_fight.json"
OVERLAY_DIR = BASE_DIR / "FightControl" / "data" / "overlay"


def read_overlay(color: str) -> dict:
    try:
        path = OVERLAY_DIR / f"{color}_bpm.json"
        return json.loads(path.read_text())
    except Exception:
        return {"bpm": 0}


def load_zone_model(fighter_name: str | None) -> dict:
    if not fighter_name:
        return {}
    safe = fighter_name.lower().replace(" ", "_")
    path = FIGHTER_DIR / safe / "zone_model.json"
    try:
        data = json.loads(path.read_text()) if path.exists() else {}
    except Exception:
        return {}

    # Coerce numeric fields to their appropriate types where possible so
    # downstream calculations don't have to defensively cast.
    for key in ("rest_hr", "max_hr", "age"):
        if key in data:
            try:
                data[key] = float(data[key]) if key != "age" else int(data[key])
            except (TypeError, ValueError):
                del data[key]

    thresholds = data.get("zone_thresholds")
    if isinstance(thresholds, dict):
        clean: dict[str, list[float]] = {}
        for name, bounds in thresholds.items():
            try:
                low, high = bounds
                clean[name] = [float(low), float(high)]
            except Exception:
                continue
        data["zone_thresholds"] = clean

    smoothing = data.get("smoothing")
    if isinstance(smoothing, dict):
        if "window" in smoothing:
            try:
                smoothing["window"] = int(smoothing["window"])
            except (TypeError, ValueError):
                del smoothing["window"]
        if "polyorder" in smoothing:
            try:
                smoothing["polyorder"] = int(smoothing["polyorder"])
            except (TypeError, ValueError):
                del smoothing["polyorder"]
    return data


def calc_metrics(bpm: int, model: dict, ema: list[int] | float | None) -> tuple[float, str, list[int] | float | None]:
    # Defensive casting of model values in case ``load_zone_model`` was bypassed
    rest_hr = float(model.get("rest_hr", 60))
    max_hr = float(model.get("max_hr", 180))
    smoothing = model.get("smoothing") or {}
    method = smoothing.get("method")
    window = int(smoothing.get("window", 5))

    if method == "ewma":
        alpha = 2 / (window + 1)
        ema = bpm if ema is None else alpha * bpm + (1 - alpha) * ema
        bpm_val = ema
    elif method == "moving_average":
        if ema is None or not isinstance(ema, list):
            ema = []
        ema.append(bpm)
        if len(ema) > window:
            ema.pop(0)
        bpm_val = sum(ema) / len(ema)
    else:
        bpm_val = bpm

    effort = ((bpm_val - rest_hr) / (max_hr - rest_hr)) * 100 if max_hr > rest_hr else 0
    effort = max(0.0, min(100.0, effort))

    zone_key = None
    thresholds = model.get("zone_thresholds", {})
    for name, bounds in sorted(thresholds.items(), key=lambda x: x[1][0]):
        try:
            low, high = bounds
            low = float(low)
            high = float(high)
        except Exception:
            continue
        if low <= effort < high:
            zone_key = name
            break
    if zone_key is None and thresholds:
        zone_key = max(thresholds.items(), key=lambda x: x[1][1])[0]

    zone = model.get("zone_colours", {}).get(zone_key, zone_key or "none")
    return effort, zone, ema


def save_series(name: str, date: str, bout: str, series: list[dict]) -> None:
    base = get_session_dir(name, date, bout)
    Path(base).mkdir(parents=True, exist_ok=True)
    (base / "hr_data.json").write_text(json.dumps(series, indent=2))

    if plt is not None and series:
        times = [p["time"] for p in series]
        bpm = [p.get("bpm", 0) for p in series]
        max_hr = series[0].get("max_hr", 180)

        plt.figure(figsize=(8, 3))
        zones = [
            (0.0, 0.6, "blue"),
            (0.6, 0.7, "limegreen"),
            (0.7, 0.8, "yellow"),
            (0.8, 0.9, "orange"),
            (0.9, 1.1, "red"),
        ]
        for low, high, color in zones:
            plt.axhspan(low * max_hr, high * max_hr, facecolor=color, alpha=0.2)

        plt.plot(times, bpm, color="lime", linewidth=2)
        plt.xlabel("Time (s)")
        plt.ylabel("BPM")
        plt.title(f"{name} Heart Rate")
        plt.ylim(0, max_hr)
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(base / "graph.png")
        plt.close()


def main() -> None:
    try:
        fight = json.loads(FIGHT_JSON.read_text())
    except Exception:
        logger.exception("Failed to load current fight")
        return

    red = fight.get("red_fighter") or fight.get("red") or "Red"
    blue = fight.get("blue_fighter") or fight.get("blue") or "Blue"
    rounds = fight.get("rounds", 1)
    date = fight.get("fight_date", datetime.now().strftime("%Y-%m-%d"))

    red_model = load_zone_model(red)
    blue_model = load_zone_model(blue)
    red_ema = None
    blue_ema = None

    bout_num = next_bout_number(date, red, blue)
    safe_red = safe_filename(red).upper()
    safe_blue = safe_filename(blue).upper()
    bout_name = f"{date}_{safe_red}_vs_{safe_blue}_BOUT{bout_num}"

    start = time.time()
    red_series = []
    blue_series = []

    while True:
        try:
            status_data = round_status()
            status = status_data.get("status")
            round_no = status_data.get("round")
        except Exception:
            status = None
            round_no = None

        elapsed = int(time.time() - start)

        red_raw = read_overlay("red")
        red_bpm = int(red_raw.get("bpm", 0))
        red_effort, red_zone, red_ema = calc_metrics(red_bpm, red_model, red_ema)
        red_data = {
            "bpm": red_bpm,
            "effort_percent": round(red_effort),
            "zone": red_zone,
            "time": elapsed,
            "max_hr": red_model.get("max_hr", 180),
            "status": status,
            "round": round_no,
        }
        (OVERLAY_DIR / "red_bpm.json").write_text(json.dumps(red_data))

        red_entry = dict(red_data)

        blue_raw = read_overlay("blue")
        blue_bpm = int(blue_raw.get("bpm", 0))
        blue_effort, blue_zone, blue_ema = calc_metrics(blue_bpm, blue_model, blue_ema)
        blue_data = {
            "bpm": blue_bpm,
            "effort_percent": round(blue_effort),
            "zone": blue_zone,
            "time": elapsed,
            "max_hr": blue_model.get("max_hr", 180),
            "status": status,
            "round": round_no,
        }
        (OVERLAY_DIR / "blue_bpm.json").write_text(json.dumps(blue_data))

        blue_entry = dict(blue_data)

        red_series.append(red_entry)
        blue_series.append(blue_entry)

        if status == "ENDED":
            break
        time.sleep(1)

    save_series(red, date, bout_name, red_series)
    save_series(blue, date, bout_name, blue_series)
    logger.info("HR data saved for bout %s (%s rounds)", bout_num, rounds)


if __name__ == "__main__":
    setup_logging()
    if os.environ.get("TEST_MODE") == "1":
        import threading

        thread = threading.Thread(target=main, daemon=True)
        thread.start()
        thread.join(5)
        if thread.is_alive():
            print("[HRLogger] main() timeout reached, terminating")
            os._exit(0)
    else:
        main()
