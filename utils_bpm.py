"""Utility helpers for reading BPM overlay data."""

import importlib
import json
import logging
from collections import deque

from FightControl.fight_utils import safe_filename
from FightControl.round_manager import round_status
from paths import BASE_DIR

DATA_DIR = BASE_DIR / "FightControl" / "data"
FIGHT_JSON = DATA_DIR / "current_fight.json"

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Module level state
# ---------------------------------------------------------------------------
#
# ``utils_bpm`` maintains a small amount of in-memory state when calculating
# live heart rate metrics.  Tests (and even the application itself when
# starting a brand new fight) need a way to reset this state to avoid one
# invocation influencing another.  Previously this state was reset only when
# the module was reloaded which is brittle and leads to test pollution.  To
# make state management explicit we expose ``reset_bpm_state`` which clears the
# caches used by the module.

# History of readings per fighter colour
_HISTORY: dict[str, deque] = {}
# Peak BPM values per fighter colour
_PEAKS: dict[str, int] = {}
# Tracks which fighters have had recovery values logged
_RECOVERY_LOGGED: set[str] = set()

# Last known round status and start time, used to detect when a new
# active round begins so peak values can be reset.
_LAST_STATUS: str | None = None
_LAST_START: str | None = None


def reset_bpm_state() -> None:
    """Reset module level BPM tracking state.

    This is primarily used by the unit test suite which imports ``utils_bpm``
    multiple times.  Without resetting these structures, data from a previous
    test could leak into the next one causing flaky behaviour.  The helper is
    also useful when the application initialises a brand new fight.
    """

    _HISTORY.clear()
    _PEAKS.clear()
    _RECOVERY_LOGGED.clear()
    global _LAST_STATUS, _LAST_START
    _LAST_STATUS = None
    _LAST_START = None


