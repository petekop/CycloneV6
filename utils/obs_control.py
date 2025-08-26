"""Thin wrapper around obsws_python.ReqClient for recording controls."""

from __future__ import annotations

import logging
import os
from threading import Lock
from typing import Callable

try:  # pragma: no cover - optional dependency
    from obsws_python import ReqClient  # type: ignore
except Exception:  # pragma: no cover - fallback when library missing
    ReqClient = None  # type: ignore

try:  # pragma: no cover - optional dependency
    import pyautogui  # type: ignore
except Exception:  # pragma: no cover - library may not be installed in tests
    pyautogui = None  # type: ignore

logger = logging.getLogger(__name__)


HOTKEYS: dict[str, tuple[str, ...]] = {
    "start_record": ("f9",),
    "stop_record": ("f9",),
    "pause_record": ("f10",),
    "resume_record": ("f10",),
}


class ObsController:
    """Synchronous OBS controller using :class:`obsws_python.ReqClient`.

    The controller lazily establishes a connection on first use and reuses the
    ``ReqClient`` instance for subsequent requests. All public methods are
    thread-safe and fall back to sending configured hotkeys when WebSocket
    communication fails.
    """

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        password: str | None = None,
        timeout: float | None = None,
    ) -> None:
        self.host = host or os.getenv("OBS_WS_HOST", "127.0.0.1")
        self.port = port or int(os.getenv("OBS_WS_PORT", "4455"))
        self.password = password if password is not None else os.getenv("OBS_WS_PASSWORD", "")
        self.timeout = timeout if timeout is not None else float(os.getenv("OBS_CONNECT_TIMEOUT", "1.0"))
        self._client: ReqClient | None = None
        self._lock = Lock()

    # ------------------------------------------------------------------ #
    # Connection handling
    # ------------------------------------------------------------------ #
    def _connect(self) -> None:
        """Establish the WebSocket connection if not already connected."""
        if self._client is not None:
            return
        if ReqClient is None:  # pragma: no cover - library absent
            raise RuntimeError("obsws_python library is not installed")
        logger.info("Connecting to OBS at %s:%s", self.host, self.port)
        try:
            self._client = ReqClient(
                host=self.host,
                port=self.port,
                password=self.password,
                timeout=self.timeout,
            )
            logger.info("OBS connection established")
        except Exception:
            logger.exception("OBS connection failed")
            self._client = None
            raise

    def _with_client(self, func: Callable[[ReqClient], None]) -> None:
        """Execute ``func`` with a connected ``ReqClient`` instance.

        ``func`` should be a callable accepting the client. Any exceptions raised
        will trigger the hotkey fallback for the associated action.
        """

        with self._lock:
            try:
                self._connect()
                assert self._client is not None  # for type checkers
                func(self._client)
            except Exception:
                raise

    # ------------------------------------------------------------------ #
    # Hotkey fallback
    # ------------------------------------------------------------------ #
    def _send_hotkey(self, action: str) -> None:
        combo = HOTKEYS.get(action)
        if combo is None:
            logger.warning("No hotkey configured for action %s", action)
            return
        if pyautogui is None:
            logger.warning("pyautogui not available; cannot send hotkey for %s", action)
            return
        try:
            pyautogui.hotkey(*combo)
            logger.info("Sent hotkey %s for %s", "+".join(combo), action)
        except Exception:  # pragma: no cover - best effort
            logger.exception("Failed to send hotkey for %s", action)

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def start_record(self) -> None:
        """Start OBS recording, falling back to hotkey on failure."""
        try:
            self._with_client(lambda c: c.start_record())
        except Exception:
            logger.exception("start_record failed; using hotkey fallback")
            self._send_hotkey("start_record")

    def pause_record(self) -> None:
        """Pause OBS recording, falling back to hotkey on failure."""
        try:
            self._with_client(lambda c: c.pause_record())
        except Exception:
            logger.exception("pause_record failed; using hotkey fallback")
            self._send_hotkey("pause_record")

    def resume_record(self) -> None:
        """Resume OBS recording, falling back to hotkey on failure."""
        try:
            self._with_client(lambda c: c.resume_record())
        except Exception:
            logger.exception("resume_record failed; using hotkey fallback")
            self._send_hotkey("resume_record")

    def stop_record(self) -> None:
        """Stop OBS recording, falling back to hotkey on failure."""
        try:
            self._with_client(lambda c: c.stop_record())
        except Exception:
            logger.exception("stop_record failed; using hotkey fallback")
            self._send_hotkey("stop_record")

# Global controller instance used throughout the application
obs = ObsController()

__all__ = ["ObsController", "obs"]
