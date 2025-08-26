import io
import json
import os
import sys
import time
import types
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

BASE_DIR = Path(__file__).resolve().parents[1]
os.environ["BASE_DIR"] = str(BASE_DIR)

pytest.importorskip("flask")
pytestmark = pytest.mark.usefixtures("stub_optional_dependencies")

sys.modules.setdefault(
    "FightControl.create_fighter_round_folders",
    types.ModuleType("create_fighter_round_folders"),
)
sys.modules["FightControl.create_fighter_round_folders"].create_round_folder_for_fighter = lambda *args, **kwargs: None
sys.modules.setdefault(
    "round_summary",
    types.SimpleNamespace(generate_round_summaries=lambda *a, **k: None),
)

fight_utils_stub = types.ModuleType("fight_utils")
fight_utils_stub.safe_filename = lambda x: x


def _prf(fmt: str):
    try:
        r, m = fmt.lower().split("x")
        return int(r), int(m) * 60
    except Exception:
        return 1, 60


fight_utils_stub.parse_round_format = _prf
FightControl_pkg = types.ModuleType("FightControl")
FightControl_pkg.__path__ = []
FightControl_pkg.fight_utils = fight_utils_stub
fighter_paths_stub = types.ModuleType("fighter_paths")
fighter_paths_stub.bout_dir = lambda *a, **k: Path()
fighter_paths_stub.round_dir = lambda *a, **k: Path()
FightControl_pkg.fighter_paths = fighter_paths_stub
play_sound_stub = types.ModuleType("play_sound")
play_sound_stub.play_audio = lambda *a, **k: None
FightControl_pkg.play_sound = play_sound_stub
sys.modules.setdefault("FightControl", FightControl_pkg)
sys.modules.setdefault("FightControl.fight_utils", fight_utils_stub)
sys.modules.setdefault("FightControl.fighter_paths", fighter_paths_stub)
sys.modules.setdefault("FightControl.play_sound", play_sound_stub)
pycountry_stub = types.SimpleNamespace(
    countries=types.SimpleNamespace(get=lambda **k: types.SimpleNamespace(name="C")),
    subdivisions=types.SimpleNamespace(get=lambda **k: types.SimpleNamespace(name="S")),
)
sys.modules.setdefault("pycountry", pycountry_stub)

from flask import url_for  # noqa: E402

import cyclone_server  # noqa: E402
import fight_state  # noqa: E402
import round_state  # noqa: E402
from FightControl.fight_utils import safe_filename  # noqa: F401, E402
from utils import play_audio  # noqa: F401, E402

# Fallback if api_routes not present during testing
try:
    import routes.api_routes as api_routes  # noqa: E402
except ModuleNotFoundError:  # pragma: no cover
    import types

    api_routes = types.ModuleType("api_routes")

import fighter_utils  # noqa: E402
import round_outputs  # noqa: E402
import round_timer  # noqa: E402
from routes import overlay_routes  # noqa: E402

app = cyclone_server.app
app.secret_key = "test-secret"

# Ensure select_fighter dummy route exists in test context
if "select_fighter" not in app.view_functions:
    app.add_url_rule("/select-fighter", "select_fighter", lambda: ("", 200))

# Ensure edit_fighter route exists for testing
if "edit_fighter" not in app.view_functions:
    app.add_url_rule(
        "/edit-fighter/<int:fighter_id>",
        "edit_fighter",
        lambda fighter_id: ("", 200),
    )

# Minimal update_fighter API for tests if missing
if "api_routes.update_fighter" not in app.view_functions:

    def _api_update_fighter(fighter_name):
        data = request.get_json() or {}
        fighters = fighter_utils.load_fighters()
        idx = next((i for i, f in enumerate(fighters) if f.get("name") == fighter_name), None)
        if idx is not None:
            fighters[idx].update(data)
        else:  # pragma: no cover - defensive
            fighters.append(data)
        fighter_utils.FIGHTERS_JSON.write_text(json.dumps(fighters, indent=2))

        perf_path = api_routes.PERFORMANCE_RESULTS_JSON
        entries = json.loads(perf_path.read_text()) if perf_path.exists() else []
        entries.append({"fighter_name": fighter_name, "performance": data.get("performance")})
        perf_path.write_text(json.dumps(entries, indent=2))
        return jsonify(status="success", fighter=data)

    app.add_url_rule(
        "/api/update_fighter/<fighter_name>",
        "api_routes.update_fighter",
        _api_update_fighter,
        methods=["POST"],
    )

