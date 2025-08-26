# utils/obs_ws.py
import asyncio
import contextlib
import json
import logging
import uuid
import base64
import hashlib
from typing import Any
from urllib.parse import urlparse

try:  # pragma: no cover - exercised when dependency present
    import websockets

    if not all(hasattr(websockets, attr) for attr in ("connect", "WebSocketClientProtocol", "ConnectionClosed")):
        raise ModuleNotFoundError
except ModuleNotFoundError:  # pragma: no cover - default path in tests
    # Provide a tiny stub so the module can be imported without the optional
    # ``websockets`` dependency. The stub is inserted into ``sys.modules`` so
    # downstream imports succeed in test environments lacking the real package.
    import sys
    import types
    import logging

    class _WSStub:
        async def send(self, *_args, **_kwargs):
            return None

        async def recv(self):
            return "{}"

        async def close(self):
            return None

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_exc):
            return None

    async def _missing_ws(*_args, **_kwargs):  # pragma: no cover - simple stub
        logging.getLogger(__name__).warning(
            "websockets library is not installed; OBS features are disabled"
        )
        return _WSStub()

    _missing_ws._is_stub = True  # type: ignore[attr-defined]

    websockets = types.SimpleNamespace(
        connect=_missing_ws,
        ConnectionClosed=RuntimeError,
        WebSocketClientProtocol=_WSStub,
    )
    sys.modules["websockets"] = websockets

WS_AVAILABLE = not getattr(websockets.connect, "_is_stub", False)

from config.settings import settings

logger = logging.getLogger(__name__)


# Heartbeat / reconnect tuning
HEARTBEAT_SECS = 10.0
BACKOFF_BASE = 1.0
BACKOFF_MAX = 5.0


