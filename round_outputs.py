"""Manage OBS outputs during round start and end.

Loads configuration from ``CONFIG_DIR / "obs_outputs.json"`` and provides helpers
to start and stop OBS outputs for each round. Optionally controls the program
recording and moves output files when a round finishes.
"""

from __future__ import annotations

import asyncio
import csv
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import sys
import types

try:  # Optional websockets dependency
    import websockets  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - default path in tests
    class _WSStub:
        async def send(self, *_args, **_kwargs):
            return None

        async def recv(self):
            return "{}"

        async def close(self):
            return None

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_exc):
            return None

    async def _missing_ws(*_args, **_kwargs):  # pragma: no cover - simple stub
        logging.getLogger(__name__).warning(
            "websockets library is not installed; OBS features are disabled"
        )
        return _WSStub()

    _missing_ws._is_stub = True  # type: ignore[attr-defined]

    websockets = types.SimpleNamespace(
        connect=_missing_ws,
        ConnectionClosed=RuntimeError,
        WebSocketClientProtocol=_WSStub,
    )
    sys.modules["websockets"] = websockets

WS_AVAILABLE = not getattr(websockets.connect, "_is_stub", False)

from fight_state import load_fight_state  # noqa: E402
from FightControl.fight_utils import safe_filename  # noqa: E402
from paths import BASE_DIR, CONFIG_DIR  # noqa: E402
from utils.file_moves import move_outputs_for_round as _move_outputs_sync  # noqa: E402
from utils.files import open_utf8  # noqa: E402
from config.settings import settings

try:  # Optional at runtime
    from zone_tracker import ZoneTracker
except Exception:  # pragma: no cover - zone tracking unavailable
    ZoneTracker = None  # type: ignore

logger = logging.getLogger(__name__)

CONFIG_PATH = CONFIG_DIR / "obs_outputs.json"


def _load_config() -> dict[str, Any]:
    try:
        text = CONFIG_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.warning("OBS outputs config file not found at %s", CONFIG_PATH)
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        logger.warning("Invalid JSON in OBS outputs config at %s: %s", CONFIG_PATH, exc)
        return {}


CONFIG: dict[str, Any] = _load_config()
OUTPUTS: list[str] = CONFIG.get("outputs", [])
OVERLAY_WARMUP_MS: int = int(CONFIG.get("overlay_warmup_ms", 0))
ALSO_RECORD_PROGRAM: bool = bool(CONFIG.get("also_record_program", False))
SOURCE_RECORDS: dict[str, int] = CONFIG.get("source_records", {})


def make_filename(bout: int, round_no: int, camera: str, ext: str = ".mkv") -> str:
    """Return a standard filename for an output recording.

    Parameters
    ----------
    bout:
        Bout number starting at ``1``.
    round_no:
        Round number starting at ``1``.
    camera:
        Camera identifier used in the filename.
    ext:
        File extension including the leading dot.  If omitted, ``.mkv`` is
        used by default.  A missing leading dot is added automatically.

    Returns
    -------
    str
        A filesystem-safe filename in the format
        ``B<bb>_R<rr>_<camera><ext>`` where ``bb`` and ``rr`` are zero padded
        to two digits and ``camera`` is sanitised via
        :func:`FightControl.fight_utils.safe_filename`.
    """

    cam = safe_filename(camera)
    if not cam:
        cam = "unnamed"
    ext = ext if ext.startswith(".") else f".{ext}"
    return f"B{int(bout):02d}_R{int(round_no):02d}_{cam}{ext}"


def round_folder(bout: int, round_no: int) -> Path:
    """Return the directory path for ``bout`` and ``round_no``.

    The directory is created beneath :data:`settings.BASE_DIR` in the structure
    ``<BASE_DIR>/round_outputs/B<bb>/R<rr>`` where ``bb`` and ``rr`` are zero
    padded.  The directory is created if it does not already exist.
    """

    path = settings.BASE_DIR / "round_outputs" / f"B{int(bout):02d}" / f"R{int(round_no):02d}"
    path.mkdir(parents=True, exist_ok=True)
    return path


