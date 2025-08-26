import asyncio
import importlib
import sys

import pytest

# Ensure we import the real module (not a cached stub)
sys.modules.pop("cyclone_modules.ObsControl.obs_control", None)
sys.modules.pop("cyclone_modules.ObsControl", None)
obs_control = importlib.import_module("cyclone_modules.ObsControl.obs_control")


@pytest.mark.parametrize(
    "func_name, async_name, args",
    [
        ("start_obs_recording", "start_program_recording", []),
        ("stop_obs_recording", "stop_program_recording", []),
        ("start_all_source_records", "_start_all_source_records", []),
        ("stop_all_source_records", "_stop_all_source_records", []),
        ("start_source_record", "start_source_record_ws", [123]),
        ("stop_source_record", "stop_source_record_ws", [123]),
        ("pause_obs_recording", "pause_record_ws", []),
        ("resume_obs_recording", "resume_record_ws", []),
        ("start_obs_track", "start_track", ["cam1"]),
        ("stop_obs_track", "stop_track", ["cam1"]),
        ("refresh_obs_overlay", "refresh_overlay_ws", ["foo"]),
        ("quit_obs", "quit_obs_ws", []),
    ],
)
def test_wrappers_run_outside_event_loop(monkeypatch, func_name, async_name, args):
    called = False

    async def dummy(*_a, **_k):
        nonlocal called
        called = True

    if func_name in ("start_obs_recording", "stop_obs_recording"):
        monkeypatch.setattr(obs_control.OBS_WS, async_name, dummy, raising=True)
    else:
        monkeypatch.setattr(obs_control, async_name, dummy, raising=True)

    func = getattr(obs_control, func_name)
    func(*args)
    assert called


@pytest.mark.parametrize(
    "func_name, async_name, args",
    [
        ("start_obs_recording", "start_program_recording", []),
        ("stop_obs_recording", "stop_program_recording", []),
        ("start_all_source_records", "_start_all_source_records", []),
        ("stop_all_source_records", "_stop_all_source_records", []),
        ("start_source_record", "start_source_record_ws", [123]),
        ("stop_source_record", "stop_source_record_ws", [123]),
        ("pause_obs_recording", "pause_record_ws", []),
        ("resume_obs_recording", "resume_record_ws", []),
        ("start_obs_track", "start_track", ["cam1"]),
        ("stop_obs_track", "stop_track", ["cam1"]),
        ("refresh_obs_overlay", "refresh_overlay_ws", ["foo"]),
        ("quit_obs", "quit_obs_ws", []),
    ],
)
def test_wrappers_return_task_inside_event_loop(monkeypatch, func_name, async_name, args):
    called = False

    async def dummy(*_a, **_k):
        nonlocal called
        called = True

    if func_name in ("start_obs_recording", "stop_obs_recording"):
        monkeypatch.setattr(obs_control.OBS_WS, async_name, dummy, raising=True)
    else:
        monkeypatch.setattr(obs_control, async_name, dummy, raising=True)

    func = getattr(obs_control, func_name)

    async def runner():
        task = func(*args)
        assert isinstance(task, asyncio.Task)
        await task
        assert called

    asyncio.run(runner())


def test_start_and_stop_source_records_order(monkeypatch):
    calls: list[str] = []

    async def start_sources():
        calls.append("sources")

    async def start_program():
        calls.append("program")

    monkeypatch.setattr(obs_control, "start_all_source_records", start_sources, raising=True)
    monkeypatch.setattr(obs_control.OBS_WS, "start_program_recording", start_program, raising=True)

    obs_control.start_obs_recording()
    assert calls == ["sources", "program"]

    calls.clear()

    async def stop_program():
        calls.append("program")

    async def stop_sources():
        calls.append("sources")

    monkeypatch.setattr(obs_control.OBS_WS, "stop_program_recording", stop_program, raising=True)
    monkeypatch.setattr(obs_control, "stop_all_source_records", stop_sources, raising=True)

    obs_control.stop_obs_recording()
    assert calls == ["program", "sources"]


def test_all_source_records_helpers_use_settings(monkeypatch):
    calls: list[tuple] = []

    async def start_id(rid):
        calls.append(("start_id", rid))

    async def stop_id(rid):
        calls.append(("stop_id", rid))

    async def set_filter(scene, filt, enabled):
        calls.append((scene, filt, enabled))

    monkeypatch.setattr(obs_control, "start_source_record_ws", start_id, raising=True)
    monkeypatch.setattr(obs_control, "stop_source_record_ws", stop_id, raising=True)
    monkeypatch.setattr(obs_control, "set_source_filter_enabled_ws", set_filter, raising=True)
    monkeypatch.setattr(obs_control.settings, "SOURCE_RECORD_IDS", [1], raising=False)
    monkeypatch.setattr(obs_control.settings, "SOURCE_FILTERS", [("Scene", "Filter")], raising=False)

    asyncio.run(obs_control._start_all_source_records())
    asyncio.run(obs_control._stop_all_source_records())

    assert calls == [
        ("start_id", 1),
        ("Scene", "Filter", True),
        ("stop_id", 1),
        ("Scene", "Filter", False),
    ]


def test_check_obs_sync_inside_and_out(monkeypatch):
    async def ok(*_args, **_kwargs):
        return None

    monkeypatch.setattr(obs_control, "check_obs_connection", ok)
    # Outside loop
    assert obs_control.check_obs_sync() is True

    async def inside_ok():
        task = obs_control.check_obs_sync()
        assert await task is True

    asyncio.run(inside_ok())

    async def fail(*_args, **_kwargs):
        raise RuntimeError

    monkeypatch.setattr(obs_control, "check_obs_connection", fail)
    assert obs_control.check_obs_sync() is False

    async def inside_fail():
        assert await obs_control.check_obs_sync() is False

    asyncio.run(inside_fail())


# Re-import the module to avoid caching side effects for subsequent tests
sys.modules.pop("cyclone_modules.ObsControl.obs_control", None)
sys.modules.pop("cyclone_modules.ObsControl", None)
obs_control = importlib.import_module("cyclone_modules.ObsControl.obs_control")


def test_check_obs_sync_times_out_returns_false(monkeypatch):
    async def slow(*_args, **_kwargs):
        # Sleep longer than the timeout the test will pass to check_obs_sync
        await asyncio.sleep(1)

    # Force the internal connectivity probe to exceed timeout
    monkeypatch.setattr(obs_control, "check_obs_connection", slow, raising=True)

    # Synchronous wrapper should coerce timeout to False
    assert obs_control.check_obs_sync(timeout=0.05) is False

    # And the async path (if exposed) should do the same under the hood
    async def inside_timeout():
        assert await obs_control.check_obs_sync(timeout=0.05) is False

    asyncio.run(inside_timeout())


def test_stop_track_polls_for_path(monkeypatch):
    """stop_track should poll until OBS reports the output path."""

    class DummyObs:
        def __init__(self):
            self.calls = 0

        async def start_track(self, track_id):
            pass

        async def stop_track(self, track_id):
            pass

        async def get_track_status(self, track_id):
            self.calls += 1
            if self.calls < 3:
                return {"responseData": {"outputPath": ""}}
            return {"responseData": {"outputPath": f"/tmp/{track_id}.mkv"}}

    dummy = DummyObs()
    # Replace the global OBS client used inside stop_track with our dummy
    monkeypatch.setattr(obs_control, "OBS_WS", dummy, raising=True)

    path = asyncio.run(obs_control.stop_track("cam1"))
    assert path == "/tmp/cam1.mkv"
    assert dummy.calls >= 3