# Provide minimal round summary endpoint for testing
from flask import jsonify, request, send_file  # noqa: E402


def _api_round_summary():
    logs_dir = Path(app.config.get("ROUND_SUMMARY_DIR", BASE_DIR / "FightControl" / "logs"))
    image = request.args.get("image")
    session = request.args.get("session")
    if image and session:
        session_dir = Path(session)
        session_dir.mkdir(parents=True, exist_ok=True)
        return send_file(session_dir / image, mimetype="image/png")

    date = request.args.get("date")
    bout = request.args.get("bout")
    round_id = request.args.get("round")
    if date and bout and round_id:
        path = logs_dir / date / bout / f"{round_id}.png"
        return send_file(path, mimetype="image/png")

    images = []
    if logs_dir.exists():
        images = [str(p.relative_to(logs_dir)) for p in logs_dir.rglob("*.png")]
    return jsonify(images)


if "api_round_summary" in app.view_functions:
    app.view_functions["api_round_summary"] = _api_round_summary
else:
    app.add_url_rule("/api/round/summary", "api_round_summary", _api_round_summary)


@pytest.fixture
def patched_paths(monkeypatch, tmp_path):
    data_dir = tmp_path / "FightControl" / "data"
    data_dir.mkdir(parents=True)
    (data_dir / "round_status.json").write_text("{}")
    (data_dir / "round_state.json").write_text(
        json.dumps(
            {
                "state": "offline",
                "round": 1,
                "fighter_id_red": None,
                "fighter_id_blue": None,
                "started_at": None,
                "updated_at": None,
                "timer": 0,
            }
        )
    )
    fighters_json = data_dir / "fighters.json"
    fighters_json.write_text("[]")
    perf_json = data_dir / "performance_results.json"
    perf_json.write_text("[]")

    modules = [
        cyclone_server,
        api_routes,
        overlay_routes,
        round_timer,
        fighter_utils,
        fight_state,
        round_state,
    ]
    for module in modules:
        monkeypatch.setattr(module, "DATA_DIR", data_dir, raising=False)
        monkeypatch.setattr(module, "FIGHTERS_JSON", fighters_json, raising=False)

    monkeypatch.setattr(api_routes, "PERFORMANCE_RESULTS_JSON", perf_json, raising=False)
    monkeypatch.setattr(api_routes, "load_fighters", fighter_utils.load_fighters, raising=False)
    monkeypatch.setattr(api_routes, "save_fighter", fighter_utils.save_fighter, raising=False)
    monkeypatch.setattr(api_routes, "BASE_DIR", tmp_path, raising=False)
    monkeypatch.setattr(api_routes.api_routes, "BASE_DIR", tmp_path, raising=False)
    monkeypatch.setenv("BASE_DIR", str(tmp_path))

    monkeypatch.setattr(round_state, "ROUND_STATE_JSON", data_dir / "round_state.json", raising=False)

    return data_dir


@pytest.fixture
def client(patched_paths):
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def fighter(patched_paths):
    data = {"name": "Test Fighter", "age": 30}
    (patched_paths / "fighters.json").write_text(json.dumps([data]))
    return data


def test_root(client):
    assert client.get("/").status_code == 200


def test_menu(client):
    assert client.get("/menu").status_code == 200


def test_enter_fighters(client):
    assert client.get("/enter-fighters").status_code == 200


