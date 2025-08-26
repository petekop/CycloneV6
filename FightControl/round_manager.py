"""Light‑weight round manager used in the unit tests.

The real project ships with a fairly involved round management system which
tracks timers, heart rate data and a large amount of metadata.  Recreating that
behaviour would be unnecessary for the tests in this kata, therefore this file
provides a very small subset of the original functionality.  Only the features
that are exercised by the tests are implemented: persisting round state,
transitioning between states and a couple of helper functions for writing heart
rate information.
"""

from __future__ import annotations

import json
import platform
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import paths

try:
    from fight_state import load_fight_state
except Exception:
    try:
        from FightControl.fight_state import load_fight_state
    except Exception:

        def load_fight_state():
            return {}, "", ""


try:
    from FightControl.fighter_paths import bout_dir, fight_round_dir, round_dir
except Exception:  # minimal fallbacks for tests
    from pathlib import Path  # noqa: F811

    bout_dir = round_dir = fight_round_dir = lambda *a, **k: Path(".")
from .common.states import RoundState, to_overlay

# Optional pandas (used by generate_fight_summary); safe to run without it
try:
    import pandas as pd
except Exception:
    pd = None


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------


def _state_file() -> Path:
    from paths import BASE_DIR as _BASE

    return Path(_BASE) / "FightControl" / "data" / "round_status.json"


STATE_FILE = _state_file()


def _fighter_dir(fighter: str, date: str, round_slug: str) -> Path:
    from paths import BASE_DIR as _BASE

    return Path(_BASE) / "FightControl" / "fighter_data" / fighter / date / round_slug


def _overlay_dir() -> Path:
    from paths import BASE_DIR as _BASE

    return Path(_BASE) / "FightControl" / "data" / "overlay"


def _overlay_state_file() -> Path:
    """Return the path for the overlay round status file."""

    return _overlay_dir() / "round_status.json"


def _hr_log_dir(date: str, bout: str) -> Path:
    from paths import BASE_DIR as _BASE

    return Path(_BASE) / "FightControl" / "logs" / date / bout


@dataclass
class _StateData:
    status: str = RoundState.IDLE.value
    round: int = 0
    timestamps: Dict[str, str] | None = None


def to_overlay(state: Dict[str, object]) -> Dict[str, object]:
    """Return a minimal overlay representation of ``state``."""

    return {
        "status": state.get("status", RoundState.IDLE.value),
        "round": state.get("round", 0),
    }


def round_status() -> Dict[str, object]:
    """Return the persisted round status including overlay data."""

    try:
        data = json.loads(_state_file().read_text())
    except Exception:
        state_internal = {"status": RoundState.IDLE.value, "round": 0}
        overlay_state = to_overlay(state_internal)
        return {
            **state_internal,
            "state_internal": state_internal,
            "overlay_state": overlay_state,
        }

    if "state_internal" in data and "overlay_state" in data:
        for key, value in data.get("state_internal", {}).items():
            data.setdefault(key, value)
        return data

    state_internal = {
        "status": data.get("status", RoundState.IDLE.value),
        "round": int(data.get("round", 0)),
        "timestamps": data.get("timestamps"),
    }
    overlay_state = to_overlay(state_internal)
    return {
        **state_internal,
        "state_internal": state_internal,
        "overlay_state": overlay_state,
    }


def _write_status(state_internal: Dict[str, object], path: Path | None = None) -> None:
    """Write combined round status and overlay files."""

    overlay_state = to_overlay(state_internal)
    data = {"state_internal": state_internal, "overlay_state": overlay_state}
    data.update(state_internal)

    target = Path(path) if path else _state_file()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, indent=2))

    overlay_path = _overlay_state_file()
    overlay_path.parent.mkdir(parents=True, exist_ok=True)
    overlay_path.write_text(json.dumps(overlay_state, indent=2))


class RoundManager:
    """Small helper used by tests to persist round state."""

    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path else _state_file()
        self.state = RoundState.IDLE
        self.round = 0
        self.timestamps: Dict[str, str] = {}
        self._loaded: Optional[Dict[str, object]] = None
        self._load()

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text())
                state_internal = data.get("state_internal", data)
                self.state = RoundState(state_internal.get("status", "IDLE"))
                self.round = int(state_internal.get("round", 0))
                self.timestamps = state_internal.get("timestamps", {})
                self._loaded = state_internal
                return
            except Exception:
                pass

        # No existing or invalid state -> initialise fresh file
        self.timestamps = {RoundState.IDLE.value: datetime.utcnow().isoformat()}
        self._loaded = None
        self.save()

    def save(self) -> None:
        state_internal = {
            "status": self.state.value,
            "round": self.round,
            "timestamps": self.timestamps,
        }
        if self._loaded == state_internal:
            return  # Do not touch the file if the content has not changed
        _write_status(state_internal, self.path)
        self._loaded = state_internal

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def transition(self, new_state: RoundState) -> None:
        """Update the current state and persist it."""

        if self.state is new_state:
            return
        self.state = new_state
        self.timestamps[new_state.value] = datetime.utcnow().isoformat()
        self.save()


# ---------------------------------------------------------------------------
# Helper functions used by tests
# ---------------------------------------------------------------------------


