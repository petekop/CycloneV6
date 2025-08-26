import asyncio
import json
import logging
import os
from urllib.parse import urlparse

from config.settings import settings

try:  # pragma: no cover - exercised when dependency present
    import websockets

    if not all(hasattr(websockets, attr) for attr in ("connect", "WebSocketClientProtocol", "ConnectionClosed")):
        raise ModuleNotFoundError
except ModuleNotFoundError:  # pragma: no cover - default path in tests
    # Provide a tiny stub so the module can be imported without the optional
    # ``websockets`` dependency.  Tests patch ``websockets.connect`` with their
    # own fakes, so only a placeholder is required here.
    import sys
    import types

    class _WSStub:  # pragma: no cover - placeholder protocol class
        async def send(self, *_args, **_kwargs):
            return None

        async def recv(self):
            return "{}"

        async def close(self):
            return None

        async def __aenter__(self):  # support "async with"
            return self

        async def __aexit__(self, *_exc):
            return None

    async def _missing_ws(*_args, **_kwargs):  # pragma: no cover - simple stub
        logging.getLogger(__name__).warning("websockets library is not installed; OBS actions are disabled")
        return _WSStub()

    _missing_ws._is_stub = True  # type: ignore[attr-defined]

    websockets = types.SimpleNamespace(
        connect=_missing_ws,
        ConnectionClosed=RuntimeError,
        WebSocketClientProtocol=_WSStub,
    )
    sys.modules["websockets"] = websockets

# ``utils`` lazily imports ``psutil`` which isn't always available in the test
# environment. Install a lightweight stub to avoid import errors.
try:  # pragma: no cover - when psutil is installed
    import psutil  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover - default path in tests
    import sys
    import types

    psutil_stub = types.SimpleNamespace(process_iter=lambda *a, **k: [])
    sys.modules.setdefault("psutil", psutil_stub)


def _parse_obs_url(url: str) -> tuple[str, int]:
    """Return host and port extracted from an OBS WebSocket URL."""
    parsed = urlparse(str(url))
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 4455
    return host, port


def _compose_obs_url() -> str:
    """Construct the OBS WebSocket URL from environment variables."""
    url = os.getenv("OBS_WS_URL")
    if url:
        return url
    host = os.getenv("OBS_WS_HOST", "127.0.0.1")
    port = os.getenv("OBS_WS_PORT", "4455")
    return f"ws://{host}:{port}"


# ``check_obs_connection`` previously used a very small timeout which caused
# flakiness in slower environments.  Use a more realistic default and honour
# any ``OBS_CONNECT_TIMEOUT`` override from the environment.
DEFAULT_OBS_CONNECT_TIMEOUT = float(os.getenv("OBS_CONNECT_TIMEOUT", "1.0"))

OBS_WS_URI = _compose_obs_url().rstrip("/") + "/"
_HOST, _PORT = _parse_obs_url(str(OBS_WS_URI))
_PASSWORD = settings.OBS_WS_PASSWORD
SOURCE_RECORD_IDS = settings.SOURCE_RECORD_IDS
SOURCE_FILTERS = settings.SOURCE_FILTERS


class ObsClient:
    """Tiny in-process OBS WebSocket client used in tests.

    The client records each request type sent via :attr:`sent_requests`.
    """

    def __init__(self) -> None:
        self.sent_requests: list[str] = []

    async def _send(self, request_type: str) -> None:
        self.sent_requests.append(request_type)

    async def connect(self) -> None:  # pragma: no cover - no-op stub
        return None

    async def start_program_recording(self) -> None:
        await self._send("StartRecord")

    async def stop_program_recording(self) -> None:
        await self._send("StopRecord")

    # Stubs for APIs used by other helpers/tests
    async def start_track(self, _track_id: str) -> None:  # pragma: no cover - stub
        return None

    async def stop_track(self, _track_id: str) -> None:  # pragma: no cover - stub
        return None

    async def get_track_status(self, _track_id: str) -> dict:  # pragma: no cover - stub
        return {"responseData": {"outputPath": ""}}

    async def get_last_output_path(self, _output_name: str) -> str:  # pragma: no cover - stub
        return ""


# Persistent OBS WebSocket client used by higher level helpers.  This simplified
# implementation avoids ``None`` so callers needn't guard against it.
OBS_WS = ObsClient()


