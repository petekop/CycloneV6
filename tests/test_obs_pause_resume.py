"""Tests for pause and resume recording helpers in obs_control."""

import importlib
import json
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Ensure repository root on path

# Remove any pre-loaded obs_control stubs before importing the real module
sys.modules.pop("cyclone_modules.ObsControl.obs_control", None)
sys.modules.pop("cyclone_modules.ObsControl", None)
obs_control = importlib.import_module("cyclone_modules.ObsControl.obs_control")


def _install_mock_websocket(monkeypatch, sent_messages, uri_calls=None):
    """Patch websockets.connect with a dummy context manager."""

    class DummyWS:
        async def send(self, message: str) -> None:
            sent_messages.append(json.loads(message))

        async def recv(self) -> str:  # pragma: no cover - response unused
            return "{}"

    @asynccontextmanager
    async def dummy_connect(_uri: str):
        if uri_calls is not None:
            uri_calls.append(_uri)
        yield DummyWS()

    async def noop_identify(_ws):
        return None

    monkeypatch.setattr(obs_control, "_ws_identify", noop_identify)
    monkeypatch.setattr(obs_control.websockets, "connect", dummy_connect)


def test_pause_and_resume_send_expected_requests(monkeypatch):
    """pause_obs_recording and resume_obs_recording send proper requests."""

    sent = []
    _install_mock_websocket(monkeypatch, sent)

    obs_control.pause_obs_recording()
    obs_control.resume_obs_recording()

    assert [m["d"]["requestType"] for m in sent] == [
        "PauseRecord",
        "ResumeRecord",
    ]


def test_ws_uri_can_be_overridden(monkeypatch):
    """Environment variable overrides the WebSocket URI."""

    sent = []
    uris = []
    monkeypatch.setenv("OBS_WS_URL", "ws://example:5678")
    from config.settings import reset_settings

    reset_settings()
    importlib.reload(obs_control)

    _install_mock_websocket(monkeypatch, sent, uris)

    obs_control.pause_obs_recording()

    expected = os.environ["OBS_WS_URL"].rstrip("/") + "/"
    assert [str(u) for u in uris] == [expected]
