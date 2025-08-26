"""Round timing utilities.

This module persists round state to ``FightControl/data/round_status.json`` for
consumption by other parts of the system.  The ``start_time`` field is only
written once a round or rest period actually begins.  While the timer is armed
and awaiting the start command, ``round_status.json`` deliberately omits
``start_time`` to represent an unstarted state.
"""

import asyncio
import copy
import json
import logging
import os
import threading
import time
from datetime import datetime
from typing import Optional

from fight_state import fighter_session_dir, load_fight_state
from FightControl.fight_utils import safe_filename
from FightControl.play_sound import play_audio
from FightControl.round_manager import round_status
from paths import BASE_DIR
from session_summary import build_session_summary
from utils.obs_ws import ObsWs
from utils_bpm import read_bpm
from utils_checks import next_bout_number

logger = logging.getLogger(__name__)

try:
    from cyclone_modules.ObsControl.obs_control import refresh_obs_overlay
except ImportError:
    logger.warning("OBS module not found; OBS features disabled")

    def refresh_obs_overlay(*_args, **_kwargs) -> None:  # type: ignore
        """Fallback no-op when OBS integration is unavailable."""


DATA_DIR = BASE_DIR / "FightControl" / "data"
EVENTS_FILE = DATA_DIR / "round_events.csv"

logging.basicConfig(level=logging.INFO)


class ObsClient(ObsWs):
    """Thin wrapper adding convenient recording helpers."""

    async def start_record(self):
        return await self.ws_request("StartRecord")

    async def stop_record(self):
        return await self.ws_request("StopRecord")

    async def pause_record(self):
        return await self.ws_request("PauseRecord")

    async def resume_record(self):
        return await self.ws_request("ResumeRecord")


obs = ObsClient(timeout=0.1)


def _format_timer(seconds: float) -> str:
    mins = int(seconds) // 60
    secs = int(seconds) % 60
    return f"{mins:02}:{secs:02}"


def _read_hr(color: str) -> str:
    try:
        return str(int(read_bpm(color).get("bpm", 0)))
    except Exception:
        return "0"


def push_obs_text_sources() -> None:
    """Push timer/HR/round info to OBS text sources.

    Updates are executed concurrently over the persistent WebSocket
    connection.  Any errors are logged but otherwise ignored so the timer
    thread can continue without interruption.
    """

    status = round_status()

    timer_val = _format_timer(status.get("remaining_time", remaining_secs))
    badge = str(status.get("round", 1))
    red_hr = _read_hr("red")
    blue_hr = _read_hr("blue")

    async def _update():
        await asyncio.gather(
            obs.set_text_source("Timer", timer_val),
            obs.set_text_source("RedHR", red_hr),
            obs.set_text_source("BlueHR", blue_hr),
            obs.set_text_source("RoundBadge", badge),
            return_exceptions=True,
        )

    try:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(_update())
        else:
            loop.create_task(_update())
    except Exception:
        logger.exception("OBS text update failed")


# Shared state used by the round timer thread. ``pause_event`` is set when the
# timer is running and cleared when paused. ``remaining_secs`` tracks the time
# left in the current round so it can be persisted across pauses. ``elapsed_secs``
# records how long the round has already run. ``_start_time`` and ``_end_time``
# store the monotonic timestamps delimiting the active window and
# ``_timer_thread`` holds the background thread instance.
pause_event = threading.Event()
pause_event.set()
remaining_secs: float = 0
elapsed_secs: float = 0
_start_time: Optional[float] = None
_end_time: Optional[float] = None
_timer_thread: Optional[threading.Thread] = None


def save_round_logs(current_round: int) -> None:
    """Flush round logs for both fighters and ensure they're written to disk."""
    fight, date, round_id = load_fight_state()
    try:
        round_num = int(round_id.split("_")[-1])
    except (ValueError, AttributeError):
        round_num = current_round

    for color in ("red", "blue"):
        try:
            session_dir = fighter_session_dir(color, fight=fight, date=date, round_id=round_id)
            file_path = session_dir / "hr_log.csv"
            with open(file_path, "a", encoding="utf-8") as f:
                f.flush()
                os.fsync(f.fileno())
        except Exception:
            logger.exception("failed to save %s logs", color)

    print(f"[SAVED] hr_log.csv for round {round_num}")


def create_round_folder_for_fighter(color: str, new_round: int) -> None:
    session_dir = fighter_session_dir(color, round_id=f"round_{new_round}")
    (session_dir / "hr_log.csv").write_text("")


