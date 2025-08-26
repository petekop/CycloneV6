from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from bleak import BleakClient

# ------------------------- Base dir & paths -------------------------

try:
    import paths  # project helper
except Exception:
    paths = None  # type: ignore


def _get_base_dir() -> Path:
    if paths is not None:
        bd = getattr(paths, "base_dir", None)
        if callable(bd):
            try:
                p = Path(bd())
                if p.exists():
                    return p
            except Exception:
                pass
        bd2 = getattr(paths, "BASE_DIR", None)
        if bd2:
            try:
                p = Path(bd2)
                if p.exists():
                    return p
            except Exception:
                pass
    env = os.environ.get("BASE_DIR")
    if env:
        try:
            p = Path(env)
            if p.exists():
                return p
        except Exception:
            pass
    return Path.cwd()


BASE_DIR = _get_base_dir()

# Ensure cyclone_modules is on sys.path for HRLogger
mods_dir = BASE_DIR / "cyclone_modules"
if mods_dir.exists():
    sys.path.insert(0, str(mods_dir))

# --------------------- HRLogger (zone model) import -------------------

try:
    # Preferred (repo layout)
    from cyclone_modules.HRLogger.hr_logger import load_zone_model  # type: ignore
except Exception:
    try:
        # Fallback if module is importable by package name
        from HRLogger.hr_logger import load_zone_model  # type: ignore
    except Exception:
        def load_zone_model(_fighter_name: Optional[str]) -> dict:
            return {}

# ---------------- Round state & logging (robust) ---------------------

def _fallback_round_status() -> Dict[str, Any]:
    return {"status": "ACTIVE", "round": 0}

def _fallback_load_fight_state():
    return ({"red_fighter": "Red", "blue_fighter": "Blue"}, datetime.now().strftime("%Y-%m-%d"), 0)

def _fallback_log_bpm(name, date, round_id, bpm, status, bout_name=None, meta=None):
    return None

try:
    from FightControl.round_manager import round_status as _round_status  # type: ignore
except Exception:
    _round_status = _fallback_round_status  # type: ignore

try:
    from FightControl.round_manager import _load_fight_state as _load_fight_state  # type: ignore
except Exception:
    _load_fight_state = _fallback_load_fight_state  # type: ignore

try:
    from FightControl.round_manager import log_bpm as _log_bpm  # type: ignore
except Exception:
    _log_bpm = _fallback_log_bpm  # type: ignore

try:
    from FightControl.fight_utils import safe_filename as _safe_filename  # type: ignore
except Exception:
    def _safe_filename(name: str) -> str:
        bad = '<>:"/\\|?*'
        for ch in bad:
            name = name.replace(ch, "")
        return "_".join(name.split()).strip("_")

# ----------------------- BLE helpers/compat --------------------------

async def _bleak_wait_compat(client: BleakClient) -> None:
    """
    Wait for disconnect in a way that works across Bleak backends (WinRT has no wait_for_disconnect()).
    Treat asyncio.CancelledError as a graceful shutdown.
    """
    import asyncio as _asyncio
    try:
        evt = getattr(client, "disconnected_event", None)
        if evt is not None:
            await evt.wait()
            return

        loop = _asyncio.get_running_loop()
        fut: _asyncio.Future[None] = loop.create_future()

        def _on_disc(_):
            if not fut.done():
                loop.call_soon_threadsafe(fut.set_result, None)

        set_cb = getattr(client, "set_disconnected_callback", None)
        if callable(set_cb):
            set_cb(_on_disc)
            await fut
            return

        while True:
            if not getattr(client, "is_connected", False):
                return
            await _asyncio.sleep(0.5)

    except _asyncio.CancelledError:
        return  # graceful shutdown


def _log_bpm_compat(_fn, name, date, round_id, bpm, status,
                    bout_name=None, meta=None, overlay_state=None):
    """
    Call log_bpm with the correct signature.
    Older (5-arg) loggers expect a STATE DICT as arg #5, not a string.
    """
    try:
        import inspect
        n = len(inspect.signature(_fn).parameters)
    except Exception:
        n = 7  # safest default

    if n <= 5:
        # (name, date, round_id, bpm, state_dict)
        arg5 = overlay_state if overlay_state is not None else {"status": status}
        return _fn(name, date, round_id, bpm, arg5)
    if n == 6:
        # (name, date, round_id, bpm, status_or_state, bout_name)
        return _fn(name, date, round_id, bpm, status, bout_name)
    # (name, date, round_id, bpm, status, bout_name, meta)
    return _fn(name, date, round_id, bpm, status, bout_name, meta)


def parse_hr_measurement(data: bytes | bytearray) -> Optional[int]:
    """
    Parse Bluetooth Heart Rate Measurement (0x2A37).
    Handles 8-bit and 16-bit values.
    """
    if not data or len(data) < 2:
        return None
    flags = data[0]
    hr_16bit = flags & 0x01
    try:
        if hr_16bit:
            if len(data) < 3:
                return None
            bpm = int.from_bytes(data[1:3], "little")
        else:
            bpm = int(data[1])
        if bpm <= 0 or bpm > 510:
            return None
        return int(bpm)
    except Exception:
        return None

# ----------------------------- Defaults --------------------------------

DEFAULT_MACS: Dict[str, str] = {
    # Your known straps from the scan
    "red":  "A0:9E:1A:EB:9C:A5",
    "blue": "A0:9E:1A:EB:A2:36",
}

HR_CHAR_UUID = "00002A37-0000-1000-8000-00805F9B34FB".lower()

# ============================== Daemon =================================

