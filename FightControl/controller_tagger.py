from __future__ import annotations

import csv
import importlib
import json
from datetime import datetime
from pathlib import Path

try:  # optional locking support
    import fcntl  # type: ignore[attr-defined]
except Exception:  # pragma: no cover - platform dependent
    fcntl = None  # type: ignore
try:  # fallback for non-posix systems
    import portalocker  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    portalocker = None  # type: ignore

import fight_state
import paths
from FightControl import fighter_paths
from FightControl.fight_utils import safe_filename
from utils_checks import next_bout_number

_STATE_CACHE: tuple[dict, str, str] | None = None
_INITIALISED = False


def _now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _load_state() -> tuple[dict, str, str]:
    """Load and cache fight state information."""

    global _STATE_CACHE, _INITIALISED
    if not _INITIALISED:
        importlib.reload(fight_state)
        paths.refresh_paths()
        fighter_paths.refresh_base_dir()
        _STATE_CACHE = fight_state.load_fight_state()
        fight, date, _ = _STATE_CACHE
        next_bout_number(date, fight.get("red_fighter", ""), fight.get("blue_fighter", ""))
        _INITIALISED = True
    assert _STATE_CACHE is not None  # for type checkers
    return _STATE_CACHE


def _ensure_logs(date: str, red: str, blue: str, round_id: str) -> Path:
    bout = f"{date}_{safe_filename(red).upper()}_vs_{safe_filename(blue).upper()}_BOUT0"
    path = Path(paths.BASE_DIR) / "FightControl" / "logs" / date / bout / round_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def log_tag(
    fighter: str,
    tag: str | None = None,
    note: str | None = None,
    type: str | None = None,
) -> None:
    fight, date, round_id = _load_state()
    red = fight.get("red_fighter", "Red Fighter")
    blue = fight.get("blue_fighter", "Blue Fighter")
    log_dir = _ensure_logs(date, red, blue, round_id)

    # tags.csv
    tag_csv = log_dir / "tags.csv"
    tag_csv.parent.mkdir(parents=True, exist_ok=True)
    new_file = not tag_csv.exists()
    with tag_csv.open("a", newline="", encoding="utf-8") as f:
        try:  # avoid concurrent writes where possible
            if fcntl is not None:
                fcntl.flock(f, fcntl.LOCK_EX)
            elif portalocker is not None:
                portalocker.lock(f, portalocker.LOCK_EX)
        except Exception:
            pass
        w = csv.writer(f)
        if new_file:
            w.writerow(["timestamp", "fighter", "tag"])
        w.writerow([_now_str(), fighter, tag or note or ""])
        f.flush()
        try:
            if fcntl is not None:
                fcntl.flock(f, fcntl.LOCK_UN)
            elif portalocker is not None:
                portalocker.unlock(f)
        except Exception:
            pass

    # events.csv
    events_csv = log_dir.parent / "events.csv"
    events_new = not events_csv.exists()
    with events_csv.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if events_new:
            w.writerow(["time", "round", "fighter", "type", "value"])
        w.writerow([_now_str(), round_id, fighter, type or "coach_note", tag or note or ""])

    # JSON tag log
    tag_json = log_dir.parent.parent / "tag_log.json"
    try:
        items = json.loads(tag_json.read_text(encoding="utf-8"))
        if not isinstance(items, list):
            items = []
    except Exception:
        items = []
    items.append({"time": _now_str(), "fighter": fighter, "tag": tag or note or ""})
    tag_json.write_text(json.dumps(items), encoding="utf-8")


__all__ = ["log_tag"]