def _merge_bout_metadata(session_dir, updates: dict) -> None:
    """Merge ``updates`` into ``bout.json`` within ``session_dir``.

    Existing metadata is preserved and only the supplied keys are updated.
    ``session_dir`` should point to a bout directory as returned by
    :func:`FightControl.fighter_paths.bout_dir`.
    """

    def _deep_merge(base: dict, incoming: dict) -> dict:
        for key, value in incoming.items():
            if isinstance(value, dict) and isinstance(base.get(key), dict):
                base[key] = _deep_merge(base[key], value)
            else:
                base[key] = copy.deepcopy(value)
        return base

    path = session_dir / "bout.json"
    try:
        current = json.loads(path.read_text()) if path.exists() else {}
        if not isinstance(current, dict):
            current = {}
    except Exception:
        current = {}
    current = _deep_merge(current, updates)
    path.write_text(json.dumps(current, indent=2))


def init_bout_metadata(fight: dict, data: dict) -> str:
    """Create bout-level metadata files for both fighters.

    The returned ``bout_id`` matches the directory name used by
    :func:`FightControl.fighter_paths.bout_dir`.  Metadata includes the
    fighters, fight date, round configuration and any detected maximum heart
    rates.  The JSON is written to ``bout.json`` for *both* fighters so either
    corner can reference the same bout information.
    """

    date = fight.get("fight_date", datetime.now().strftime("%Y-%m-%d"))
    red = fight.get("red_fighter") or fight.get("red") or "Red"
    blue = fight.get("blue_fighter") or fight.get("blue") or "Blue"
    bout_num = next_bout_number(date, red, blue)
    safe_red = safe_filename(red).upper()
    safe_blue = safe_filename(blue).upper()
    bout_id = f"{date}_{safe_red}_vs_{safe_blue}_BOUT{bout_num}"

    round_type = fight.get("round_type")
    round_duration = data.get("duration")
    rest_duration = data.get("rest")

    max_hr = {}
    try:  # Retrieve per-fighter max HR from zone models if available
        from cyclone_modules.HRLogger import hr_logger

        red_model = hr_logger.load_zone_model(safe_filename(red))
        blue_model = hr_logger.load_zone_model(safe_filename(blue))
        max_hr = {
            "red": red_model.get("max_hr"),
            "blue": blue_model.get("max_hr"),
        }
    except Exception:
        pass

    metadata = {
        "bout_id": bout_id,
        "red_fighter": red,
        "blue_fighter": blue,
        "fight_date": date,
        "round_type": round_type,
        "round_duration": round_duration,
        "rest_duration": rest_duration,
        "max_hr": max_hr,
    }

    from FightControl.fighter_paths import bout_dir

    for fighter in (red, blue):
        session_dir = bout_dir(fighter, date, bout_id)
        _merge_bout_metadata(session_dir, metadata)

    return bout_id


def update_bout_metadata(updates: dict) -> None:
    """Merge ``updates`` into the active bout's metadata files."""

    fight, date, _ = load_fight_state()
    red = fight.get("red_fighter") or fight.get("red") or "Red"
    blue = fight.get("blue_fighter") or fight.get("blue") or "Blue"
    bout_num = next_bout_number(date, red, blue) - 1
    if bout_num <= 0:
        bout_num = 1
    safe_red = safe_filename(red).upper()
    safe_blue = safe_filename(blue).upper()
    bout_id = updates.get("bout_id") or f"{date}_{safe_red}_vs_{safe_blue}_BOUT{bout_num}"

    from FightControl.fighter_paths import bout_dir

    for fighter in (red, blue):
        session_dir = bout_dir(fighter, date, bout_id)
        _merge_bout_metadata(session_dir, updates)


def arm_round_status(dur, rest, total_rounds):
    """Initialise ``round_status.json`` for a new fight.

    The resulting file contains the round configuration and a ``status`` of
    ``WAITING`` but deliberately excludes ``start_time`` until the round is
    actually started via the timer API.
    """

    info = {"round": 1, "duration": dur, "rest": rest, "total_rounds": total_rounds, "status": "WAITING"}
    path = DATA_DIR / "round_status.json"
    # Ensure the data directory exists before writing to avoid FileNotFoundError
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(info, indent=2))
    # Ensure the current round tracker is initialised at fight start.
    (DATA_DIR / "current_round.txt").write_text("round_1")
    try:
        from routes import api_routes

        alt = getattr(api_routes, "DATA_DIR", DATA_DIR) / "round_status.json"
        if alt != path:
            alt.write_text(json.dumps(info, indent=2))
    except Exception:
        pass
    logger.info("round_status armed: %s", info)
    refresh_obs_overlay()
    push_obs_text_sources()