class HRDaemon:
    def __init__(self, colour: str) -> None:
        self.colour = colour.lower()  # "red" or "blue"
        self.zone_model: Dict[str, Any] | None = None
        self.EMA_VALUE: Optional[float] = None
        self.SMOOTH_BUFFER: list[int] = []
        self.mac: Optional[str] = self._resolve_mac()
        self.fighter_name: str = ""  # can be set by caller
        self.calc_zone = lambda bpm: ("none", 0)  # monkey-patchable

    # -------------------------- Paths/IO helpers --------------------------

    def _overlay_dir(self) -> Path:
        p = BASE_DIR / "FightControl" / "data" / "overlay"
        p.mkdir(parents=True, exist_ok=True)
        return p

    def _cache_dir(self) -> Path:
        p = BASE_DIR / "FightControl" / "cache"
        p.mkdir(parents=True, exist_ok=True)
        return p

    def write_status(self, text: str) -> None:
        p = BASE_DIR / "FightControl" / "live_data"
        p.mkdir(parents=True, exist_ok=True)
        (p / f"{self.colour}_status.txt").write_text(str(text))

    # ------------------------ Config / MAC resolve ------------------------

    def _resolve_mac(self) -> Optional[str]:
        env_var = f"HR_{self.colour.upper()}_MAC"
        mac = os.environ.get(env_var)
        if mac:
            return mac

        cfg = BASE_DIR / "FightControl" / "heartrate_mon" / "config.json"
        try:
            cfg_data = json.loads(cfg.read_text())
            mac2 = cfg_data.get(self.colour)
            if mac2:
                return mac2
            self.write_status(f"No {self.colour} MAC in config.json; using default")
        except Exception:
            self.write_status("Missing/invalid config.json; using defaults")

        return DEFAULT_MACS.get(self.colour)

    # ---------------------------- Overlay/cache ---------------------------

    def _ensure_zone_model(self) -> None:
        if self.zone_model is None:
            try:
                self.zone_model = load_zone_model(self.fighter_name or None)
            except Exception:
                self.zone_model = {}

    def write_overlay_json(self, bpm: int | float, status: str, current_round: int) -> None:
        self._ensure_zone_model()
        try:
            zone, effort = self.calc_zone(bpm)
        except Exception:
            zone, effort = "none", 0
        try:
            effort = max(0, min(100, int(effort)))
        except Exception:
            effort = 0

        payload: Dict[str, Any] = {
            "bpm": bpm,
            "effort_percent": effort,
            "zone": zone,
            "status": status,
            "round": current_round,
            "time": datetime.now().isoformat(timespec="seconds"),
        }

        if self.zone_model:
            if self.zone_model.get("max_hr") is not None:
                payload["max_hr"] = self.zone_model.get("max_hr")
            if self.zone_model.get("smoothing") is not None:
                payload["smoothing"] = self.zone_model.get("smoothing")

        (self._overlay_dir() / f"{self.colour}_bpm.json").write_text(json.dumps(payload))

        cache_path = self._cache_dir() / f"{self.colour}_bpm_series.json"
        try:
            series = json.loads(cache_path.read_text())
            if not isinstance(series, list):
                series = []
        except Exception:
            series = []
        series.append({
            "time": payload["time"],
            "bpm": bpm,
            "status": status,
            "round": current_round,
            "zone": payload["zone"],
        })
        cache_path.write_text(json.dumps(series))

    # ------------------------------ Logging --------------------------------

    def _round_status(self) -> Dict[str, Any]:
        try:
            rs = _round_status()  # type: ignore
            if isinstance(rs, dict):
                return rs
            # tolerate odd returns
            return {"status": str(rs), "round": 0}
        except Exception:
            return _fallback_round_status()

    def write_bpm(self, bpm: int | float) -> None:
        rs = self._round_status()
        status = rs.get("status", "ACTIVE")
        rnd = int(rs.get("round", 0) or 0)

        self.write_overlay_json(bpm, status, rnd)

        if os.environ.get("CYCLONE_SKIP_LOG_BPM", "").lower() in {"1","true","yes"}:
            return

        try:
            fight_state, date, round_id = _load_fight_state()
            red_name = fight_state.get("red_fighter", "Red")
            blue_name = fight_state.get("blue_fighter", "Blue")
            name = red_name if self.colour == "red" else blue_name
            bout_name = f"{_safe_filename(red_name)}_vs_{_safe_filename(blue_name)}"
        except Exception:
            date = datetime.now().strftime("%Y-%m-%d")
            round_id = 0
            name = self.colour.capitalize()
            bout_name = "Red_vs_Blue"

        overlay_state = {"status": status, "round": rnd}

        _log_bpm_compat(
            _log_bpm, name, date, round_id, bpm, status,
            bout_name, {"bpm": bpm}, overlay_state=overlay_state
        )

    # -------------------------- BLE Notifications --------------------------

    def handle_data(self, sender_or_data, maybe_data: Optional[bytes] = None) -> None:
        data = maybe_data if maybe_data is not None else sender_or_data
        bpm = parse_hr_measurement(data)
        if bpm is None:
            return
        self.write_bpm(bpm)

    # ---------------------------- Main connect -----------------------------

    async def run(self) -> None:
        mac = self.mac
        if not mac:
            self.write_status(f"NO_MAC_{self.colour.upper()}")
            raise RuntimeError(f"No MAC address configured for {self.colour}")

        self.write_status("CONNECTING")
        try:
            async with BleakClient(mac) as client:
                self.write_status("CONNECTED")
                await client.start_notify(HR_CHAR_UUID, self.handle_data)
                try:
                    await _bleak_wait_compat(client)  # WinRT-safe
                except asyncio.CancelledError:
                    pass
                finally:
                    try:
                        await client.stop_notify(HR_CHAR_UUID)
                    except Exception:
                        pass
        except Exception:
            self.write_status("DISCONNECTED")
            raise