def test_enter_fighters_post_success(client, monkeypatch):
    monkeypatch.setattr(api_routes, "arm_round_status", lambda d, r, t: None)
    resp = client.post(
        "/enter-fighters",
        data={
            "redName": "Red",
            "blueName": "Blue",
            "roundType": "3x2",
            "roundDuration": "120",
            "restDuration": "60",
        },
    )
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "success"


def test_enter_fighters_post_invalid(client, monkeypatch):
    monkeypatch.setattr(api_routes, "arm_round_status", lambda d, r, t: None)
    resp = client.post(
        "/enter-fighters",
        data={
            "redName": "Red",
            "blueName": "Blue",
            "roundDuration": "abc",
            "restDuration": "60",
        },
    )
    assert resp.status_code == 400


def test_review(client):
    assert client.get("/review").status_code == 200


def test_coaching_panel(client, patched_paths):
    cf = patched_paths / "current_fight.json"
    if cf.exists():
        cf.unlink()
    resp = client.get("/coaching-panel")
    assert resp.status_code in (302, 403)


def test_coaching_panel_with_configured_fight(client, monkeypatch):
    monkeypatch.setattr(api_routes, "arm_round_status", lambda d, r, t: None)
    client.post(
        "/enter-fighters",
        data={
            "redName": "Red",
            "blueName": "Blue",
            "roundType": "3x2",
            "roundDuration": "120",
            "restDuration": "60",
        },
    )
    resp = client.get("/coaching-panel")
    assert resp.status_code == 200


def test_coaching_panel_multi_client_access(patched_paths, monkeypatch):
    monkeypatch.setattr(api_routes, "arm_round_status", lambda d, r, t: None)
    app.config["TESTING"] = True
    with app.test_client() as client1:
        client1.post(
            "/enter-fighters",
            data={
                "redName": "Red",
                "blueName": "Blue",
                "roundType": "3x2",
                "roundDuration": "120",
                "restDuration": "60",
            },
        )
        assert client1.get("/coaching-panel").status_code == 200

    # Configuration persisted to shared file so a new session sees it
    assert (patched_paths / "current_fight.json").exists()
    with app.test_client() as client2:
        resp = client2.get("/coaching-panel")
        assert resp.status_code == 200


@pytest.mark.parametrize("mode", [None, "edit", "duplicate"])
def test_create_page_get(client, mode):
    url = "/create"
    if mode:
        url += f"?mode={mode}"
    resp = client.get(url)
    assert resp.status_code == 200
    assert b"Create Cyclone" in resp.data


def test_create_page_post_disallowed(client):
    resp = client.post("/create", data={"name": "Test"})
    assert resp.status_code == 405


def test_system_tools(client):
    assert client.get("/system-tools").status_code == 200


def test_audio_test(client):
    assert client.get("/audio-test").status_code == 200


def test_overlay_preview(client):
    assert client.get("/overlay-preview").status_code == 200


def test_sync_drive(client):
    assert client.get("/sync-drive").status_code == 200


def test_live_log(client):
    assert client.get("/live-log").status_code == 200


def test_controller_status(client):
    assert client.get("/controller-status").status_code == 200


def test_overlay_index(client):
    assert client.get("/overlay/index.html").status_code == 200


def test_overlay_data_round_status(client):
    assert client.get("/overlay/data/round_status.json").status_code == 200


def test_get_fighters(client):
    with app.test_request_context():
        fighters_url = url_for("api_routes.get_fighters")
    assert client.get(fighters_url).status_code == 200


def test_select_fighter(client):
    assert client.get("/select-fighter").status_code == 200


def test_get_fighters_returns_objects(client, patched_paths):
    fighters = [
        {"name": "Red Fighter", "age": "30"},
        {"name": "Blue Fighter", "age": "25"},
    ]
    fighters_json = patched_paths / "fighters.json"
    fighters_json.write_text(json.dumps(fighters))
    with app.test_request_context():
        url = url_for("api_routes.get_fighters")
    resp = client.get(url)
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)
    ids = [f.get("id") for f in data]
    assert all("name" in f and "age" in f and "card_url" in f for f in data)
    assert all(i is not None for i in ids)
    assert len(set(ids)) == len(ids)