def start_round_timer(dur, rest, on_complete=None, fire_bell: bool = True):
    """Start or resume the background round timer.

    ``dur`` is the number of seconds remaining in the active round.  The
    function relies on the module-level ``pause_event`` and ``remaining_secs``
    variables to coordinate pausing and resuming. When called while a timer
    thread is already running the shared state is updated so the existing
    thread can resume without spawning a new one.
    """

    # ``start_round_timer`` is sometimes invoked directly (bypassing the API)
    # when the timer transitions from the initial ``WAITING`` state to the
    # first active round.  In this scenario ``round_status.json`` still reflects
    # ``WAITING`` which prevents other components – notably
    # :func:`FightControl.round_manager.log_bpm` – from recording heart rate
    # data.  Detect this cold-start and persist the same state changes normally
    # performed by the API so the rest of the system observes an ``ACTIVE``
    # round immediately.
    path = DATA_DIR / "round_status.json"
    data = round_status()
    start_ts_str = data.get("start_time")
    if data.get("status") == "WAITING":
        data["status"] = "ACTIVE"
        if not start_ts_str:
            start_ts_str = datetime.now().isoformat()
            data["start_time"] = start_ts_str
        path.write_text(json.dumps(data, indent=2))
        refresh_obs_overlay()
        push_obs_text_sources()
        try:
            create_round_folder_for_fighter("red", data.get("round", 1))
        except Exception:
            logger.exception("failed to create red fighter session dir")
        try:
            create_round_folder_for_fighter("blue", data.get("round", 1))
        except Exception:
            logger.exception("failed to create blue fighter session dir")
        try:
            fight, _, _ = load_fight_state()
            init_bout_metadata(fight, data)
        except Exception:
            logger.exception("failed to write bout metadata")
        try:  # Ensure real round_manager is loaded for subsequent imports
            import importlib

            import FightControl.round_manager as rm  # type: ignore

            importlib.reload(rm)
        except Exception:
            pass

        try:
            asyncio.run(obs.start_record())
        except Exception:
            logger.exception("OBS start recording failed")

    def default_on_complete():
        path = DATA_DIR / "round_status.json"
        data = round_status()
        current_round = data.get("round", 1)
        total = data.get("total_rounds", 1)

        if current_round >= total:
            data["status"] = "ENDED"
            data["start_time"] = datetime.now().isoformat()
            path.write_text(json.dumps(data, indent=2))
            save_round_logs(current_round)
            try:
                from round_summary import generate_round_summaries

                fight, date, _ = load_fight_state()
                fight_meta = {**fight, "fight_date": date}
                generate_round_summaries(fight_meta)

                red = fight_meta.get("red_fighter") or fight_meta.get("red") or "Red"
                blue = fight_meta.get("blue_fighter") or fight_meta.get("blue") or "Blue"
                bout_num = next_bout_number(date, red, blue) - 1
                safe_red = safe_filename(red).upper()
                safe_blue = safe_filename(blue).upper()
                bout_name = f"{date}_{safe_red}_vs_{safe_blue}_BOUT{bout_num}"
                from FightControl.fighter_paths import bout_dir

                for fighter in (red, blue):
                    session_dir = bout_dir(fighter, date, bout_name)
                    build_session_summary(session_dir)
            except Exception:
                logger.exception("failed to build summaries")
            refresh_obs_overlay()
            push_obs_text_sources()
            return

        data["status"] = "RESTING"
        data["start_time"] = datetime.now().isoformat()
        data["remaining_time"] = int(rest)
        path.write_text(json.dumps(data, indent=2))
        refresh_obs_overlay()
        push_obs_text_sources()

        rest_end = time.monotonic() + rest
        while True:
            remaining = int(rest_end - time.monotonic())
            current = round_status()
            if current.get("status") != "RESTING":
                return
            current["remaining_time"] = max(0, remaining)
            path.write_text(json.dumps(current, indent=2))
            push_obs_text_sources()
            if remaining <= 0:
                break
            time.sleep(1)

        def start_next_round() -> None:
            new_round = current_round + 1
            data["round"] = new_round
            # Persist the new round identifier for other components.
            (DATA_DIR / "current_round.txt").write_text(f"round_{new_round}")
            data["status"] = "ACTIVE"
            data.pop("remaining_time", None)
            try:
                create_round_folder_for_fighter("red", new_round)
            except Exception:
                logger.exception("failed to create red fighter session dir")
            try:
                create_round_folder_for_fighter("blue", new_round)
            except Exception:
                logger.exception("failed to create blue fighter session dir")
            try:
                asyncio.run(obs.start_record())
            except Exception:
                logger.exception("OBS start recording failed")
            data["start_time"] = datetime.now().isoformat()
            path.write_text(json.dumps(data, indent=2))
            refresh_obs_overlay()
            push_obs_text_sources()
            start_round_timer(dur, rest)

        if round_status().get("status") == "RESTING":
            threading.Thread(target=start_next_round, daemon=True).start()

    global remaining_secs, elapsed_secs, _start_time, _end_time, _timer_thread

    remaining_secs = dur
    elapsed_secs = 0
    # Ensure the timer is in a running state whenever (re)started.
    pause_event.set()

    # If a timer thread is already active (e.g. resuming after a pause) simply
    # update ``_start_time``/``_end_time`` and release the pause without spawning
    # a new thread.
    if _timer_thread and _timer_thread.is_alive():
        _start_time = time.monotonic()
        _end_time = _start_time + remaining_secs
        return

    _start_time = time.monotonic()
    _end_time = _start_time + remaining_secs
    if fire_bell:
        play_audio("bell_start.mp3")
    push_obs_text_sources()

    def run():
        global remaining_secs, elapsed_secs, _start_time, _end_time, _timer_thread
        clapper_fired = False
        while True:
            # Wait here while the timer is paused.
            pause_event.wait()
            now = time.monotonic()
            remaining_secs = _end_time - now
            elapsed_secs = now - _start_time
            if remaining_secs <= 0:
                break
            if not clapper_fired and remaining_secs <= 10:
                play_audio("clapper.mp3")
                clapper_fired = True

            push_obs_text_sources()
            time.sleep(min(1, max(0, remaining_secs)))

        remaining_secs = 0
        push_obs_text_sources()
        try:
            asyncio.run(obs.stop_record())
        except Exception:
            logger.exception("OBS stop recording failed")
        play_audio("bell_end.mp3")

        if on_complete:
            on_complete()
        else:
            default_on_complete()

        _timer_thread = None
        _start_time = None
        _end_time = None
        elapsed_secs = 0

    _timer_thread = threading.Thread(target=run, daemon=True)
    _timer_thread.start()