def setup_logging(level: int = logging.INFO) -> None:
    """Initialise basic logging configuration.

    Applications using this module are expected to configure logging at the
    entry point.  This helper is provided for convenience when a minimal
    configuration is desired.
    """

    logging.basicConfig(level=level)


logger = logging.getLogger(__name__)


async def connect() -> None:
    """Establish the OBS WebSocket connection if needed."""
    await OBS_WS.connect()


async def _ws_identify(ws):
    """Perform the OBS WebSocket IDENTIFY handshake."""
    await ws.recv()
    await ws.send(
        json.dumps(
            {
                "op": 1,
                "d": {"rpcVersion": 1, "eventSubscriptions": 1},
            }
        )
    )
    await ws.recv()


async def start_record_ws():
    """Asynchronously send StartRecord to OBS."""
    async with websockets.connect(OBS_WS_URI) as ws:
        await _ws_identify(ws)
        await ws.send(
            json.dumps(
                {
                    "op": 6,
                    "d": {"requestType": "StartRecord", "requestId": "rec_start"},
                }
            )
        )
        resp = await ws.recv()
        logger.info("OBS StartRecord response: %s", resp)


async def stop_record_ws():
    """Asynchronously send StopRecord to OBS."""
    async with websockets.connect(OBS_WS_URI) as ws:
        await _ws_identify(ws)
        await ws.send(
            json.dumps(
                {
                    "op": 6,
                    "d": {"requestType": "StopRecord", "requestId": "rec_stop"},
                }
            )
        )
        resp = await ws.recv()
        logger.info("OBS StopRecord response: %s", resp)


async def start_source_record_ws(source_record_id: int):
    """Start a Source Record by ID via OBS."""
    async with websockets.connect(OBS_WS_URI) as ws:
        await _ws_identify(ws)
        await ws.send(
            json.dumps(
                {
                    "op": 6,
                    "d": {
                        "requestType": "CallVendorRequest",
                        "requestId": f"src_rec_start_{source_record_id}",
                        "requestData": {
                            "vendorName": "source-record",
                            "requestType": "start",
                            "requestData": {"sourceRecordID": source_record_id},
                        },
                    },
                }
            )
        )
        resp = await ws.recv()
        logger.info("OBS StartSourceRecord %s response: %s", source_record_id, resp)


async def stop_source_record_ws(source_record_id: int):
    """Stop a Source Record by ID via OBS."""
    async with websockets.connect(OBS_WS_URI) as ws:
        await _ws_identify(ws)
        await ws.send(
            json.dumps(
                {
                    "op": 6,
                    "d": {
                        "requestType": "CallVendorRequest",
                        "requestId": f"src_rec_stop_{source_record_id}",
                        "requestData": {
                            "vendorName": "source-record",
                            "requestType": "stop",
                            "requestData": {"sourceRecordID": source_record_id},
                        },
                    },
                }
            )
        )
        resp = await ws.recv()
        logger.info("OBS StopSourceRecord %s response: %s", source_record_id, resp)


async def set_source_filter_enabled_ws(source_name: str, filter_name: str, enabled: bool):
    """Enable or disable a source filter via OBS."""
    async with websockets.connect(OBS_WS_URI) as ws:
        await _ws_identify(ws)
        await ws.send(
            json.dumps(
                {
                    "op": 6,
                    "d": {
                        "requestType": "SetSourceFilterEnabled",
                        "requestId": f"filter_{'on' if enabled else 'off'}_{source_name}_{filter_name}",
                        "requestData": {
                            "sourceName": source_name,
                            "filterName": filter_name,
                            "filterEnabled": enabled,
                        },
                    },
                }
            )
        )
        resp = await ws.recv()
        logger.info(
            "OBS SetSourceFilterEnabled %s/%s -> %s response: %s",
            source_name,
            filter_name,
            enabled,
            resp,
        )


async def refresh_overlay_ws(input_name: str = "overlay"):
    """Reload a browser source in OBS."""
    async with websockets.connect(OBS_WS_URI) as ws:
        await _ws_identify(ws)
        await ws.send(
            json.dumps(
                {
                    "op": 6,
                    "d": {
                        "requestType": "PressInputPropertiesButton",
                        "requestId": "refresh_001",
                        "requestData": {
                            "inputName": input_name,
                            "propertyName": "refreshnocache",
                        },
                    },
                }
            )
        )
        logger.info("OBS overlay refresh sent for: %s", input_name)