class ObsWs:
    """Persistent OBS WebSocket client (v5 protocol).

    The client lazily establishes a connection on the first request and
    reuses it for subsequent calls. If the connection drops, a new one is
    created on the next request. All requests use the v5 IDENTIFY handshake
    with ``rpcVersion`` 1. High-level helpers such as ``start_output``,
    ``get_last_output_path``, ``set_text_source``, Source Record controls,
    and track controls are provided.
    """

    def __init__(
        self,
        uri: str | None = None,
        *,
        host: str | None = None,
        port: int | None = None,
        password: str = "",
        timeout: float = 5.0,
    ):
        if uri is None:
            if host is not None or port is not None:
                host = host or "127.0.0.1"
                port = port or 4455
                uri = f"ws://{host}:{port}"
            else:
                uri = str(settings.OBS_WS_URL)
        uri = uri.rstrip("/") + "/"
        parsed = urlparse(uri)
        host = host or parsed.hostname or "127.0.0.1"
        port = port or parsed.port or 4455
        self.uri = uri
        self.host = host
        self.port = port
        self.password = password
        self.timeout = min(timeout, 5.0)
        self._ws: websockets.WebSocketClientProtocol | None = None
        self._lock = asyncio.Lock()
        self._hb_task: asyncio.Task | None = None

    # ------------------------------------------------------------------ #
    # Connection / request plumbing
    # ------------------------------------------------------------------ #
    async def _connect(self) -> None:
        """Open the WebSocket connection and perform the IDENTIFY handshake."""
        if not WS_AVAILABLE:
            return
        ws: websockets.WebSocketClientProtocol | None = None
        try:
            ws = await asyncio.wait_for(websockets.connect(self.uri), self.timeout)
            raw = await asyncio.wait_for(ws.recv(), self.timeout)
            hello = json.loads(raw)
            if hello.get("op") != 0:
                raise RuntimeError("Unexpected HELLO payload from OBS")

            identify_data: dict[str, Any] = {
                "rpcVersion": 1,
                "eventSubscriptions": 1,
            }
            if self.password:
                auth_info = hello.get("d", {}).get("authentication") or {}
                challenge = auth_info.get("challenge", "")
                salt = auth_info.get("salt", "")
                secret = base64.b64encode(
                    hashlib.sha256((self.password + salt).encode()).digest()
                ).decode()
                authentication = base64.b64encode(
                    hashlib.sha256((secret + challenge).encode()).digest()
                ).decode()
                identify_data["authentication"] = authentication
                identify_data["password"] = self.password

            identify = {"op": 1, "d": identify_data}
            await asyncio.wait_for(ws.send(json.dumps(identify)), self.timeout)

            raw = await asyncio.wait_for(ws.recv(), self.timeout)
            identified = json.loads(raw)
            if identified.get("op") != 2:
                raise RuntimeError("OBS IDENTIFY handshake failed")

            self._ws = ws
            if self._hb_task is None or self._hb_task.done():
                self._hb_task = asyncio.create_task(self._heartbeat())
        except TimeoutError as exc:
            if ws is not None:
                with contextlib.suppress(Exception):
                    await ws.close()
            raise TimeoutError("Timed out connecting to OBS WebSocket") from exc
        except Exception:
            if ws is not None:
                with contextlib.suppress(Exception):
                    await ws.close()
            raise

    async def _ensure_connection(self) -> websockets.WebSocketClientProtocol:
        async with self._lock:
            if self._ws is None or getattr(self._ws, "closed", True):
                await self._connect()
        if self._ws is None:
            raise RuntimeError("OBS WebSocket unavailable")
        return self._ws

    async def connect(self) -> None:
        """Explicitly establish the WebSocket connection."""
        if WS_AVAILABLE:
            await self._ensure_connection()

    async def _heartbeat(self) -> None:
        """Periodically ping OBS to keep the connection alive."""
        delay = BACKOFF_BASE
        while True:
            ws = self._ws
            if ws is None or ws.closed:
                await asyncio.sleep(min(delay, BACKOFF_MAX))
                delay = min(delay * 2, BACKOFF_MAX)
                continue
            try:
                pong_waiter = await asyncio.wait_for(ws.ping(), self.timeout)
                await asyncio.wait_for(pong_waiter, self.timeout)
                delay = BACKOFF_BASE
                await asyncio.sleep(HEARTBEAT_SECS)
            except Exception:
                logger.warning("OBS heartbeat failed; resetting connection")
                with contextlib.suppress(Exception):
                    await ws.close()
                self._ws = None
                await asyncio.sleep(min(delay, BACKOFF_MAX))
                delay = min(delay * 2, BACKOFF_MAX)

    async def ws_request(self, request_type: str, request_data: dict[str, Any] | None = None) -> dict:
        """Send a request and return the response payload.

        One reconnect attempt is performed if the socket is closed.
        Raises TimeoutError on request timeout and RuntimeError after retry failure.
        """
        if not WS_AVAILABLE:
            logger.warning("OBS WebSocket unavailable; '%s' skipped", request_type)
            return {}
        for _ in range(2):  # Allow one reconnect attempt
            ws = await self._ensure_connection()
            req_id = uuid.uuid4().hex
            payload: dict[str, Any] = {
                "op": 6,
                "d": {"requestType": request_type, "requestId": req_id},
            }
            if request_data:
                payload["d"]["requestData"] = request_data

            try:
                await asyncio.wait_for(ws.send(json.dumps(payload)), self.timeout)
                while True:
                    raw = await asyncio.wait_for(ws.recv(), self.timeout)
                    data = json.loads(raw)
                    if data.get("op") == 7 and data.get("d", {}).get("requestId") == req_id:
                        return data["d"]
            except TimeoutError as exc:
                logger.error("OBS request '%s' timed out", request_type)
                raise TimeoutError(f"OBS request '{request_type}' timed out") from exc
            except websockets.ConnectionClosed:
                logger.warning("OBS WebSocket connection closed; will reconnect")
                self._ws = None
            except Exception:
                logger.exception("Unexpected OBS WebSocket error; will reconnect")
                self._ws = None

        raise RuntimeError("OBS WebSocket request failed after reconnect")

    # ------------------------------------------------------------------ #
    # Core helpers
    # ------------------------------------------------------------------ #
    async def start_output(self, output_name: str) -> dict:
        """Start an OBS output by name."""
        return await self.ws_request("StartOutput", {"outputName": output_name})

    async def stop_output(self, output_name: str) -> dict:
        """Stop an OBS output by name."""
        return await self.ws_request("StopOutput", {"outputName": output_name})

    async def start_program_recording(self) -> dict:
        """Start the program recording in OBS."""
        return await self.ws_request("StartRecord")

    async def stop_program_recording(self) -> dict:
        """Stop the program recording in OBS."""
        return await self.ws_request("StopRecord")

    # ------------------------------------------------------------------ #
    # Track recording helpers (from codex branch)
    # NOTE: These assume a plugin or requests named StartTrack/StopTrack exist.
    # ------------------------------------------------------------------ #
    async def start_track(self, track_id: str) -> dict:
        """Start recording for a specific track."""
        return await self.ws_request("StartTrack", {"trackId": track_id})

    async def stop_track(self, track_id: str) -> dict:
        """Stop recording for a specific track."""
        return await self.ws_request("StopTrack", {"trackId": track_id})

    async def get_track_status(self, track_id: str) -> dict:
        """Return status information for a track recording."""
        return await self.ws_request("GetTrackStatus", {"trackId": track_id})

    # ------------------------------------------------------------------ #
    # Source Record vendor calls (kept from main)
    # ------------------------------------------------------------------ #
    async def start_source_record(self, source_record_id: int) -> dict:
        """Start a Source Record by its numeric ID."""
        data = {
            "vendorName": "source-record",
            "requestType": "start",
            "requestData": {"sourceRecordID": source_record_id},
        }
        return await self.ws_request("CallVendorRequest", data)

    async def stop_source_record(self, source_record_id: int) -> dict:
        """Stop a Source Record by its numeric ID."""
        data = {
            "vendorName": "source-record",
            "requestType": "stop",
            "requestData": {"sourceRecordID": source_record_id},
        }
        return await self.ws_request("CallVendorRequest", data)

    # ------------------------------------------------------------------ #
    # Overlay helpers (single definition; removed duplicate)
    # ------------------------------------------------------------------ #
    async def set_text_source(self, source: str, text: str) -> dict:
        """
        Update the text of a string input in OBS (overlay without polling).

        Works for both `text_gdiplus` and `freetype2_text` inputs via
        SetInputSettings. Connection errors bubble up to the caller.
        """
        return await self.ws_request(
            "SetInputSettings",
            {
                "inputName": source,
                "inputSettings": {"text": text},
                "overlay": True,
            },
        )

    # ------------------------------------------------------------------ #
    # Queries
    # ------------------------------------------------------------------ #
    async def get_outputs_list(self) -> list[dict[str, Any]]:
        """Return the list of configured outputs."""
        resp = await self.ws_request("GetOutputsList")
        return resp.get("responseData", {}).get("outputs", [])

    async def get_last_output_path(self, output_name: str) -> str:
        """Return the file path of the most recent recording for an output."""
        resp = await self.ws_request("GetLastOutputPath", {"outputName": output_name})
        return resp.get("responseData", {}).get("outputPath", "")

    # ------------------------------------------------------------------ #
    # Teardown
    # ------------------------------------------------------------------ #
    async def close(self) -> None:
        """Close the WebSocket connection if open."""
        if self._hb_task is not None:
            self._hb_task.cancel()
            with contextlib.suppress(Exception):
                await self._hb_task
            self._hb_task = None
        if self._ws is not None and not self._ws.closed:
            await self._ws.close()
        self._ws = None
