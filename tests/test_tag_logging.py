import csv
import json
import os
import sys
import time
import types
from pathlib import Path

from FightControl.common.states import RoundState
from utils.csv_writer import DebouncedCsvWriter

BASE_DIR = Path(__file__).resolve().parents[1]
os.environ["BASE_DIR"] = str(BASE_DIR)

sys.modules.setdefault("psutil", types.ModuleType("psutil"))


def load_tag_module():
    import importlib.util
    import types

    names = [
        "psutil",
        "matplotlib",
        "matplotlib.pyplot",
        "pandas",
        "websockets",
        "flask",
    ]
    saved = {n: sys.modules.get(n) for n in names}

    sys.modules.setdefault("psutil", types.SimpleNamespace())
    sys.modules.setdefault("matplotlib", types.ModuleType("matplotlib"))
    sys.modules["matplotlib"].use = lambda *a, **k: None
    sys.modules.setdefault("matplotlib.pyplot", types.ModuleType("pyplot"))
    sys.modules.setdefault("pandas", types.ModuleType("pandas"))
    sys.modules.setdefault("websockets", types.ModuleType("websockets"))

    flask_stub = types.ModuleType("flask")

    class DummyBlueprint:
        def __init__(self, *a, **k):
            pass

        def route(self, *a, **k):
            def decorator(func):
                return func

            return decorator

    flask_stub.Blueprint = DummyBlueprint
    flask_stub.jsonify = lambda *a, **k: None
    flask_stub.request = object()
    sys.modules.setdefault("flask", flask_stub)

    fc_pkg = types.ModuleType("FightControl")
    fc_pkg.fight_utils = types.SimpleNamespace(safe_filename=lambda x: x)
    fc_pkg.fighter_paths = types.SimpleNamespace(round_dir=lambda *a, **k: Path("."))
    fc_pkg.round_manager = types.SimpleNamespace(
        get_state=lambda: types.SimpleNamespace(bout={}, round=1),
        round_status=lambda: {},
    )
    sys.modules["FightControl"] = fc_pkg
    sys.modules["FightControl.fight_utils"] = fc_pkg.fight_utils
    sys.modules["FightControl.fighter_paths"] = fc_pkg.fighter_paths
    sys.modules["FightControl.round_manager"] = fc_pkg.round_manager

    spec = importlib.util.spec_from_file_location(
        "tags_module", BASE_DIR / "FightControl" / "routes" / "tags.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    for n, mod in saved.items():
        if mod is None:
            sys.modules.pop(n, None)
        else:
            sys.modules[n] = mod
    for mod in [
        "FightControl",
        "FightControl.fight_utils",
        "FightControl.fighter_paths",
        "FightControl.round_manager",
    ]:
        sys.modules.pop(mod, None)
    return module


def load_tag_module_real_flask():
    import importlib.util
    import types

    names = ["psutil", "matplotlib", "matplotlib.pyplot", "pandas", "websockets"]
    saved = {n: sys.modules.get(n) for n in names}
    sys.modules.setdefault("psutil", types.SimpleNamespace())
    sys.modules.setdefault("matplotlib", types.ModuleType("matplotlib"))
    sys.modules["matplotlib"].use = lambda *a, **k: None
    sys.modules.setdefault("matplotlib.pyplot", types.ModuleType("pyplot"))
    sys.modules.setdefault("pandas", types.ModuleType("pandas"))
    sys.modules.setdefault("websockets", types.ModuleType("websockets"))

    fc_pkg = types.ModuleType("FightControl")
    fc_pkg.fight_utils = types.SimpleNamespace(safe_filename=lambda x: x)
    fc_pkg.fighter_paths = types.SimpleNamespace(round_dir=lambda *a, **k: Path("."))
    fc_pkg.round_manager = types.SimpleNamespace(
        get_state=lambda: types.SimpleNamespace(bout={}, round=1),
        round_status=lambda: {},
    )
    sys.modules["FightControl"] = fc_pkg
    sys.modules["FightControl.fight_utils"] = fc_pkg.fight_utils
    sys.modules["FightControl.fighter_paths"] = fc_pkg.fighter_paths
    sys.modules["FightControl.round_manager"] = fc_pkg.round_manager

    spec = importlib.util.spec_from_file_location(
        "tags_module", BASE_DIR / "FightControl" / "routes" / "tags.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    for n, mod in saved.items():
        if mod is None:
            sys.modules.pop(n, None)
        else:
            sys.modules[n] = mod
    for mod in [
        "FightControl",
        "FightControl.fight_utils",
        "FightControl.fighter_paths",
        "FightControl.round_manager",
    ]:
        sys.modules.pop(mod, None)
    return module


def test_debounced_writer_orders_and_flushes(tmp_path):
    path = tmp_path / "log.csv"
    writer = DebouncedCsvWriter(path, ["n"])
    for i in range(20):
        writer.write({"n": i})
    time.sleep(0.2)
    writer.close()
    with path.open() as f:
        rows = list(csv.DictReader(f))
    assert [int(r["n"]) for r in rows] == list(range(20))
    assert writer.flush_count == 20


def test_tag_log_manager_handles_transitions(tmp_path):
    tags_module = load_tag_module()
    TagLogManager = tags_module.TagLogManager

    status_path = tmp_path / "round_status.json"
    status_path.write_text(json.dumps({"status": RoundState.IDLE.value}))
    log_path = tmp_path / "tags.csv"
    manager = TagLogManager(
        path_fn=lambda: log_path,
        status_path=status_path,
        poll_interval=0.01,
    )
    time.sleep(0.05)
    assert manager.writer is None
    status_path.write_text(json.dumps({"status": RoundState.LIVE.value}))
    time.sleep(0.05)
    assert manager.writer is not None
    for i in range(20):
        row = {
            "ts_iso": str(i),
            "button_id": str(i),
            "label": "L",
            "color": "red",
            "state": "press",
            "fighter": "red",
            "user": "u",
        }
        assert manager.log(row)
    time.sleep(0.2)
    with log_path.open() as f:
        rows = list(csv.DictReader(f))
    assert [r["button_id"] for r in rows] == [str(i) for i in range(20)]
    assert manager.writer.flush_count == 20
    status_path.write_text(json.dumps({"status": RoundState.ENDED.value}))
    time.sleep(0.05)
    assert manager.writer is None or manager.writer._fh.closed
    manager.shutdown()


def test_tag_press_minimal_fields(tmp_path, monkeypatch):
    pytest = __import__("pytest")
    flask = pytest.importorskip("flask")
    tags_module = load_tag_module_real_flask()

    csv_path = tmp_path / "coach_notes.csv"

    class DummyManager:
        def __init__(self):
            self.writer = DebouncedCsvWriter(csv_path, tags_module.FIELDS)

        def log(self, row):
            self.writer.write_row(row)
            return True

    monkeypatch.setattr(tags_module, "tag_log_manager", DummyManager())
    monkeypatch.setattr(
        tags_module, "get_state", lambda: type("S", (), {"round": 1, "bout": {}})()
    )

    app = flask.Flask(__name__)
    app.register_blueprint(tags_module.tags_bp)
    client = app.test_client()

    resp = client.post("/api/tags/log", json={"button_id": "b1", "state": "press"})
    assert resp.status_code == 200

    tags_module.tag_log_manager.writer.close()
    with csv_path.open() as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["button_id"] == "b1"
    assert rows[0]["state"] == "press"
    assert rows[0]["label"] == ""
    assert rows[0]["color"] == ""
    assert rows[0]["fighter"] == ""
    assert rows[0]["user"] == ""
    assert rows[0]["ts_iso"]
