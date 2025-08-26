from flask import Blueprint, jsonify

try:
    # our tiny in-memory default
    from threading import Lock

    DEFAULT_SERVICES = {"hr_daemon": "WAIT", "mediamtx": "WAIT", "obs": "READY"}

    class BootState:
        def __init__(self):
            self._lock = Lock()
            self._services = DEFAULT_SERVICES.copy()

        def snapshot(self):
            with self._lock:
                return dict(self._services)

    boot_state = BootState()
except Exception:
    # ultra-safe fallback
    class _Boot:
        def snapshot(self):
            return {"hr_daemon": "WAIT", "mediamtx": "WAIT", "obs": "READY"}

    boot_state = _Boot()

bp = Blueprint("boot", __name__, url_prefix="/api/boot")


@bp.get("/status")
def boot_status():
    return jsonify({"services": boot_state.snapshot()}), 200
