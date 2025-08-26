"""System checks (mediaMTX, process, OBS health)."""

import csv
import json
import logging
import re
import statistics
from pathlib import Path

from config.settings import settings  # noqa: E402
from cyclone_modules.ObsControl.obs_control import check_obs_sync  # noqa: E402
from fight_state import get_session_dir as _fs_get_session_dir
from FightControl.round_manager import round_status  # noqa: E402
from utils import check_media_mtx  # noqa: E402
from utils.files import open_utf8
from utils.obs_ws import WS_AVAILABLE, websockets

logger = logging.getLogger(__name__)

_BOUT_SUFFIX_RE = re.compile(r"_BOUT(\d+)$", re.IGNORECASE)


async def _ws_identify(ws):
    await ws.recv()
    await ws.send(json.dumps({"op": 1, "d": {"rpcVersion": 1, "eventSubscriptions": 1}}))
    await ws.recv()


async def check_obs_connection(timeout: float = 0.01):
    """Quickly probe the OBS WebSocket server."""

    uri = settings.OBS_WS_URL.rstrip("/") + "/"
    if not WS_AVAILABLE:
        return
    async with websockets.connect(uri, open_timeout=timeout) as ws:
        await _ws_identify(ws)
        await ws.send(json.dumps({"op": 6, "d": {"requestType": "GetRecordStatus", "requestId": "check_obs"}}))
        await ws.recv()


def check_backend_ready() -> bool:
    """Return True if both OBS (WebSocket) and MediaMTX are reachable."""

    try:
        obs_ok = bool(check_obs_sync())
    except Exception:
        obs_ok = False

    try:
        mtx_ok = bool(check_media_mtx())
    except Exception:
        mtx_ok = False

    return obs_ok and mtx_ok


# -------------------------------------------------
# Session analytics utilities
# -------------------------------------------------


def get_session_dir(name: str, date: str, round_id: str):
    """Compatibility wrapper for :func:`fight_state.get_session_dir`.

    The utility previously lived in ``utils_checks``.  To maintain backwards
    compatibility while centralising the actual implementation in
    :mod:`fight_state`, this thin wrapper simply delegates to
    :func:`fight_state.get_session_dir`.
    """

    return _fs_get_session_dir(name, date, round_id)


def next_bout_number(date: str, red: str, blue: str) -> int:
    """Return the next bout index for the fighter folders.

    The application's base directory is determined by :mod:`paths` and is
    refreshed at call time so any updates to the ``BASE_DIR`` environment
    variable are honoured automatically.
    """

    import paths

    paths.refresh_paths()
    from FightControl.fight_utils import safe_filename

    fighter_root = Path(paths.BASE_DIR) / "FightControl" / "fighter_data"

    def scan(fighter: str) -> int:
        base = fighter_root / safe_filename(fighter) / date
        if not base.exists():
            return 0
        mx = 0
        for d in base.iterdir():
            if not d.is_dir():
                continue
            m = _BOUT_SUFFIX_RE.search(d.name)
            if m:
                try:
                    idx = int(m.group(1))
                    mx = max(mx, idx)
                except Exception:
                    pass
        return mx

    return max(scan(red), scan(blue)) + 1


