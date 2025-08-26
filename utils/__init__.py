from __future__ import annotations

import contextlib
import logging
import os
import shutil
import signal
import socket
import subprocess
import time
from collections.abc import Iterable
from pathlib import Path
from urllib.parse import urlparse

try:  # pragma: no cover - optional dependency
    import psutil  # type: ignore
except Exception:  # pragma: no cover - fallback when psutil is missing
    psutil = None  # type: ignore[assignment]

from config.settings import settings
from open_utf8 import open_utf8
from config.boot_paths import load_boot_paths

from .files import read_csv_dicts
from .obs_health import ObsHealth, obs_health

__all__ = [
    "open_utf8",
    "read_csv_dicts",
    "check_obs_connection",
    "check_media_mtx",
    "quick_disk_free_gb",
    "quick_cpu_percent",
    "quick_mem_percent",
    "process_is_running",
    "is_process_running",
    "terminate_process",
    "play_audio",
    "ensure_dir",
    "ensure_dir_permissions",
    "obs_health",
    "ObsHealth",
]

try:  # pragma: no cover - optional dependency
    import simpleaudio
    from pydub import AudioSegment
except Exception:  # pragma: no cover - fallback when libs missing
    simpleaudio = None
    AudioSegment = None

# ---- Fast network reachability checks (use tiny timeouts) ----


def check_obs_connection(host: str | None = None, port: int | None = None, timeout: float = 0.05) -> bool:
    """Return True if the OBS WebSocket TCP port is reachable quickly."""

    if host is None or port is None:
        parsed = urlparse(settings.OBS_WS_URL)
        host = host or parsed.hostname or "127.0.0.1"
        port = port or (parsed.port or 80)

    s = socket.socket()
    s.settimeout(timeout)
    try:
        s.connect((host, port))
        return True
    except OSError:
        return False
    finally:
        with contextlib.suppress(Exception):
            s.close()


def check_media_mtx(host: str = "127.0.0.1", port: int | None = None, timeout: float = 0.05) -> bool:
    """Return True if MediaMTX is reachable (RTSP TCP listen)."""
    if port is None:
        try:
            port = int(load_boot_paths().get("mediamtx", {}).get("rtsp_port", 8554))
        except Exception:  # pragma: no cover - best effort
            port = 8554
    s = socket.socket()
    s.settimeout(timeout)
    try:
        s.connect((host, port))
        return True
    except OSError:
        return False
    finally:
        try:
            s.close()
        except Exception:
            pass


# ---- Lightweight system metrics (no blocking intervals) ----


def quick_disk_free_gb(path: str | None = None) -> float:
    """Fast free space check in GiB (uses current drive by default)."""
    p = path or os.getcwd()
    usage = shutil.disk_usage(p)
    return round(usage.free / (1024**3), 2)


def quick_cpu_percent() -> float:
    """
    Non-blocking CPU percent. psutil uses a cached sample when interval=0.0.
    First call may be 0.0; that's acceptable for a health probe.
    """
    if psutil is None:  # pragma: no cover - psutil missing
        return 0.0
    return float(psutil.cpu_percent(interval=0.0))


def quick_mem_percent() -> float:
    """Instantaneous memory usage percent."""
    if psutil is None:  # pragma: no cover - psutil missing
        return 0.0
    return float(psutil.virtual_memory().percent)


# ---- Process checks for HR daemons ----


def process_is_running(names: Iterable[str] | tuple[str, ...]) -> bool:
    """
    True if any process whose name OR cmdline contains one of `names` is running.
    Uses limited attrs to keep it fast.
    """
    if psutil is None:  # pragma: no cover - psutil missing
        return False
    want = tuple(n.lower() for n in names)
    for p in psutil.process_iter(attrs=("name", "cmdline")):
        try:
            name = (p.info.get("name") or "").lower()
            if name and any(w in name for w in want):
                return True
            cmd = " ".join(p.info.get("cmdline") or ()).lower()
            if cmd and any(w in cmd for w in want):
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False


def is_process_running(name: str) -> bool:
    """Return True if any running process matches ``name``.

    The check inspects both the executable name and each element of the
    command line in a case-insensitive manner. When :mod:`psutil` is
    available this simply delegates to :func:`process_is_running` for
    consistency. If :mod:`psutil` is not installed a best effort fallback
    parses ``ps`` (POSIX) or ``tasklist`` (Windows) output and performs a
    case-insensitive substring match against each command line.
    """

    if psutil is not None:  # pragma: no branch - preferred path
        return process_is_running((name,))

    cmd = name.lower()
    try:
        if os.name == "nt":  # Windows
            out = subprocess.check_output(["tasklist"], text=True, errors="ignore")
            return any(cmd in line.lower() for line in out.splitlines())
        else:  # POSIX
            out = subprocess.check_output(["ps", "-Ao", "cmd"], text=True, errors="ignore")
            for line in out.splitlines()[1:]:  # skip header
                if cmd in line.lower():
                    return True
            return False
    except Exception:  # pragma: no cover - best effort
        return False


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