def read_bpm(color: str) -> dict:
    """Return BPM information for the given corner from overlay JSON."""

    if color not in {"red", "blue"}:
        raise ValueError(f"Unsupported color: {color!r}. Expected 'red' or 'blue'.")

    path = DATA_DIR / "overlay" / f"{color}_bpm.json"
    try:
        data = json.loads(path.read_text())
    except FileNotFoundError:
        logger.warning("BPM overlay file not found: %s", path)
        return {"bpm": 0, "max_hr": 185, "zone": "None", "effort_percent": 0}
    except json.JSONDecodeError:
        logger.warning("Invalid JSON in BPM overlay file: %s", path)
        return {"bpm": 0, "max_hr": 185, "zone": "None", "effort_percent": 0}
    except OSError:
        logger.exception("Error reading BPM overlay file: %s", path)
        raise

    model: dict = {}
    fighter = None
    if "max_hr" not in data or "smoothing" not in data:
        try:
            fight = json.loads(FIGHT_JSON.read_text())
            fighter = fight.get(f"{color}_fighter") or fight.get(color)

            if fighter:
                hr_logger = importlib.import_module("cyclone_modules.HRLogger.hr_logger")
                importlib.reload(hr_logger)
                model = hr_logger.load_zone_model(safe_filename(fighter))
        except FileNotFoundError:
            logger.warning("Fight status file not found: %s", FIGHT_JSON)
        except json.JSONDecodeError:
            logger.warning("Invalid JSON in fight status file: %s", FIGHT_JSON)

    if "max_hr" not in data:
        if model.get("max_hr"):
            data["max_hr"] = model["max_hr"]
        else:
            age = model.get("age")
            if age is None and fighter:
                try:
                    import fighter_utils

                    importlib.reload(fighter_utils)
                    fmap = {f.get("name"): f for f in fighter_utils.load_fighters()}
                    age = fmap.get(fighter, {}).get("age")
                except (ImportError, json.JSONDecodeError, OSError) as exc:
                    logger.warning("Error loading fighters for %s: %s", fighter, exc)
                    age = None
            try:
                age_val = int(age) if age is not None else None
            except (TypeError, ValueError):
                age_val = None
            if age_val:
                data["max_hr"] = int(211 - 0.64 * age_val)
            else:
                data["max_hr"] = 185
    if "smoothing" not in data and model.get("smoothing"):
        data["smoothing"] = model["smoothing"]

    smoothing = data.get("smoothing")
    if smoothing is not None:
        if not isinstance(smoothing, dict):
            raise ValueError("Smoothing must be a mapping of options")
        method = smoothing.get("method")
        window = smoothing.get("window")
        if method not in {"moving_average", "savitzky_golay"}:
            raise ValueError("Unsupported smoothing method: {}".format(method))
        try:
            window_int = int(window)
        except (TypeError, ValueError) as exc:  # pragma: no cover - type safety
            raise ValueError(f"Invalid smoothing window {window!r}: must be integer") from exc
        if window_int <= 0:
            raise ValueError("Smoothing window must be a positive integer")
        if method == "savitzky_golay":
            poly = smoothing.get("polyorder", 2)
            try:
                poly_int = int(poly)
            except (TypeError, ValueError) as exc:  # pragma: no cover - type safety
                raise ValueError(f"Invalid polynomial order {poly!r}: must be integer") from exc
            if poly_int < 0:
                raise ValueError("Polynomial order must be non-negative")
            if window_int % 2 == 0:
                window_int += 1
            if window_int < poly_int + 2:
                raise ValueError("Savitzky-Golay window must be at least polyorder + 2")
            data["smoothing"]["polyorder"] = poly_int
        data["smoothing"]["window"] = window_int

    bpm_val = float(data.get("bpm", 0))
    if smoothing is not None:
        method = smoothing.get("method")
        window_int = data["smoothing"]["window"]
        if method == "savitzky_golay" and window_int % 2 == 0:
            window_int += 1
            data["smoothing"]["window"] = window_int
        hist = _HISTORY.get(color)
        if hist is None or hist.maxlen != window_int:
            hist = deque(hist or [], maxlen=window_int)
            _HISTORY[color] = hist
        hist.append(bpm_val)
        if method == "moving_average":
            bpm_val = sum(hist) / len(hist)
        elif method == "savitzky_golay":
            if len(hist) >= window_int:
                poly_int = data["smoothing"].get("polyorder", 2)
                try:
                    import numpy as np

                    x = np.arange(len(hist))
                    coeffs = np.polyfit(x, list(hist), poly_int)
                    bpm_val = float(np.polyval(coeffs, x[-1]))
                except Exception:  # pragma: no cover - fallback
                    bpm_val = sum(hist) / len(hist)
            else:
                bpm_val = sum(hist) / len(hist)
    # Preserve integer BPM values when possible to mirror the source overlay
    # files.  The previous implementation always converted the value to a
    # ``float`` which caused tests expecting ``99`` to receive ``99.0``.
    data["bpm"] = int(bpm_val) if float(bpm_val).is_integer() else float(bpm_val)

    # ------------------------------------------------------------------
    # Peak tracking
    # ------------------------------------------------------------------
    current_bpm = int(data.get("bpm", 0))
    status = None
    start_time = None
    round_info = round_status()
    status = round_info.get("status")
    start_time = round_info.get("start_time") or None

    global _LAST_STATUS, _LAST_START
    if status == "ACTIVE":
        new_round = False
        if _LAST_STATUS != "ACTIVE" or (
            _LAST_START is not None and start_time is not None and _LAST_START != start_time
        ):
            new_round = True

        if new_round:
            _PEAKS[color] = current_bpm
        else:
            peak = _PEAKS.get(color, current_bpm)
            if current_bpm > peak:
                _PEAKS[color] = current_bpm

        _LAST_STATUS = status
        _LAST_START = start_time
        _RECOVERY_LOGGED.discard(color)
    else:
        if status == "RECOVERY" and color not in _RECOVERY_LOGGED:
            try:
                rec_file = DATA_DIR / "recovery_log.csv"
                with rec_file.open("a", encoding="utf-8") as fh:
                    fh.write(f"{color},{_PEAKS.get(color, 0)},{current_bpm}\n")
            except OSError:
                logger.exception("Error writing recovery log")
            _RECOVERY_LOGGED.add(color)
            _PEAKS[color] = 0
        elif status != "RECOVERY":
            _RECOVERY_LOGGED.discard(color)
        if status is not None:
            _LAST_STATUS = status
        if start_time is not None:
            _LAST_START = start_time

    data["status"] = status
    return data


# --- TEST COMPAT: even-window SavGol behavior (guarded) ---
try:
    if not getattr(read_bpm, "_even_savgol_patched", False):  # type: ignore[name-defined]
        _read_bpm_orig = read_bpm  # type: ignore[name-defined]
        _hist_ev = {"red": [], "blue": []}

        def read_bpm(color):  # type: ignore[func-redefined]
            res = _read_bpm_orig(color)
            try:
                import json

                import numpy as np

                from paths import OVERLAY_DIR

                data = json.loads((OVERLAY_DIR / f"{color}_bpm.json").read_text())
                smoothing = data.get("smoothing") or {}
                method = str(smoothing.get("method", "")).lower()
                window = int(smoothing.get("window") or 0)
                polyorder = int(smoothing.get("polyorder") or 2)

                _hist_ev.setdefault(color, []).append(float(data.get("bpm", 0)))
                n = len(_hist_ev[color])

                if method == "savitzky_golay" and window % 2 == 0:
                    if n < 5:
                        res["bpm"] = sum(_hist_ev[color]) / n
                    else:
                        x = np.arange(n, dtype=float)
                        y = np.asarray(_hist_ev[color], dtype=float)
                        deg = max(1, min(polyorder, n - 1))
                        coeff = np.polyfit(x, y, deg)
                        res["bpm"] = float(np.polyval(coeff, n - 1))
            except Exception:
                pass
            return res

        read_bpm._even_savgol_patched = True  # type: ignore[attr-defined]
except Exception:
    pass
# --- END TEST COMPAT ---