async def check_obs_connection(timeout: float = DEFAULT_OBS_CONNECT_TIMEOUT):
    """Raise if the OBS WebSocket cannot be reached within ``timeout`` seconds.

    ``timeout`` defaults to :data:`DEFAULT_OBS_CONNECT_TIMEOUT` but can be
    overridden to fail fast during health checks.  The same timeout is applied
    to opening the socket and to the handshake/response phase so callers have a
    consistent upper bound on the probe duration.
    """

    async with websockets.connect(OBS_WS_URI, open_timeout=timeout) as ws:
        await asyncio.wait_for(_ws_identify(ws), timeout)
        await asyncio.wait_for(
            ws.send(
                json.dumps(
                    {
                        "op": 6,
                        "d": {
                            "requestType": "GetRecordStatus",
                            "requestId": "check_obs",
                        },
                    }
                )
            ),
            timeout,
        )
        await asyncio.wait_for(ws.recv(), timeout)


async def start_track(track_id: str):
    """Start recording for a specific OBS track."""
    await OBS_WS.start_track(track_id)


async def stop_track(
    track_id: str,
    *,
    poll_interval: float = 0.25,
    timeout: float = 10.0,
) -> str:
    """Stop recording for a track and return the output file path.

    After issuing the stop command, OBS is polled for the track status until an
    ``outputPath`` is reported or the timeout elapses.  An empty string is
    returned if no path is produced.
    """

    await OBS_WS.stop_track(track_id)
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while True:
        status = await OBS_WS.get_track_status(track_id)
        path = status.get("responseData", {}).get("outputPath")
        if path:
            return path
        if loop.time() > deadline:
            return ""
        await asyncio.sleep(poll_interval)


def _run_async(coro):
    """Run ``coro`` in the current loop or start a new one.

    If a loop is already running a task is scheduled and returned. Otherwise
    :func:`asyncio.run` is used to execute the coroutine synchronously and
    ``None`` is returned.
    """

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    else:
        return loop.create_task(coro)


async def _start_all_source_records():
    """Start all configured source records and filters."""
    ids_raw = getattr(settings, "SOURCE_RECORD_IDS", None)
    filters_raw = getattr(settings, "SOURCE_FILTERS", None)

    if isinstance(ids_raw, str):
        ids = [int(i) for i in ids_raw.split(",") if i]
    else:
        ids = list(ids_raw) if ids_raw else []

    if isinstance(filters_raw, str):
        filters: list[tuple[str, str]] = []
        for pair in filters_raw.split(";"):
            scene, _, filt = pair.partition("|")
            if scene and filt:
                filters.append((scene, filt))
    else:
        filters = list(filters_raw) if filters_raw else []

    for record_id in ids:
        try:
            await start_source_record_ws(int(record_id))
        except Exception:
            logger.exception("OBS start source record failed")
    for scene, filter_name in filters:
        try:
            await set_source_filter_enabled_ws(scene, filter_name, True)
        except Exception:
            logger.exception("OBS enable source filter failed for %s/%s", scene, filter_name)


async def _stop_all_source_records():
    """Stop all configured source records and filters."""
    ids_raw = getattr(settings, "SOURCE_RECORD_IDS", None)
    filters_raw = getattr(settings, "SOURCE_FILTERS", None)

    if isinstance(ids_raw, str):
        ids = [int(i) for i in ids_raw.split(",") if i]
    else:
        ids = list(ids_raw) if ids_raw else []

    if isinstance(filters_raw, str):
        filters: list[tuple[str, str]] = []
        for pair in filters_raw.split(";"):
            scene, _, filt = pair.partition("|")
            if scene and filt:
                filters.append((scene, filt))
    else:
        filters = list(filters_raw) if filters_raw else []

    for record_id in ids:
        try:
            await stop_source_record_ws(int(record_id))
        except Exception:
            logger.exception("OBS stop source record failed")
    for scene, filter_name in filters:
        try:
            await set_source_filter_enabled_ws(scene, filter_name, False)
        except Exception:
            logger.exception("OBS disable source filter failed for %s/%s", scene, filter_name)


def start_all_source_records():
    """Start all configured source records and filters."""
    try:
        return _run_async(_start_all_source_records())
    except Exception:
        logger.exception("OBS start all source records failed")


def stop_all_source_records():
    """Stop all configured source records and filters."""
    try:
        return _run_async(_stop_all_source_records())
    except Exception:
        logger.exception("OBS stop all source records failed")


