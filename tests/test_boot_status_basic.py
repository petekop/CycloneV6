from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

from routes import boot_status

pytest.importorskip("flask")

BASE_DIR = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------------------
# Lightweight stubs for optional/heavy imports
# ---------------------------------------------------------------------------


def _stub(name, obj):
    sys.modules.setdefault(name, obj)


_stub(
    "FightControl.create_fighter_round_folders",
    types.SimpleNamespace(create_round_folder_for_fighter=lambda *a, **k: None),
)
_stub(
    "FightControl.fight_utils",
    types.SimpleNamespace(safe_filename=lambda x: x, parse_round_format=lambda *a, **k: None),
)
_stub(
    "fight_state",
    types.SimpleNamespace(
        load_fight_state=lambda *a, **k: {},
        get_session_dir=lambda *a, **k: Path("."),
        fighter_session_dir=lambda *a, **k: Path("."),
    ),
)
_stub(
    "FightControl.round_manager",
    types.SimpleNamespace(
        start_round_sequence=lambda *a, **k: None,
        get_state=lambda *a, **k: {},
    ),
)
_stub(
    "round_timer",
    types.SimpleNamespace(
        start_round_timer=lambda *a, **k: None,
        pause_round=lambda *a, **k: None,
        resume_round=lambda *a, **k: None,
        arm_round_status=lambda *a, **k: None,
        init_bout_metadata=lambda *a, **k: None,
        update_bout_metadata=lambda *a, **k: None,
    ),
)

from flask import Blueprint  # noqa: E402

_stub("routes.api_routes", types.SimpleNamespace(api_routes=Blueprint("api", __name__)))
_stub("routes.rounds", types.SimpleNamespace(rounds_bp=Blueprint("rounds", __name__)))

# OBS control stub
obs_control_stub = types.SimpleNamespace(
    DEFAULT_OBS_CONNECT_TIMEOUT=0.05,
    check_obs_sync=lambda *a, **k: False,
)
sys.modules["cyclone_modules.ObsControl.obs_control"] = obs_control_stub

import cyclone_server  # noqa: E402


@pytest.fixture
def client(tmp_path):
    cyclone_server.app.config["TESTING"] = True
    cyclone_server.app.config["STATE_DIR"] = tmp_path
    tmp_path.mkdir(parents=True, exist_ok=True)
    with cyclone_server.app.test_client() as c:
        yield c


def test_boot_status_basic(client):
    resp = client.get("/api/boot/status")
    assert resp.status_code == 200
    data = resp.get_json()
    expected_services = {
        "hr_daemon": "WAIT",
        "mediamtx": "WAIT",
        "obs": "READY",
    }
    assert data["services"] == expected_services
    assert data["progress"] == 33
    assert data["ready"] is False
    assert "message" in data


def test_refresh_state_preserves_error(monkeypatch):
    """``_refresh_state`` keeps ERROR flags while resetting other services."""

    # Avoid filesystem writes during the test
    monkeypatch.setattr(boot_status, "_write_state", lambda state: None)

    state = {
        "services": {"hr_daemon": "ERROR", "mediamtx": "WAIT", "obs": "READY"},
        "progress": 0,
        "ready": False,
        "message": "",
        "started": {"hr_daemon": True, "mediamtx": False, "obs": False},
    }

    refreshed = boot_status._refresh_state(state)

    assert refreshed["services"] == {
        "hr_daemon": "ERROR",
        "mediamtx": "WAIT",
        "obs": "READY",
    }
    assert refreshed["progress"] == 66
    assert refreshed["ready"] is False
    assert refreshed["started"] == {"hr_daemon": True, "mediamtx": False, "obs": False}