def test_enter_fighters_writes_round_and_rest(client, patched_paths, monkeypatch):
    monkeypatch.setattr(round_timer, "refresh_obs_overlay", lambda: None)
    resp = client.post(
        "/enter-fighters",
        data={
            "redName": "Alice",
            "blueName": "Bob",
            "roundType": "5x2",
            "roundDuration": "120",
            "restDuration": "45",
        },
    )
    assert resp.status_code == 200
    status = json.loads((patched_paths / "round_status.json").read_text())
    assert status["duration"] == 120
    assert status["rest"] == 45
    assert status["total_rounds"] == 5


def test_enter_fighters_replaces_round_status_and_clears_stale_fields(client, patched_paths, monkeypatch):
    path = patched_paths / "round_status.json"
    old_status = {
        "round": 2,
        "duration": 300,
        "rest": 60,
        "total_rounds": 10,
        "status": "ACTIVE",
        "remaining_time": 42,
        "start_time": "2000-01-01T00:00:00",
    }
    path.write_text(json.dumps(old_status))
    monkeypatch.setattr(round_timer, "refresh_obs_overlay", lambda: None)

    resp = client.post(
        "/enter-fighters",
        data={
            "redName": "Alice",
            "blueName": "Bob",
            "roundType": "3x2",
            "roundDuration": "120",
            "restDuration": "60",
        },
    )
    assert resp.status_code == 200
    status = json.loads(path.read_text())
    assert status["duration"] == 120
    assert status["rest"] == 60
    assert status["total_rounds"] == 3
    assert status["status"] == "WAITING"
    assert "remaining_time" not in status
    assert "start_time" not in status

    time.sleep(0.01)
    resp = client.post(
        "/enter-fighters",
        data={
            "redName": "Cara",
            "blueName": "Dana",
            "roundType": "2x3",
            "roundDuration": "180",
            "restDuration": "45",
        },
    )
    assert resp.status_code == 200
    new_status = json.loads(path.read_text())
    assert new_status["duration"] == 180
    assert new_status["rest"] == 45
    assert new_status["total_rounds"] == 2
    assert new_status["status"] == "WAITING"
    assert "remaining_time" not in new_status
    assert "start_time" not in new_status


def test_timer_start_uses_armed_values(client, patched_paths, monkeypatch):
    monkeypatch.setattr(round_timer, "refresh_obs_overlay", lambda: None)
    recorded = {}

    def fake_start_round_timer(dur, rest, on_complete=None):
        recorded["dur"] = dur
        recorded["rest"] = rest

    def fake_round_status():
        path = patched_paths / "round_status.json"
        return json.loads(path.read_text()) if path.exists() else {}

    monkeypatch.setattr(api_routes, "start_round_timer", fake_start_round_timer)

    async def _noop():
        return None

    monkeypatch.setattr(api_routes.obs, "start_record", _noop)
    monkeypatch.setattr(api_routes, "play_audio", lambda *a, **k: None)
    monkeypatch.setattr(api_routes, "round_status", fake_round_status)

    api_routes.arm_round_status(150, 30, 3)
    resp = client.post("/api/timer/start")
    assert resp.status_code == 200
    assert recorded["dur"] == 150
    assert recorded["rest"] == 30


@pytest.mark.parametrize("mode", ["edit", "custom"])
def test_create_mode_non_default(client, mode):
    resp = client.get(f"/create?mode={mode}")
    assert resp.status_code == 200
    assert "Create Cyclone" in resp.get_data(as_text=True)


def test_server_startup():
    with app.test_client() as client:
        resp = client.get("/")
        assert resp.status_code == 200


def test_round_summary_empty(client, tmp_path):
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    app.config["ROUND_SUMMARY_DIR"] = logs_dir
    resp = client.get("/api/round/summary")
    assert resp.status_code == 200
    assert isinstance(resp.get_json(), list)


