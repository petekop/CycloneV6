import pytest

pytest.importorskip("flask")
from flask import Flask

import routes.hr as hr_module


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(hr_module, "BASE_DIR", tmp_path)
    app = Flask(__name__)
    app.register_blueprint(hr_module.hr_bp, url_prefix="/api/hr")
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client, tmp_path


def test_hr_status_endpoint(client):
    client_app, base = client
    live = base / "FightControl" / "live_data"
    live.mkdir(parents=True)
    (live / "red_status.txt").write_text("CONNECTED")
    (live / "blue_status.txt").write_text("ERROR")
    data = client_app.get("/api/hr/status").get_json()
    assert data == {"red": "CONNECTED", "blue": "ERROR"}
