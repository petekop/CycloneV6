import importlib
import json
import os
import sys
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).resolve().parents[1]

pytest.importorskip("flask")


def setup_app(tmp_path):
    os.environ["BASE_DIR"] = str(tmp_path)

    import types

    # Stub heavy optional dependencies required by FightControl modules.
    ws = types.ModuleType("websockets")
    ws.WebSocketClientProtocol = object  # type: ignore[attr-defined]
    ws.connect = lambda *a, **kw: None  # type: ignore
    sys.modules.setdefault("websockets", ws)

    mpl = types.ModuleType("matplotlib")
    mpl.use = lambda *a, **kw: None  # type: ignore
    sys.modules.setdefault("matplotlib", mpl)

    for name in ["matplotlib.pyplot", "pandas", "psutil"]:
        sys.modules.setdefault(name, types.ModuleType(name))

    data_dir = Path(tmp_path) / "FightControl" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    import paths

    importlib.reload(paths)
    import fight_state

    importlib.reload(fight_state)
    import routes.api_routes as api_routes

    importlib.reload(api_routes)
    import FightControl.fighter_paths as fighter_paths

    importlib.reload(fighter_paths)
    from flask import Flask

    app = Flask(__name__)
    app.register_blueprint(api_routes.api_routes)
    app.config["TESTING"] = True
    return app


def _expected_bout_id(date, red, blue):
    from FightControl.fight_utils import safe_filename

    safe_red = safe_filename(red).upper()
    safe_blue = safe_filename(blue).upper()
    return f"{date}_{safe_red}_vs_{safe_blue}_BOUT1"


def test_bout_metadata_written_and_updated(tmp_path):
    app = setup_app(tmp_path)
    client = app.test_client()

    resp = client.post(
        "/enter-fighters",
        data={
            "redName": "Alice",
            "blueName": "Bob",
            "roundType": "3x3",
            "restDuration": "60",
        },
    )
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "success"

    fight_meta = json.loads((tmp_path / "FightControl" / "data" / "current_fight.json").read_text())
    date = fight_meta["fight_date"]
    bout_id = _expected_bout_id(date, "Alice", "Bob")

    from FightControl.fighter_paths import bout_dir

    alice_dir = bout_dir("Alice", date, bout_id)
    bob_dir = bout_dir("Bob", date, bout_id)
    meta = json.loads((alice_dir / "bout.json").read_text())
    assert meta["bout_id"] == bout_id
    assert meta["round_duration"] == 180
    assert meta["rest_duration"] == 60
    assert "max_hr" in meta

    resp = client.post("/api/bout/meta", json={"max_hr": {"red": 200}})
    assert resp.status_code == 200
    updated = json.loads((bob_dir / "bout.json").read_text())
    assert updated["max_hr"]["red"] == 200