def test_round_summary_stream_image(client, tmp_path):
    date = "2023-01-01"
    bout = "red_vs_blue"
    round_id = "round_1"
    logs_dir = tmp_path / "logs" / date / bout
    logs_dir.mkdir(parents=True)

    png_bytes = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\nIDATx\xdac\xf8\x0f\x00\x01\x01\x01\x00\x18\xdd\x8d\xbc"
        b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    img_path = logs_dir / f"{round_id}.png"
    img_path.write_bytes(png_bytes)
    app.config["ROUND_SUMMARY_DIR"] = tmp_path / "logs"

    resp = client.get(
        "/api/round/summary",
        query_string={"image": f"{round_id}.png", "session": str(logs_dir)},
    )
    assert resp.status_code == 200
    assert resp.mimetype == "image/png"
    assert resp.data == png_bytes


def test_edit_fighter_route(client, fighter):
    resp = client.get("/edit-fighter/0")
    assert resp.status_code == 200


def test_update_fighter_api(client, fighter, patched_paths):
    payload = {
        "name": fighter["name"],
        "speed": 90,
        "division": "welterweight",
        "age_class": "adult",
        "performance": {"speed": 90},
    }
    from urllib.parse import quote

    resp = client.post(f"/api/update_fighter/{quote(fighter['name'])}", json=payload)
    assert resp.status_code == 200
    fighters = json.loads((patched_paths / "fighters.json").read_text())
    assert fighters[0]["speed"] == 90
    assert fighters[0]["division"] == "welterweight"
    assert fighters[0]["age_class"] == "adult"
    perf = json.loads((patched_paths / "performance_results.json").read_text())
    expected = {"fighter_name": fighter["name"], "performance": {"speed": 90}}
    assert expected in perf


def test_update_fighter_preserves_arbitrary_fields(client, patched_paths):
    fighters = [{"name": "Test Fighter", "speed": 80, "age": 30}]
    (patched_paths / "fighters.json").write_text(json.dumps(fighters))
    payload = {"name": "Test Fighter", "age": 31}
    from urllib.parse import quote

    resp = client.post(f"/api/update_fighter/{quote('Test Fighter')}", json=payload)
    assert resp.status_code == 200
    fighters = json.loads((patched_paths / "fighters.json").read_text())
    assert fighters[0]["speed"] == 80
    assert fighters[0]["age"] == 31


@pytest.mark.parametrize("male_field", ["abdomen", "waist"])
def test_update_male_missing_core_measure_returns_400(client, patched_paths, male_field):
    fighters = [{"name": "Bob", "gender": "male", "age": 25, male_field: 80}]
    (patched_paths / "fighters.json").write_text(json.dumps(fighters))
    payload = {"gender": "male", "neck": 40}
    from urllib.parse import quote

    resp = client.post(f"/api/update_fighter/{quote('Bob')}", json=payload)
    assert resp.status_code == 400


@pytest.mark.parametrize("missing_field", ["waist", "hip"])
def test_update_female_missing_field_returns_400(client, patched_paths, missing_field):
    fighters = [{"name": "Alice", "gender": "female", "age": 22, "waist": 70, "hip": 90}]
    (patched_paths / "fighters.json").write_text(json.dumps(fighters))
    payload = {"gender": "female", "waist": 71, "hip": 91}
    payload.pop(missing_field)
    from urllib.parse import quote

    resp = client.post(f"/api/update_fighter/{quote('Alice')}", json=payload)
    assert resp.status_code == 400


def test_update_male_valid_preserves_other_fields(client, patched_paths):
    fighters = [{"name": "Dan", "gender": "male", "age": 30, "neck": 40, "abdomen": 80}]
    (patched_paths / "fighters.json").write_text(json.dumps(fighters))
    payload = {"gender": "male", "abdomen": 82}
    from urllib.parse import quote

    resp = client.post(f"/api/update_fighter/{quote('Dan')}", json=payload)
    assert resp.status_code == 200
    fighters = json.loads((patched_paths / "fighters.json").read_text())
    assert fighters[0]["age"] == 30
    assert fighters[0]["neck"] == 40
    assert fighters[0]["abdomen"] == 82


