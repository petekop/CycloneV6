"""Disk space helper utilities using psutil."""

from __future__ import annotations

from pathlib import Path

import psutil


def disk_free_gb(path: Path = Path("/")) -> float:
    """Return available disk space for ``path`` in gigabytes.

    The partition containing ``path`` is inspected using psutil and the
    free space in bytes is converted to gigabytes.
    """
    usage = psutil.disk_usage(str(path))
    return usage.free / (1024**3)