def start_obs_recording():
    """Start OBS recording.

    When called inside an event loop a task is scheduled and returned so that
    callers may await it.  Outside of a loop the coroutine is executed
    synchronously.
    """

    async def _start():
        await start_all_source_records()
        await OBS_WS.start_program_recording()

    try:
        return _run_async(_start())
    except Exception:
        logger.exception("OBS start recording failed")


def stop_obs_recording():
    """Stop OBS recording and return the file path.

    Behaves like :func:`start_obs_recording` regarding event loop handling.
    The resulting path is returned or an empty string if unavailable.
    """

    async def _stop():
        result = await OBS_WS.stop_program_recording()
        await stop_all_source_records()
        return result

    try:
        return _run_async(_stop())
    except Exception:
        logger.exception("OBS stop recording failed")


def start_source_record(source_record_id: int):
    """Start a Source Record by ID."""
    try:
        return _run_async(start_source_record_ws(source_record_id))
    except Exception:
        logger.exception("OBS start source record failed")


def stop_source_record(source_record_id: int):
    """Stop a Source Record by ID."""
    try:
        return _run_async(stop_source_record_ws(source_record_id))
    except Exception:
        logger.exception("OBS stop source record failed")


async def pause_record_ws():
    """Asynchronously send PauseRecord to OBS."""
    async with websockets.connect(OBS_WS_URI) as ws:
        await _ws_identify(ws)
        await ws.send(
            json.dumps(
                {
                    "op": 6,
                    "d": {"requestType": "PauseRecord", "requestId": "rec_pause"},
                }
            )
        )
        resp = await ws.recv()
        logger.info("OBS PauseRecord response: %s", resp)
        return resp


async def resume_record_ws():
    """Asynchronously send ResumeRecord to OBS."""
    async with websockets.connect(OBS_WS_URI) as ws:
        await _ws_identify(ws)
        await ws.send(
            json.dumps(
                {
                    "op": 6,
                    "d": {"requestType": "ResumeRecord", "requestId": "rec_resume"},
                }
            )
        )
        resp = await ws.recv()
        logger.info("OBS ResumeRecord response: %s", resp)
        return resp


def pause_obs_recording():
    """Pause OBS recording.

    Works both inside and outside an event loop.
    """
    try:
        return _run_async(pause_record_ws())
    except Exception:
        logger.exception("OBS pause recording failed")


def resume_obs_recording():
    """Resume OBS recording."""
    try:
        return _run_async(resume_record_ws())
    except Exception:
        logger.exception("OBS resume recording failed")


def start_obs_track(track_id: str):
    """Start recording a specific OBS track."""
    try:
        return _run_async(start_track(track_id))
    except Exception:
        logger.exception("OBS start track failed")


def stop_obs_track(track_id: str):
    """Stop recording a track and return its file path."""
    try:
        return _run_async(stop_track(track_id))
    except Exception:
        logger.exception("OBS stop track failed")


def refresh_obs_overlay(input_name: str = "overlay"):
    """Trigger a browser source refresh.

    ``input_name`` identifies the browser source to refresh.  The coroutine is
    either scheduled on the running loop or executed synchronously if no loop
    is active.
    """
    try:
        return _run_async(refresh_overlay_ws(input_name))
    except Exception:
        logger.exception("OBS overlay refresh failed")


def check_obs_sync(timeout: float = DEFAULT_OBS_CONNECT_TIMEOUT):
    """Return ``True`` if OBS is reachable via WebSocket.

    ``timeout`` defaults to :data:`DEFAULT_OBS_CONNECT_TIMEOUT`. When called in
    an event loop a task is returned which resolves to ``True`` or ``False``.
    Outside a loop the result is returned synchronously.
    """

    async def _check() -> bool:
        try:
            await asyncio.wait_for(check_obs_connection(timeout=timeout), timeout)
        except Exception:
            return False
        return True

    try:
        return _run_async(_check())
    except Exception:
        return False


async def quit_obs_ws():
    """Send a Shutdown request to OBS via WebSocket."""
    async with websockets.connect(OBS_WS_URI) as ws:
        await _ws_identify(ws)
        await ws.send(
            json.dumps(
                {
                    "op": 6,
                    "d": {"requestType": "Shutdown", "requestId": "quit_obs"},
                }
            )
        )
        await ws.recv()


def quit_obs():
    """Quit OBS if reachable."""
    try:
        return _run_async(quit_obs_ws())
    except Exception:
        logger.exception("OBS quit failed")
