import asyncio
import importlib
import logging
import sys
import types
from pathlib import Path

import pytest


class BoomError(RuntimeError):
    pass


def test_retry_async(monkeypatch, caplog):
    # Provide lightweight stubs so the FightControl package can be imported
    # without executing its heavy initialisation logic.
    fc_stub = types.ModuleType("FightControl")
    fc_stub.__path__ = [str(Path(__file__).resolve().parents[1] / "FightControl")]
    sys.modules["FightControl"] = fc_stub
    rm_stub = types.ModuleType("FightControl.round_manager")
    rm_stub.start_round_sequence = lambda *a, **k: None
    rm_stub.round_status = lambda *a, **k: {}
    sys.modules["FightControl.round_manager"] = rm_stub

    backoff = importlib.import_module("FightControl.heartrate_mon.backoff")
    retry_async = backoff.retry_async

    attempts = {"count": 0}

    async def op():
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise BoomError("fail")
        return "ok"

    sleeps: list[float] = []

    async def fake_sleep(d):
        sleeps.append(d)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    statuses: list[str] = []

    logger = logging.getLogger("test")

    async def runner():
        return await retry_async(
            op,
            status_update=statuses.append,
            logger=logger,
            max_attempts=5,
        )

    with caplog.at_level(logging.WARNING):
        result = asyncio.run(runner())

    assert result == "ok"
    assert sleeps == [5, 10]
    assert statuses == [
        "ERROR",
        "RETRYING in 5s",
        "ERROR",
        "RETRYING in 10s",
        "SUCCESS",
    ]
    assert "Attempt 1 failed" in caplog.text
    assert "Attempt 2 failed" in caplog.text
