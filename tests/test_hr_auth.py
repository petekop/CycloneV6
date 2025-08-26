import pytest

pytest.importorskip("flask")
pytest.importorskip("flask_socketio")

from flask import Flask, jsonify, request
from flask_socketio import Namespace, SocketIO

TOKEN = "secret-token"


def _token_from_request() -> str | None:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth.split()[1]
    return request.args.get("auth.token")


class HRNamespace(Namespace):
    def on_connect(self):  # pragma: no cover
        if request.args.get("auth.token") != TOKEN:
            return False
        return None


def create_app():
    app = Flask(__name__)
    socketio = SocketIO(app, async_mode="threading", logger=False, engineio_logger=False)

    @app.route("/api/hr/ping")
    def ping():
        if _token_from_request() != TOKEN:
            return "", 401
        return jsonify(status="ok")

    @app.route("/api/hr/<sensor>", methods=["POST"])
    def sensor(sensor: str):
        if _token_from_request() != TOKEN:
            return "", 401
        return jsonify(sensor=sensor)

    socketio.on_namespace(HRNamespace("/ws/hr"))
    return app, socketio


@pytest.fixture
def app_socketio():
    return create_app()


@pytest.fixture
def client(app_socketio):
    app, _ = app_socketio
    with app.test_client() as client:
        yield client


def test_hr_ping_auth_header(client):
    resp = client.get("/api/hr/ping", headers={"Authorization": "Bearer bad"})
    assert resp.status_code == 401


def test_hr_ping_auth_query(client):
    resp = client.get("/api/hr/ping?auth.token=bad")
    assert resp.status_code == 401


def test_hr_sensor_auth_header(client):
    resp = client.post("/api/hr/red", json={}, headers={"Authorization": "Bearer bad"})
    assert resp.status_code == 401


def test_hr_sensor_auth_query(client):
    resp = client.post("/api/hr/red?auth.token=bad", json={})
    assert resp.status_code == 401


def test_ws_hr_rejects_invalid_token(app_socketio):
    app, socketio = app_socketio
    sio_client = socketio.test_client(app, namespace="/ws/hr", query_string="auth.token=bad")
    assert not sio_client.is_connected("/ws/hr")
