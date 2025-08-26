"""OBS recording control routes.

Provides endpoints to start, pause, resume and stop OBS recordings via the
``cyclone_modules.ObsControl`` helpers.
"""

try:
    from flask import Blueprint, jsonify
except ImportError:  # pragma: no cover - Flask optional
    Blueprint = None  # type: ignore
    jsonify = lambda *a, **k: {"ok": True}  # type: ignore

try:  # pragma: no cover - optional dependency
    from cyclone_modules.ObsControl import obs_control as obs
except Exception:  # pragma: no cover - provide fallbacks
    class _ObsStub:
        def start_obs_recording(self, *_a, **_k):
            return None

        def pause_obs_recording(self, *_a, **_k):
            return None

        def resume_obs_recording(self, *_a, **_k):
            return None

        def stop_obs_recording(self, *_a, **_k):
            return None

    obs = _ObsStub()

obs_bp = Blueprint("obs", __name__, url_prefix="/api/obs") if Blueprint is not None else None

if obs_bp is not None:

    @obs_bp.post("/record/start")
    def record_start():
        """Start OBS recording."""
        obs.start_obs_recording()
        return jsonify(ok=True)

    @obs_bp.post("/record/pause")
    def record_pause():
        """Pause OBS recording."""
        obs.pause_obs_recording()
        return jsonify(ok=True)

    @obs_bp.post("/record/resume")
    def record_resume():
        """Resume OBS recording."""
        obs.resume_obs_recording()
        return jsonify(ok=True)

    @obs_bp.post("/record/stop")
    def record_stop():
        """Stop OBS recording."""
        obs.stop_obs_recording()
        return jsonify(ok=True)
