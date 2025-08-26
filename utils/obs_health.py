"""Lightweight OBS TCP health check helper."""

from __future__ import annotations

import contextlib
import os
import socket


class ObsHealth:
    """Small helper that performs a TCP connect probe to OBS."""

    def __init__(self, host: str | None = None, port: int | None = None, timeout: float | None = None) -> None:
        self.host = host or os.getenv("OBS_WS_HOST", "127.0.0.1")
        self.port = port or int(os.getenv("OBS_WS_PORT", "4455"))
        self.timeout = timeout if timeout is not None else float(os.getenv("OBS_CONNECT_TIMEOUT", "0.05"))

    def healthy(self, timeout: float | None = None) -> bool:
        """Return ``True`` if a TCP connection to OBS can be established."""

        s = socket.socket()
        s.settimeout(timeout or self.timeout)
        try:
            s.connect((self.host, self.port))
            return True
        except OSError:
            return False
        finally:
            with contextlib.suppress(Exception):
                s.close()


# Shared instance used by health checks
obs_health = ObsHealth()

__all__ = ["ObsHealth", "obs_health"]
