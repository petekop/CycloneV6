from __future__ import annotations

import asyncio
import logging
import sys
from typing import Any, Dict, Optional

from .daemon import HRDaemon, BASE_DIR
from .backoff import retry_async

# Ensure cyclone_modules is importable (for HRLogger)
mods_dir = BASE_DIR / "cyclone_modules"
if mods_dir.exists():
    sys.path.insert(0, str(mods_dir))
try:
    from cyclone_modules.HRLogger.hr_logger import load_zone_model  # type: ignore
except Exception:
    try:
        from HRLogger.hr_logger import load_zone_model  # type: ignore
    except Exception:
        def load_zone_model(_: Optional[str]) -> Dict[str, Any]:
            return {}

LOGGER = logging.getLogger("hr_blue")
if not LOGGER.handlers:
    logging.basicConfig(level=logging.INFO)

def _zone_calc_factory(model: Dict[str, Any], daemon: HRDaemon):
    rest = float(model.get("rest_hr", 60))
    maxh = float(model.get("max_hr", 190))
    smoothing = model.get("smoothing") or {}
    method = str(smoothing.get("method", "ewma")).lower()
    window = int(smoothing.get("window", 5))

    def _effort(bpm_val: float) -> float:
        if maxh <= rest:
            return 0.0
        return max(0.0, min(100.0, ((bpm_val - rest) / (maxh - rest)) * 100.0))

    def _zone_from_effort(e: float) -> str:
        if e < 50:  return "Blue"
        if e < 60:  return "Green"
        if e < 70:  return "Yellow"
        if e < 90:  return "Orange"
        return "Red"

    def calc(bpm: float):
        if method == "ewma":
            alpha = 2.0 / (window + 1.0)
            daemon.EMA_VALUE = bpm if daemon.EMA_VALUE is None else alpha * bpm + (1 - alpha) * daemon.EMA_VALUE
            smoothed = float(daemon.EMA_VALUE)
        elif method == "moving_average":
            buf = daemon.SMOOTH_BUFFER
            buf.append(int(bpm))
            if len(buf) > window:
                buf.pop(0)
            smoothed = sum(buf) / len(buf)
        else:
            smoothed = float(bpm)

        e = _effort(smoothed)
        return _zone_from_effort(e), int(e)
    return calc

async def _run_daemon():
    d = HRDaemon("blue")
    try:
        from FightControl.round_manager import _load_fight_state  # type: ignore
        fs, _date, _rid = _load_fight_state()
        d.fighter_name = fs.get("blue_fighter") or ""
    except Exception:
        d.fighter_name = ""
    model = {}
    try:
        model = load_zone_model(d.fighter_name or None) or {}
    except Exception:
        model = {}
    d.calc_zone = _zone_calc_factory(model, d)
    try:
        await retry_async(d.run, status_update=d.write_status, logger=LOGGER)
    except asyncio.CancelledError:
        return

def main():
    try:
        asyncio.run(_run_daemon())
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