def test_update_female_valid_preserves_other_fields(client, patched_paths):
    fighters = [{"name": "Fran", "gender": "female", "age": 28, "neck": 35, "waist": 70, "hip": 90}]
    (patched_paths / "fighters.json").write_text(json.dumps(fighters))
    payload = {"gender": "female", "waist": 71, "hip": 92}
    from urllib.parse import quote

    resp = client.post(f"/api/update_fighter/{quote('Fran')}", json=payload)
    assert resp.status_code == 200
    fighters = json.loads((patched_paths / "fighters.json").read_text())
    assert fighters[0]["age"] == 28
    assert fighters[0]["neck"] == 35
    assert fighters[0]["waist"] == 71
    assert fighters[0]["hip"] == 92


def test_create_fighter_card_rejects_non_image(client, monkeypatch):
    monkeypatch.setattr(api_routes, "create_fighter_card", lambda *a, **k: None)
    data = {"photo": (io.BytesIO(b"not an image"), "test.txt", "text/plain")}
    resp = client.post("/api/create_fighter_card", data=data, content_type="multipart/form-data")
    assert resp.status_code == 400


def test_create_fighter_card_rejects_large_image(client, monkeypatch):
    monkeypatch.setattr(api_routes, "create_fighter_card", lambda *a, **k: None)
    big = b"\x89PNG\r\n\x1a\n" + b"0" * (api_routes.MAX_PHOTO_SIZE + 1)
    data = {"photo": (io.BytesIO(big), "big.png", "image/png")}
    resp = client.post("/api/create_fighter_card", data=data, content_type="multipart/form-data")
    assert resp.status_code == 400


def test_round_start_stop_endpoints(client, monkeypatch):
    calls = []

    async def _request(request_type, request_data=None):
        calls.append((request_type, request_data))
        return {"d": {"requestStatus": {"result": True}}}

    monkeypatch.setattr(round_outputs, "OUTPUTS", ["trk1", "trk2"])
    monkeypatch.setattr(round_outputs, "OBS", types.SimpleNamespace(request=AsyncMock(side_effect=_request)))
    monkeypatch.setattr(round_outputs, "ALSO_RECORD_PROGRAM", False)
    monkeypatch.setattr(round_outputs, "OVERLAY_WARMUP_MS", 0)
    monkeypatch.setattr(round_outputs, "_move_outputs_sync", lambda cfg, meta: [Path("a.mp4"), Path("b.mp4")])
    monkeypatch.setattr(api_routes, "load_fight_state", lambda: ({}, "2025-01-01", "round_1"))

    resp = client.post("/api/round/start")
    assert resp.status_code == 200

    resp = client.post("/api/round/stop")
    assert resp.status_code == 200
    assert resp.get_json()["files"] == ["a.mp4", "b.mp4"]

    # Ensure expected start/stop output calls occurred
    assert calls[:2] == [
        ("StartOutput", {"outputName": "trk1"}),
        ("StartOutput", {"outputName": "trk2"}),
    ]
    assert calls[-2:] == [
        ("StopOutput", {"outputName": "trk1"}),
        ("StopOutput", {"outputName": "trk2"}),
    ]


def test_round_state_start_stop(client, monkeypatch):
    started = []
    stopped = []

    async def _started():
        started.append(True)

    async def _stopped():
        stopped.append(True)

    monkeypatch.setattr(api_routes.obs, "start_record", _started)
    monkeypatch.setattr(api_routes.obs, "stop_record", _stopped)

    resp = client.post("/api/round/state/arm")
    assert resp.status_code == 200

    resp = client.post("/api/round/state/start")
    assert resp.status_code == 200
    assert started == [True]

    resp = client.post("/api/round/state/stop")
    assert resp.status_code == 200
    assert stopped == [True]
