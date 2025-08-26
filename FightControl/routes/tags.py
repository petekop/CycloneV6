import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Callable

from flask import Blueprint, jsonify, request

from FightControl.common.states import RoundState
from FightControl.fight_utils import safe_filename
from FightControl.fighter_paths import round_dir
from FightControl.round_manager import get_state, round_status
from utils.csv_writer import DebouncedCsvWriter
from utils_checks import next_bout_number

FIELDS = [
    "ts_iso",
    "button_id",
    "label",
    "color",
    "state",
    "fighter",
    "user",
]


def _default_log_path() -> Path:
    state = get_state()
    bout = state.bout or {}
    date = bout.get("fight_date") or datetime.now().strftime("%Y-%m-%d")
    red = bout.get("red_fighter") or bout.get("red") or "Red"
    blue = bout.get("blue_fighter") or bout.get("blue") or "Blue"
    round_id = f"round_{state.round}" if state.round else "round_1"
    bout_num = next_bout_number(date, red, blue) - 1
    safe_red = safe_filename(red).upper()
    safe_blue = safe_filename(blue).upper()
    bout_name = f"{date}_{safe_red}_vs_{safe_blue}_BOUT{bout_num}"
    rdir = round_dir(red, date, bout_name, round_id)
    return rdir / "coach_notes.csv"


class TagLogManager:
    """Manage CSV logging based on round status."""

    def __init__(
        self,
        path_fn: Callable[[], Path] | None = None,
        status_path: Path | None = None,
        poll_interval: float = 0.5,
    ) -> None:
        self.path_fn = path_fn or _default_log_path
        self.poll_interval = poll_interval
        if status_path is None:
            self._status_func = round_status
        else:

            def _read_path() -> dict:
                try:
                    return json.loads(status_path.read_text())
                except Exception:
                    return {}

            self._status_func = _read_path
        self._writer: DebouncedCsvWriter | None = None
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._watch, daemon=True)
        self._thread.start()

    def _read_status(self) -> str | None:
        try:
            return self._status_func().get("status")
        except Exception:
            return None

    def _watch(self) -> None:
        prev = None
        while not self._stop.is_set():
            status = self._read_status()
            if status == RoundState.LIVE.value and prev != RoundState.LIVE.value:
                path = self.path_fn()
                self._writer = DebouncedCsvWriter(path, FIELDS)
            elif status != RoundState.LIVE.value and self._writer is not None:
                self._writer.close()
                self._writer = None
            prev = status
            self._stop.wait(self.poll_interval)

    def log(self, row: dict) -> bool:
        if self._writer is None:
            return False
        self._writer.write_row(row)
        return True

    def shutdown(self) -> None:
        self._stop.set()
        self._thread.join(timeout=1)
        if self._writer is not None:
            self._writer.close()
            self._writer = None

    @property
    def writer(self) -> DebouncedCsvWriter | None:  # pragma: no cover - simple prop
        return self._writer


tag_log_manager = TagLogManager()


tags_bp = Blueprint("tags", __name__)


@tags_bp.route("/api/tags/log", methods=["POST"])
def tag_press() -> tuple:
    data = request.get_json(silent=True) or {}
    if not all(k in data for k in ["button_id", "state"]):
        return jsonify(status="error", error="missing fields"), 400
    rm_state = get_state()
    row = {
        "ts_iso": datetime.utcnow().isoformat(),
        "button_id": str(data["button_id"]),
        "label": str(data.get("label", "")),
        "color": str(data.get("color", "")),
        "state": str(data["state"]),
        "fighter": str(data.get("fighter", "")),
        "user": str(data.get("user", "")),
    }
    # Access rm_state to derive round/fight info for default path
    _ = rm_state.round, rm_state.bout
    if not tag_log_manager.log(row):
        return jsonify(status="error", error="round not live"), 400
    return jsonify(status="ok")
