"""Health check blueprint.

Provides a lightweight ``/api/health`` endpoint for status probes.
"""

import json
import time

try:
    from flask import Blueprint
except ImportError:  # pragma: no cover - Flask optional
    Blueprint = None
import psutil

from paths import BASE_DIR
from utils import check_media_mtx, is_process_running, obs_health

health_bp = Blueprint("health", __name__) if Blueprint is not None else None


if health_bp is not None:

    @health_bp.route("/", strict_slashes=False)
    def api_health():
        """Return quick status information about system components."""

        from flask import jsonify

        try:
            obs_ok = obs_health.healthy(timeout=0.05)
        except Exception:
            obs_ok = False
        mtx_ok = check_media_mtx(timeout=0.05)
        hr_running = is_process_running("heartrate_mon.daemon")
        if not hr_running:
            overlay_dir = BASE_DIR / "FightControl" / "data" / "overlay"
            now = time.time()
            for name in ("red_bpm.json", "blue_bpm.json"):
                try:
                    entry = json.loads((overlay_dir / name).read_text())
                except (FileNotFoundError, json.JSONDecodeError):
                    continue
                stamp = entry.get("time")
                if isinstance(stamp, (int, float)) and now - stamp < 10:
                    hr_running = True
                    break
        usage = psutil.disk_usage("/")
        data = {
            "obs_connected": obs_ok,
            "mediamtx_running": mtx_ok,
            "hr_daemon": hr_running,
            "disk_free_gb": round(usage.free / (1024**3), 2),
            "cpu_percent": psutil.cpu_percent(interval=None),
            "mem_percent": psutil.virtual_memory().percent,
        }
        return jsonify(data)
