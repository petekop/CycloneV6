import sys
import types
from pathlib import Path

import pytest

pytest.importorskip("flask")

import routes.health as health_module  # noqa: E402

# Ensure repository root on import path
BASE_DIR = Path(__file__).resolve().parents[1]

# Stubs for heavy modules
sys.modules.setdefault(
    "FightControl.create_fighter_round_folders",
    types.SimpleNamespace(create_round_folder_for_fighter=lambda *a, **k: None),
)
sys.modules.setdefault(
    "FightControl.fight_utils",
    types.SimpleNamespace(safe_filename=lambda x: x, parse_round_format=lambda *a, **k: None),
)
sys.modules.setdefault(
    "fight_state",
    types.SimpleNamespace(
        load_fight_state=lambda *a, **k: {},
        get_session_dir=lambda *a, **k: Path("."),
        fighter_session_dir=lambda *a, **k: Path("."),
    ),
)
sys.modules.setdefault(
    "FightControl.fighter_paths",
    types.SimpleNamespace(bout_dir=lambda *a, **k: Path("."), round_dir=lambda *a, **k: Path(".")),
)
sys.modules.setdefault(
    "FightControl.round_manager",
    types.SimpleNamespace(
        RoundManager=None,
        RoundState=object,
        start_round_sequence=lambda *a, **k: None,
    ),
)
sys.modules.setdefault("FightControl.play_sound", types.SimpleNamespace(play_audio=lambda *a, **k: None))
sys.modules.setdefault("round_summary", types.SimpleNamespace(generate_round_summaries=lambda *a, **k: []))

# Stub OBS control package
obs_control_stub = sys.modules.get("cyclone_modules.ObsControl.obs_control")
if obs_control_stub is None:
    obs_control_stub = types.ModuleType("obs_control_stub")
    obs_control_stub.start_obs_recording = lambda *a, **k: None
    obs_control_stub.stop_obs_recording = lambda *a, **k: None
    obs_control_stub.refresh_obs_overlay = lambda *a, **k: None
    obs_control_stub.check_obs_connection = lambda *a, **k: True
    obs_control_stub.check_obs_sync = lambda *a, **k: True
    sys.modules["cyclone_modules.ObsControl.obs_control"] = obs_control_stub

import cyclone_server  # noqa: E402


@pytest.fixture
def client():
    cyclone_server.app.config["TESTING"] = True
    with cyclone_server.app.test_client() as client:
        yield client


def test_health_obs_connected(monkeypatch, client):
    monkeypatch.setattr(
        health_module,
        "obs_health",
        types.SimpleNamespace(healthy=lambda *a, **k: False),
    )
    monkeypatch.setattr(health_module, "check_media_mtx", lambda *a, **k: True)
    monkeypatch.setattr(health_module, "is_process_running", lambda name: True)
    monkeypatch.setattr(health_module.psutil, "disk_usage", lambda path: types.SimpleNamespace(free=0), raising=False)
    monkeypatch.setattr(health_module.psutil, "cpu_percent", lambda interval=None: 0, raising=False)
    monkeypatch.setattr(health_module.psutil, "virtual_memory", lambda: types.SimpleNamespace(percent=0), raising=False)
    resp = client.get("/api/health")
    data = resp.get_json()
    assert data["obs_connected"] is False
