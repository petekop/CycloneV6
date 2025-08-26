from flask import Blueprint, jsonify

try:
    from FightControl import RoundManager, RoundState  # noqa: F401
except Exception:  # fallback if package exposes only submodule
    import sys

    sys.modules.pop("FightControl", None)
    sys.modules.pop("FightControl.round_manager", None)
    from FightControl.round_manager import RoundManager, RoundState  # noqa: F401

from paths import BASE_DIR

rounds_bp = Blueprint("rounds", __name__)

_state_file = BASE_DIR / "state" / "round_state.json"
round_manager = RoundManager(_state_file)


@rounds_bp.route("/api/round/state", methods=["GET"])
def get_state():
    """Return the current round state."""
    return jsonify(ok=True, state=round_manager.to_dict())


def _transition(state: RoundState):
    try:
        round_manager.transition(state)
    except Exception as exc:  # pragma: no cover - defensive
        return (
            jsonify(ok=False, error=str(exc), state=round_manager.to_dict()),
            409,
        )
    return jsonify(ok=True, state=round_manager.to_dict())


@rounds_bp.route("/api/round/state-machine/start", methods=["POST"])
def start_round():
    return _transition(RoundState.LIVE)


@rounds_bp.route("/api/round/rest", methods=["POST"])
def rest_round():
    return _transition(RoundState.REST)


@rounds_bp.route("/api/round/pause", methods=["POST"])
def pause_round():
    return _transition(RoundState.PAUSED)


@rounds_bp.route("/api/round/resume", methods=["POST"])
def resume_round():
    return _transition(RoundState.LIVE)


@rounds_bp.route("/api/round/end", methods=["POST"])
def end_round():
    return _transition(RoundState.ENDED)


@rounds_bp.route("/api/round/reset", methods=["POST"])
def reset_round():
    return _transition(RoundState.IDLE)
