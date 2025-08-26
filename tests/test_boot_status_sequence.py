import pytest

pytest.importorskip("flask")
from flask import Flask

from boot_state import get_boot_state, set_boot_state
from routes.boot_status import boot_status_bp, current_status


@pytest.mark.parametrize(
    "sequence",
    [
        [
            (
                {
                    "hr_daemon": "WAIT",
                    "mediamtx": "WAIT",
                    "obs": "WAIT",
                },
                0,
                False,
            ),
            (
                {
                    "hr_daemon": "READY",
                    "mediamtx": "READY",
                    "obs": "WAIT",
                },
                66,
                False,
            ),
            (
                {
                    "hr_daemon": "READY",
                    "mediamtx": "READY",
                    "obs": "READY",
                },
                100,
                True,
            ),
        ],
    ],
)
def test_progress_sequence(sequence):
    for services, expected_progress, expected_ready in sequence:
        data = current_status(services)
        assert data["progress"] == expected_progress
        assert data["ready"] is expected_ready


def test_status_endpoint_recalculates_progress(tmp_path, monkeypatch):
    """Mutating ``boot_state`` between requests updates progress and ready."""

    # Ensure boot state starts clean
    set_boot_state({})

    # Patch paths used by status routes to avoid writing to the repo
    monkeypatch.setattr("routes.boot_status.BASE_DIR", tmp_path, raising=False)
    monkeypatch.setattr("routes.boot_status.STATE_DIR", tmp_path / "state", raising=False)

    app = Flask(__name__)
    app.register_blueprint(boot_status_bp, url_prefix="/api/boot")
    client = app.test_client()

    # Initial status should reflect default WAIT state
    resp = client.get("/api/boot/status")
    data = resp.get_json()
    assert data["progress"] == 0
    assert data["ready"] is False

    # Mark two services ready and ensure progress updates
    boot_state = get_boot_state()
    boot_state["services"]["hr_daemon"] = "READY"
    boot_state["services"]["mediamtx"] = "READY"
    resp = client.get("/api/boot/status")
    data = resp.get_json()
    assert data["progress"] == 66
    assert data["ready"] is False

    # Mark final service ready and ensure ready flag becomes True
    boot_state["services"]["obs"] = "READY"
    resp = client.get("/api/boot/status")
    data = resp.get_json()
    assert data["progress"] == 100
    assert data["ready"] is True