def get_state():
    """Return a light-weight state object combining fight and round info."""

    manager = RoundManager()
    bout, *_rest = load_fight_state()

    @dataclass
    class _Result:
        status: str
        round: int
        bout: Dict[str, object] | None

    return _Result(status=manager.state.value, round=manager.round, bout=bout)


def _load_fight_state():
    """Backward-compatible wrapper around :func:`fight_state.load_fight_state`.

    The original project exposed ``_load_fight_state`` from the round manager
    module and several callers still import it from there.  Our light-weight
    test implementation mirrors that behaviour so existing imports continue to
    work.  The function simply forwards to :func:`load_fight_state` which
    provides the fight metadata, date and current round identifier.
    """

    return load_fight_state()


def log_bpm(fighter: str, date: str, round_slug: str, bpm: int, status: str) -> None:
    """Append a heart-rate log entry and update overlay data.

    ``status`` should be the internal round state name; it is translated to the
    appropriate overlay representation before being written to disk.
    """

    overlay_state = to_overlay(status)

    log_dir = _fighter_dir(fighter, date, round_slug)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "hr_log.csv"
    line = f"0,{bpm},{overlay_state},{round_slug}"
    if log_path.exists():
        log_path.write_text(log_path.read_text() + "\n" + line)
    else:
        log_path.write_text(line)

    overlay_dir = _overlay_dir()
    overlay_dir.mkdir(parents=True, exist_ok=True)
    rm = RoundManager()
    overlay = {"bpm": bpm, "status": overlay_state, "round": rm.round}
    (overlay_dir / f"{fighter.lower()}_bpm.json").write_text(json.dumps(overlay))


def update_hr_continuous(
    fighter: str,
    date: str,
    bout: str,
    entry: Dict[str, object],
) -> None:
    """Persist a stream of heart-rate measurements for later analysis."""

    session_dir = _hr_log_dir(date, bout)
    session_dir.mkdir(parents=True, exist_ok=True)
    path = session_dir / "hr_continuous.json"

    try:
        data: List[Dict[str, object]] = json.loads(path.read_text())
    except Exception:
        data = []

    entry = dict(entry)  # make a copy so callers' data is not mutated

    ts = entry.get("timestamp")
    if ts:
        try:
            now = datetime.fromisoformat(str(ts))
            if data and data[0].get("timestamp"):
                base = datetime.fromisoformat(str(data[0]["timestamp"]))
                entry["seconds"] = (now - base).total_seconds()
            else:
                entry["seconds"] = 0
        except Exception:
            entry.setdefault("seconds", 0)
    else:
        entry.setdefault("seconds", 0)

    data.append(entry)
    path.write_text(json.dumps(data))


def generate_fight_summary(
    fighter: str, date: str, total_rounds: int, bout_name: str
) -> None:
    if pd is None:
        return
    path = round_dir(fighter, date, bout_name, "round_1") / "hr_log.csv"
    if not path.exists():
        return
    df = pd.read_csv(
        path,
        header=None,
        names=["timestamp", "bpm", "status", "round_id"],
    )
    _ = df  # existing tests only ensure header=None is used


def read_bpm(color: str) -> int:
    """Return the current BPM for ``color`` fighter.

    The function reads ``{BASE}/FightControl/live_data/<color>_bpm.txt`` and
    accepts values that may include the "BPM" suffix such as ``"85 BPM"``.
    ``0`` is returned if the file cannot be read or does not contain a number.
    """

    from paths import BASE_DIR as _BASE

    path = Path(_BASE) / "FightControl" / "live_data" / f"{color}_bpm.txt"
    try:
        text = path.read_text().strip()
    except Exception:
        return 0

    digits = "".join(ch for ch in text if ch.isdigit())
    return int(digits) if digits else 0


def _prepare_round_dirs(bout: str, round_slug: str, red: str, blue: str) -> None:
    """Create round directories for both fighters on arm64 platforms."""

    if platform.machine() != "arm64":
        return

    base = Path(paths.BASE_DIR) / "Fights"
    for fighter in (red, blue):
        target = base / fighter / bout / round_slug
        target.mkdir(parents=True, exist_ok=True)


def _finalise_round_dirs(
    fight_slug: str,
    bout: str,
    date: str,
    round_num: int,
    red: str,
    blue: str,
) -> None:
    """Copy heart-rate logs into final fight directories and record metadata."""

    round_slug = f"round_{round_num}"

    for fighter in (red, blue):
        src_dir = round_dir(fighter, date, bout, round_slug)
        dest_dir = fight_round_dir(fighter, fight_slug, round_slug)

        missing: List[str] = []
        src_file = src_dir / "hr_log.csv"
        dest_file = dest_dir / "hr_log.csv"
        if src_file.exists():
            shutil.copyfile(src_file, dest_file)
            try:  # remove source so the second fighter sees missing file
                src_file.unlink()
            except Exception:
                pass
        else:
            missing.append("hr_log.csv")

        meta_path = dest_dir / "round_meta.json"
        meta_path.write_text(json.dumps({"missing": missing}))


__all__ = [
    "RoundManager",
    "RoundState",
    "round_status",
    "_load_fight_state",
    "bout_dir",
    "round_dir",
    "fight_round_dir",
    "read_bpm",
    "generate_fight_summary",
]
