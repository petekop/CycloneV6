import json

from flask import Blueprint, jsonify, send_from_directory

from paths import BASE_DIR
from round_state import load_round_state
from utils_bpm import read_bpm

overlay_routes = Blueprint("overlay_routes", __name__)
DATA_DIR = BASE_DIR / "FightControl" / "data"
OVERLAY_DIR = BASE_DIR / "CAMSERVER" / "overlay"


def to_overlay(state: str) -> str:
    """Map internal round state to overlay-friendly values."""

    mapping = {
        "offline": "OFFLINE",
        "idle": "OFFLINE",
        "armed": "WAITING",
        "waiting": "WAITING",
        "live": "ACTIVE",
        "active": "ACTIVE",
        "rest": "RESTING",
        "resting": "RESTING",
        "paused": "PAUSED",
        "ended": "ENDED",
    }
    return mapping.get(state.lower(), state.upper())


@overlay_routes.route("/live-json/red_bpm")
def live_bpm_red():
    """Return live heart rate metrics for the red fighter."""
    return jsonify(read_bpm("red"))


@overlay_routes.route("/live-json/blue_bpm")
def live_bpm_blue():
    """Return live heart rate metrics for the blue fighter."""
    return jsonify(read_bpm("blue"))


@overlay_routes.route("/live-json/round_status")
def live_round_status():
    """Return the current round status with overlay state."""

    path = DATA_DIR / "round_status.json"
    try:
        data = json.loads(path.read_text())
    except Exception:
        data = {}
    try:
        state = load_round_state().get("state", "")
    except Exception:
        state = ""
    data["overlay_state"] = to_overlay(state)
    return jsonify(data)


@overlay_routes.route("/overlay/data/<path:fn>")
def overlay_data(fn):
    return send_from_directory(DATA_DIR, fn, max_age=0)


@overlay_routes.route("/overlay/<path:fn>")
def overlay_assets(fn):
    return send_from_directory(OVERLAY_DIR, fn)


@overlay_routes.route("/overlay/")
def serve_overlay():
    return send_from_directory(OVERLAY_DIR, "index.html")
