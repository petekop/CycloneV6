import asyncio
import importlib
import sys
import types

import pytest

from cyclone_modules.ObsControl import obs_control
from utils import obs_ws

psutil_stub = types.SimpleNamespace(
    process_iter=lambda *a, **k: [],
    NoSuchProcess=Exception,
    AccessDenied=Exception,
)
sys.modules.setdefault("psutil", psutil_stub)


def test_start_and_stop_send_expected_requests():
    """start_obs_recording and stop_obs_recording send proper requests."""

    obs_control.OBS_WS.sent_requests.clear()
    obs_control.start_obs_recording()
    obs_control.stop_obs_recording()

    assert obs_control.OBS_WS.sent_requests == ["StartRecord", "StopRecord"]


def test_start_retry_then_failure(monkeypatch):
    """ws_request retries once on failure then raises."""

    send_calls = 0

    class DummyWS:
        async def send(self, message: str) -> None:  # pragma: no cover - message unused
            nonlocal send_calls
            send_calls += 1
            raise RuntimeError("boom")

        async def recv(self) -> str:  # pragma: no cover - not reached
            return "{}"

    async def dummy_connect(self):
        self._ws = DummyWS()

    monkeypatch.setattr(obs_ws.ObsWs, "_connect", dummy_connect, raising=True)
    monkeypatch.setattr(obs_ws, "WS_AVAILABLE", True, raising=False)

    client = obs_ws.ObsWs()
    with pytest.raises(RuntimeError):
        asyncio.run(client.start_program_recording())

    assert send_calls == 2


def test_source_env_vars_accessible(monkeypatch):
    """SOURCE_* settings load from env and appear in obs_control."""

    monkeypatch.setenv("SOURCE_RECORD_IDS", "1,2,3")
    monkeypatch.setenv("SOURCE_FILTERS", "Scene|Filter")

    from config.settings import reset_settings

    reset_settings()
    importlib.reload(obs_control)

    assert obs_control.SOURCE_RECORD_IDS == "1,2,3"
    assert obs_control.SOURCE_FILTERS == "Scene|Filter"

    monkeypatch.delenv("SOURCE_RECORD_IDS", raising=False)
    monkeypatch.delenv("SOURCE_FILTERS", raising=False)
    reset_settings()
    importlib.reload(obs_control)