AUDIO_CACHE = {}


def _load_audio(path: Path):
    if simpleaudio is None or AudioSegment is None:
        return None
    try:
        seg = AudioSegment.from_file(path)
        return simpleaudio.WaveObject(
            seg.raw_data,
            num_channels=seg.channels,
            bytes_per_sample=seg.sample_width,
            sample_rate=seg.frame_rate,
        )
    except Exception as e:  # pragma: no cover - best effort
        logger.error("Failed to load audio %s: %s", path, e)
        return None


def _preload_audio_dir(directory: Path):
    for p in directory.glob("*"):
        wave = _load_audio(p)
        if wave:
            AUDIO_CACHE[str(p.resolve())] = wave
            AUDIO_CACHE[p.name] = wave


try:  # pragma: no cover - best effort
    _base = Path(__file__).resolve().parent.parent / "FightControl" / "audio"
    if _base.exists():
        _preload_audio_dir(_base)
except Exception:
    pass


def terminate_process(name, timeout=5.0):
    """Terminate all processes matching ``name``.

    If a process does not exit within ``timeout`` seconds after
    termination it will be killed.
    """
    if psutil is not None:  # preferred path
        for p in psutil.process_iter(["name", "cmdline"]):
            try:
                if name.lower() in (p.info.get("name") or "").lower() or any(
                    name.lower() in (c or "").lower() for c in (p.info.get("cmdline") or [])
                ):
                    p.terminate()
                    try:
                        p.wait(timeout=timeout)
                    except psutil.TimeoutExpired:
                        p.kill()
                        with contextlib.suppress(psutil.TimeoutExpired):
                            p.wait(timeout=timeout)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return

    # Fallback when psutil is unavailable
    cmd = name.lower()
    try:
        if os.name == "nt":  # Windows
            out = subprocess.check_output(["tasklist"], text=True, errors="ignore")
            pids = []
            for line in out.splitlines():
                if cmd in line.lower():
                    parts = line.split()
                    if len(parts) >= 2 and parts[1].isdigit():
                        pids.append(int(parts[1]))
            for pid in pids:
                subprocess.run(
                    ["taskkill", "/PID", str(pid), "/T", "/F"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            deadline = time.time() + timeout
            while time.time() < deadline and is_process_running(name):
                time.sleep(0.1)
            return

        # POSIX
        out = subprocess.check_output(["ps", "-Ao", "pid,cmd"], text=True, errors="ignore")
        pids = []
        for line in out.splitlines()[1:]:
            line = line.strip()
            if not line:
                continue
            parts = line.split(None, 1)
            if len(parts) < 2:
                continue
            pid_str, cmdline = parts
            if cmd in cmdline.lower():
                with contextlib.suppress(ValueError):
                    pids.append(int(pid_str))
        for pid in pids:
            with contextlib.suppress(OSError):
                os.kill(pid, signal.SIGTERM)
        deadline = time.time() + timeout
        while time.time() < deadline:
            if not is_process_running(name):
                break
            time.sleep(0.1)
        else:
            for pid in pids:
                with contextlib.suppress(OSError):
                    os.kill(pid, signal.SIGKILL)
        # final brief wait to allow OS to reap
        time.sleep(0.1)
    except Exception:  # pragma: no cover - best effort
        return


def play_audio(path):
    p = Path(path)
    key = None
    for k in (str(p.resolve()), p.name):
        if k in AUDIO_CACHE:
            key = k
            break
    if key is None:
        candidate = p if p.is_absolute() else Path(__file__).resolve().parent.parent / "FightControl" / "audio" / p.name
        wave = _load_audio(candidate)
        if wave:
            AUDIO_CACHE[str(candidate.resolve())] = wave
            AUDIO_CACHE[candidate.name] = wave
            key = str(candidate.resolve())
    wave_obj = AUDIO_CACHE.get(key) if key else None
    if not wave_obj:
        logger.error("Audio playback failed: %s", path)
        return
    try:
        wave_obj.play()
    except Exception as e:  # pragma: no cover - best effort
        logger.error("Audio playback failed: %s", e)


def ensure_dir(path: Path) -> Path:
    """Ensure ``path`` exists and return it.

    The directory and any missing parents are created if necessary.  An
    :class:`OSError` is raised on failure which allows callers to provide more
    context when desired.
    """

    path.mkdir(parents=True, exist_ok=True)
    return path


def ensure_dir_permissions(path: Path, mode: int = 0o755) -> int:
    """Ensure ``path`` exists with ``mode`` permissions.

    The directory is created if missing and its permissions are explicitly
    set afterwards to guarantee the final mode regardless of the current umask.
    ``chmod`` is skipped on Windows platforms.

    Returns the final permission bits of ``path``.
    """
    path.mkdir(mode=mode, parents=True, exist_ok=True)
    if os.name != "nt":
        os.chmod(path, mode)
    return path.stat().st_mode & 0o777