def load_tags(
    session_dir: str | Path | None = None,
    round_id: str | None = None,
    *,
    fighter_dir: str | Path | None = None,
) -> list[str]:
    """Return tag contents for a fighter session.

    Parameters
    ----------
    session_dir:
        Base directory of the fighter session or bout.  This corresponds to
        ``FightControl/fighter_data/<fighter>/<date>/<bout>/`` in the project
        tree.  For backward compatibility, ``session_dir`` may be omitted if
        ``fighter_dir`` is provided.
    round_id:
        Optional round identifier (e.g. ``"round_1"``).  When supplied the
        returned list is restricted to tags for that round.  With the legacy
        layout this function falls back to ``session_dir / round_id /
        "events.csv"`` if it exists.
    fighter_dir:
        Alias for ``session_dir`` offered for clarity in newer codebases.

    ``events.csv`` rows may follow either the modern schema
    ``timestamp,type,tag,round,fighter`` or the legacy
    ``timestamp,type,content,round_id,fighter_name``.  Only rows whose
    ``type`` is ``"tag"`` contribute to the returned list.  Missing files
    result in an empty list.
    """

    if fighter_dir is not None:
        base = Path(fighter_dir)
    elif session_dir is not None:
        base = Path(session_dir)
    else:  # pragma: no cover - defensive; callers should provide a path
        raise TypeError("Either session_dir or fighter_dir must be specified")

    tags: list[str] = []

    # New schema stores all events in the session directory; older versions
    # used per-round subdirectories.  Prefer the legacy file when present to
    # avoid double-filtering.
    path = base / "events.csv"
    if round_id:
        legacy = base / round_id / "events.csv"
        if legacy.exists():
            path = legacy

    try:
        with open_utf8(path, newline="") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                return []
            # Determine column names for backward compatibility
            tag_col = "tag" if "tag" in reader.fieldnames else "content"
            round_col = "round" if "round" in reader.fieldnames else "round_id"

            for row in reader:
                if (row.get("type") or "").strip().lower() != "tag":
                    continue
                if round_id and path == base / "events.csv":
                    rnd = (row.get(round_col) or "").strip()
                    # Normalise values like "round_1" or "1"
                    target = str(round_id).lower().lstrip("round_")
                    candidate = rnd.lower().lstrip("round_")
                    if candidate != target:
                        continue
                content = (row.get(tag_col) or "").strip()
                if content:
                    tags.append(content)
    except FileNotFoundError as exc:
        logger.warning("events.csv not found at %s", path, exc_info=exc)
    except Exception as exc:  # pragma: no cover - unexpected CSV errors
        logger.exception("Error loading tags from %s", path, exc_info=exc)

    return tags


def calc_time_in_zones(hr_series: list[dict]) -> dict[str, int]:
    """Aggregate total seconds spent in each heart-rate zone.

    ``hr_series`` should be the parsed list from ``hr_data.json`` where
    each entry represents one second of data.
    """
    zones: dict[str, int] = {}
    for point in hr_series:
        zone = point.get("zone")
        if not zone:
            continue
        zones[zone] = zones.get(zone, 0) + 1
    return zones


def calc_bpm_stats(hr_series: list[dict]) -> dict[str, int]:
    """Return min/avg/max BPM values from ``hr_series``."""
    bpm_values = [int(p.get("bpm", 0)) for p in hr_series if p.get("bpm")]
    if not bpm_values:
        return {"min": 0, "avg": 0, "max": 0}
    return {
        "min": min(bpm_values),
        "avg": int(statistics.mean(bpm_values)),
        "max": max(bpm_values),
    }


def build_session_summary(session_dir: str | Path) -> dict:
    """Create ``session_summary.json`` in ``session_dir``.

    The summary combines coach tags, BPM statistics, zone durations and
    the final round status.
    """
    session_dir = Path(session_dir)

    # Load HR series if available
    try:
        hr_series = json.loads((session_dir / "hr_data.json").read_text(encoding="utf-8"))
    except Exception:
        hr_series = []

    summary = {
        "tags": load_tags(session_dir),
        "time_in_zones": calc_time_in_zones(hr_series),
        "bpm_stats": calc_bpm_stats(hr_series),
        "round_results": {},
    }

    try:
        summary["round_results"] = round_status()
    except Exception:
        pass

    (session_dir / "session_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


# Re-export for backward compatibility.  Older modules may still
# import :func:`get_session_dir` from :mod:`utils_checks`, so expose it
# via ``__all__`` when present.
try:  # pragma: no cover - defensive
    __all__.append("get_session_dir")
except NameError:  # pragma: no cover - when ``__all__`` not yet defined
    __all__ = ["get_session_dir"]
