import asyncio
import json
import base64
import hashlib

import pytest

from utils import obs_ws
from utils.obs_ws import ObsWs


class DummyWS:
    def __init__(self, messages):
        self._messages = list(messages)
        self.sent = []
        self.closed = False

    async def send(self, msg):
        self.sent.append(msg)

    async def recv(self):
        return self._messages.pop(0)

    async def close(self):
        self.closed = True


async def _noop(self):
    return None


def _compute_auth(password: str, challenge: str, salt: str) -> str:
    secret = base64.b64encode(
        hashlib.sha256((password + salt).encode()).digest()
    ).decode()
    return base64.b64encode(
        hashlib.sha256((secret + challenge).encode()).digest()
    ).decode()


def test_connect_without_password(monkeypatch):
    hello = json.dumps({"op": 0, "d": {}})
    identified = json.dumps({"op": 2, "d": {}})
    ws = DummyWS([hello, identified])

    async def fake_connect(_uri):
        return ws

    monkeypatch.setattr(obs_ws.websockets, "connect", fake_connect)
    monkeypatch.setattr(obs_ws, "WS_AVAILABLE", True, raising=False)
    monkeypatch.setattr(ObsWs, "_heartbeat", _noop, raising=True)

    obs = ObsWs("ws://example")
    asyncio.run(obs._connect())

    payload = json.loads(ws.sent[0])
    assert payload["op"] == 1
    assert "authentication" not in payload["d"]
    assert "password" not in payload["d"]


def test_connect_with_password(monkeypatch):
    password = "sekret"
    challenge = "challenge123"
    salt = "salt456"
    hello = json.dumps(
        {"op": 0, "d": {"authentication": {"challenge": challenge, "salt": salt}}}
    )
    identified = json.dumps({"op": 2, "d": {}})
    ws = DummyWS([hello, identified])

    async def fake_connect(_uri):
        return ws

    monkeypatch.setattr(obs_ws.websockets, "connect", fake_connect)
    monkeypatch.setattr(obs_ws, "WS_AVAILABLE", True, raising=False)
    monkeypatch.setattr(ObsWs, "_heartbeat", _noop, raising=True)

    obs = ObsWs("ws://example", password=password)
    asyncio.run(obs._connect())

    payload = json.loads(ws.sent[0])
    expected = _compute_auth(password, challenge, salt)
    assert payload["d"]["authentication"] == expected
    assert payload["d"]["password"] == password
