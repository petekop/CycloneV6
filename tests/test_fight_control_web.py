import importlib
import sys
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).resolve().parents[1]

fight_control_web = pytest.importorskip("fight_control_web")


def test_stop_endpoint_returns_200():
    importlib.reload(fight_control_web)
    fight_control_web.app.config["TESTING"] = True
    with fight_control_web.app.test_client() as client:
        resp = client.post("/trigger/stop")
        assert resp.status_code == 200