def _log_event(event: str) -> None:
    """Append a timestamped event to ``EVENTS_FILE``.

    The parent directory is created if missing and the file is created
    atomically on first use to avoid race conditions during live sessions.
    """
    EVENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    line = f"{datetime.now().isoformat()},{event}\n"
    try:
        with EVENTS_FILE.open("a", encoding="utf-8") as f:
            f.write(line)
    except FileNotFoundError:
        tmp = EVENTS_FILE.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            f.write("timestamp,event\n")
            f.write(line)
        os.replace(tmp, EVENTS_FILE)


def pause_round() -> None:
    """Record that the round has been paused and persist remaining time."""

    global remaining_secs, elapsed_secs, _start_time, _end_time
    _log_event("pause")
    try:
        asyncio.run(obs.pause_record())
    except Exception:
        logger.exception("OBS pause recording failed")
    if _end_time is not None:
        now = time.monotonic()
        remaining_secs = max(0, _end_time - now)
        if _start_time is not None:
            elapsed_secs = now - _start_time
    pause_event.clear()
    _start_time = None
    _end_time = None

    path = DATA_DIR / "round_status.json"
    data = round_status()
    data["status"] = "PAUSED"
    data["remaining_time"] = int(remaining_secs)
    path.write_text(json.dumps(data, indent=2))
    push_obs_text_sources()


def resume_round() -> None:
    """Resume a paused round using the stored remaining time."""

    global remaining_secs, elapsed_secs, _start_time, _end_time
    _log_event("resume")
    try:
        asyncio.run(obs.resume_record())
    except Exception:
        logger.exception("OBS resume recording failed")

    path = DATA_DIR / "round_status.json"
    data = round_status()
    remaining_secs = int(data.get("remaining_time", data.get("duration", 0)))
    dur = int(data.get("duration", remaining_secs))
    data["status"] = "ACTIVE"
    data["start_time"] = datetime.now().isoformat()
    data["remaining_time"] = int(remaining_secs)
    path.write_text(json.dumps(data, indent=2))
    push_obs_text_sources()

    pause_event.set()
    if _timer_thread and _timer_thread.is_alive():
        elapsed_secs = dur - remaining_secs
        _start_time = time.monotonic() - elapsed_secs
        _end_time = _start_time + remaining_secs
        return

    # If no timer thread is running (e.g. after application restart),
    # start a new one with the remaining time without firing the start bell.
    start_round_timer(remaining_secs, data.get("rest", 0), fire_bell=False)
