"""Utility for loading boot-time binary paths from YAML."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

BOOT_PATHS_FILE = Path(__file__).resolve().parent / "boot_paths.yml"


def load_boot_paths(path: Path = BOOT_PATHS_FILE) -> Dict[str, Dict[str, Any]]:
    """Return boot configuration mapping loaded from ``boot_paths.yml``.

    A small wrapper around :func:`yaml.safe_load` with a fallback that returns
    an empty mapping when the file or dependency is missing.  This keeps the
    rest of the codebase decoupled from the YAML library and gracefully handles
    environments where it is unavailable.
    """
    try:  # pragma: no cover - PyYAML optional
        import yaml  # type: ignore
    except Exception:  # pragma: no cover - fallback when PyYAML missing
        return {}

    try:
        data = yaml.safe_load(path.read_text())
    except FileNotFoundError:
        return {}
    except Exception:  # pragma: no cover - best effort
        return {}
    return data or {}


__all__ = ["load_boot_paths"]