class ObsWs:
    """Minimal OBS WebSocket v5 client."""

    def __init__(self, uri: str | None = None) -> None:
        uri = (uri or str(settings.OBS_WS_URL)).rstrip("/") + "/"
        self.uri = uri

    async def _identify(self, ws: websockets.WebSocketClientProtocol) -> None:
        await ws.recv()
        await ws.send(json.dumps({"op": 1, "d": {"rpcVersion": 1, "eventSubscriptions": 1}}))
        await ws.recv()

    async def request(self, request_type: str, request_data: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = {
            "op": 6,
            "d": {
                "requestType": request_type,
                "requestId": f"{request_type}_{int(time.time()*1000)}",
            },
        }
        if request_data:
            payload["d"]["requestData"] = request_data
        if not WS_AVAILABLE:
            return {"d": {"requestStatus": {"result": True}}}
        async with websockets.connect(self.uri) as ws:
            await self._identify(ws)
            await ws.send(json.dumps(payload))
            resp = await ws.recv()
        return json.loads(resp)


OBS = ObsWs()

_round_start_ts: datetime | None = None


async def _start_output(name: str) -> None:
    try:
        resp = await OBS.request("StartOutput", {"outputName": name})
        status = resp.get("d", {}).get("requestStatus", {})
        if status.get("result"):
            logger.info("Started output: %s", name)
        else:
            comment = (status.get("comment") or "").lower()
            if "already active" in comment:
                logger.warning("Output already active: %s", name)
            else:
                logger.error("Failed to start output %s: %s", name, comment)
    except Exception as exc:  # pragma: no cover - network errors
        logger.error("Error starting output %s: %s", name, exc)


async def _start_source_record(record_id: int) -> None:
    try:
        await OBS.request(
            "CallVendorRequest",
            {
                "vendorName": "source-record",
                "requestType": "start",
                "requestData": {"sourceRecordID": record_id},
            },
        )
        logger.info("Started source record %s", record_id)
    except Exception as exc:  # pragma: no cover - network errors
        logger.error("Error starting source record %s: %s", record_id, exc)


async def _stop_output(name: str) -> None:
    try:
        resp = await OBS.request("StopOutput", {"outputName": name})
        status = resp.get("d", {}).get("requestStatus", {})
        if status.get("result"):
            logger.info("Stopped output: %s", name)
        else:
            comment = (status.get("comment") or "").lower()
            if "not active" in comment or "already inactive" in comment:
                logger.warning("Output already inactive: %s", name)
            else:
                logger.error("Failed to stop output %s: %s", name, comment)
    except Exception as exc:  # pragma: no cover - network errors
        logger.error("Error stopping output %s: %s", name, exc)


# Stop recording for a specific source via the OBS source-record vendor
async def _stop_source_record(record_id: int) -> None:
    try:
        await OBS.request(
            "CallVendorRequest",
            {
                "vendorName": "source-record",
                "requestType": "stop",
                "requestData": {"sourceRecordID": record_id},
            },
        )
        logger.info("Stopped source record %s", record_id)
    except Exception as exc:  # pragma: no cover - network errors
        logger.error("Error stopping source record %s: %s", record_id, exc)


def save_round_meta(
    fighter: str,
    date: str,
    round_no: int,
    duration_s: float,
    files: list[Path],
    hr_stats: dict[str, Any] | None = None,
) -> Path:
    """Write ``round_meta.json`` for ``fighter`` and return its path.

    Reads ``hr_log.csv`` and ``tags.csv`` in the fighter's round directory to
    compute tag counts (and complements supplied hr_stats if needed). Missing
    files are handled gracefully.
    """
    safe_name = safe_filename(fighter)
    round_dir = BASE_DIR / "FightControl" / "fighter_data" / safe_name / date / f"round_{round_no}"
    round_dir.mkdir(parents=True, exist_ok=True)

    # --- HR stats (prefer provided snapshot; else compute simple min/avg/max) ---
    stats: dict[str, Any] = hr_stats or {}
    if not stats:
        hr_path = round_dir / "hr_log.csv"
        if hr_path.exists():
            try:
                with open_utf8(hr_path) as f:
                    reader = csv.reader(f)
                    bpms = [float(row[1]) for row in reader if len(row) > 1]
                if bpms:
                    stats = {
                        "min": min(bpms),
                        "avg": sum(bpms) / len(bpms),
                        "max": max(bpms),
                    }
            except Exception:
                stats = {}

    # --- Tags count ---
    tags_count = 0
    tag_path = round_dir / "tags.csv"
    if tag_path.exists():
        try:
            with open_utf8(tag_path) as f:
                reader = csv.reader(f)
                _ = next(reader, None)  # header (optional)
                tags_count = sum(1 for _ in reader)
        except Exception:
            tags_count = 0

    meta = {
        "duration_s": float(duration_s),
        "files": [str(Path(p)) for p in files],
        "hr_stats": stats,
        "tags_count": int(tags_count),
        "generated_at": datetime.utcnow().isoformat(),
    }
    meta_path = round_dir / "round_meta.json"
    try:
        meta_path.write_text(json.dumps(meta, indent=2))
    except Exception:
        logger.exception("Failed to write round meta to %s", meta_path)
        raise
    return meta_path


async def move_outputs_for_round(round_meta: dict[str, Any]) -> None:
    """Move/rename output files produced during the round and write round_meta.json.

    ``round_meta`` should contain:
      - fight_id, round_no, red_name, blue_name, date, start, (optional) end
      - (optional) hr_stats  -> may be {'red': {...}, 'blue': {...}}
    """
    # Build obs/file-move config for utils.file_moves
    obs_cfg = {
        "staging_root": CONFIG.get("staging_root"),
        "dest_root": CONFIG.get("dest_root"),
        "outputs": CONFIG.get("outputs", []),
        "output_to_corner": CONFIG.get("output_to_corner", {}),
        "move_poll": CONFIG.get("move_poll", {}),
        # Legacy workflow keys kept for compatibility with _move_outputs_sync
        "cameras": CONFIG.get("cameras", []),
        "exts": CONFIG.get("exts", []),
        "stable_seconds": CONFIG.get("stable_seconds"),
    }

    logger.info("Moving OBS outputs for round: %s", round_meta)
    moved = await asyncio.to_thread(_move_outputs_sync, obs_cfg, round_meta)
    # normalize to Path list
    moved_paths: list[Path] = [Path(p) for p in (moved or [])]

    # Compute duration from start→(end|now)
    try:
        start = datetime.fromisoformat(str(round_meta.get("start")))
    except Exception:
        start = datetime.utcnow()
    try:
        end = datetime.fromisoformat(str(round_meta.get("end")))
    except Exception:
        end = datetime.utcnow()
    duration = (end - start).total_seconds()

    # Inputs for saving meta
    date = str(round_meta.get("date", datetime.utcnow().date().isoformat()))
    round_no = int(round_meta.get("round_no") or round_meta.get("round") or 1)
    red = round_meta.get("red_name")
    blue = round_meta.get("blue_name")
    hr_stats_all = round_meta.get("hr_stats") or {}

    # Write per‑fighter round_meta.json
    if red:
        red_stats = hr_stats_all.get("red", hr_stats_all) if isinstance(hr_stats_all, dict) else {}
        try:
            save_round_meta(red, date, round_no, duration, moved_paths, red_stats)
        except Exception:
            logger.exception("save_round_meta failed for fighter %s", red)
    if blue:
        blue_stats = hr_stats_all.get("blue", hr_stats_all) if isinstance(hr_stats_all, dict) else {}
        try:
            save_round_meta(blue, date, round_no, duration, moved_paths, blue_stats)
        except Exception:
            logger.exception("save_round_meta failed for fighter %s", blue)


async def round_start() -> None:
    """Handle OBS actions when a round starts."""
    global _round_start_ts
    _round_start_ts = datetime.utcnow()
    if ALSO_RECORD_PROGRAM:
        try:
            await OBS.request("StartRecord")
            logger.info("Program recording started")
        except Exception as exc:  # pragma: no cover - network errors
            logger.error("Program recording start failed: %s", exc)
    await asyncio.sleep(OVERLAY_WARMUP_MS / 1000)
    await asyncio.gather(*(_start_output(o) for o in OUTPUTS))
    await asyncio.gather(*(_start_source_record(rid) for rid in SOURCE_RECORDS.values()))


async def round_end() -> None:
    """Handle OBS actions when a round ends."""
    await asyncio.gather(*(_stop_output(o) for o in OUTPUTS))
    await asyncio.gather(*(_stop_source_record(rid) for rid in SOURCE_RECORDS.values()))
    if ALSO_RECORD_PROGRAM:
        try:
            await OBS.request("StopRecord")
            logger.info("Program recording stopped")
        except Exception as exc:  # pragma: no cover - network errors
            logger.error("Program recording stop failed: %s", exc)

    fight, date, round_id = load_fight_state()
    red = fight.get("red_fighter") or fight.get("red") or "Red"
    blue = fight.get("blue_fighter") or fight.get("blue") or "Blue"
    fight_id = fight.get("fight_id") or f"{safe_filename(red)}_vs_{safe_filename(blue)}_{date}"
    try:
        round_no = int(str(round_id).split("_")[-1])
    except Exception:
        round_no = 1
    start_ts = _round_start_ts or datetime.utcnow()

    # Prefer live ZoneTracker snapshot if available
    hr_stats = {}
    try:
        if ZoneTracker and hasattr(ZoneTracker, "stats"):
            hr_stats = ZoneTracker.stats() or {}
    except Exception:
        hr_stats = {}

    round_meta = {
        "fight_id": fight_id,
        "round_no": round_no,
        "red_name": red,
        "blue_name": blue,
        "date": date,
        "start": start_ts.isoformat(),
        "end": datetime.utcnow().isoformat(),  # added for precise duration
        "hr_stats": hr_stats,
    }
    # Fire and forget - move recordings and write round_meta.json
    asyncio.create_task(move_outputs_for_round(round_meta))


# Convenient aliases
start_round_outputs = round_start
end_round_outputs = round_end


__all__ = [
    "round_start",
    "round_end",
    "start_round_outputs",
    "end_round_outputs",
    "move_outputs_for_round",
    "save_round_meta",
    "ObsWs",
    "make_filename",
    "round_folder",
]
