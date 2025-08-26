from flask import Blueprint, send_from_directory

from paths import BASE_DIR

overlay_bp = Blueprint("overlay", __name__)


@overlay_bp.route("/overlay")
def serve_overlay():
    overlay_dir = BASE_DIR / "CAMSERVER" / "overlay"
    return send_from_directory(str(overlay_dir), "overlay.html")
