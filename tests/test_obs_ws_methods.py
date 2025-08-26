import asyncio
import sys
import types
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).resolve().parents[1]

sys.modules.setdefault(
    "psutil",
    types.SimpleNamespace(
        process_iter=lambda *a, **k: [],
        NoSuchProcess=Exception,
        AccessDenied=Exception,
    ),
)

from utils.obs_ws import ObsWs


def test_get_last_output_path(monkeypatch):
    called = {}

    async def fake_ws_request(self, request_type, request_data=None):
        called["request_type"] = request_type
        called["request_data"] = request_data
        return {"responseData": {"outputPath": "/tmp/last.mkv"}}

    obs = ObsWs("ws://example")
    monkeypatch.setattr(ObsWs, "ws_request", fake_ws_request)

    path = asyncio.run(obs.get_last_output_path("cam"))

    assert path == "/tmp/last.mkv"
    assert called == {
        "request_type": "GetLastOutputPath",
        "request_data": {"outputName": "cam"},
    }


def test_set_text_source(monkeypatch):
    called = {}

    async def fake_ws_request(self, request_type, request_data=None):
        called["request_type"] = request_type
        called["request_data"] = request_data
        return {"ok": True}

    obs = ObsWs("ws://example")
    monkeypatch.setattr(ObsWs, "ws_request", fake_ws_request)

    resp = asyncio.run(obs.set_text_source("score", "1-0"))

    assert resp == {"ok": True}
    assert called["request_type"] == "SetInputSettings"
    assert called["request_data"] == {
        "inputName": "score",
        "inputSettings": {"text": "1-0"},
        "overlay": True,
    }
