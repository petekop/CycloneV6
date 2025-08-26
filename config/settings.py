"""Lightweight settings loader for the Cyclone project.

This module attempts to use :mod:`pydantic-settings` for configuration
management.  If that dependency is missing, a very small substitute is
provided that reads values from environment variables and an optional
``.env`` file.

The :func:`reset_settings` helper can be used in tests to reload
configuration after modifying environment variables.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional, get_type_hints

try:  # pragma: no cover - optional dependency
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - executed when dependency missing
    def load_dotenv(*_args: Any, **_kwargs: Any) -> None:
        """Fallback no-op when :mod:`python-dotenv` is unavailable."""


ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(ENV_PATH)
# Default to the repository root when BASE_DIR isn't configured
DEFAULT_BASE_DIR = Path(__file__).resolve().parent.parent


def _read_env_file(path: Path) -> Dict[str, str]:
    """Parse a ``.env`` file into a dictionary."""

    data: Dict[str, str] = {}
    if not path.exists():
        return data

    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip().strip("'\"")
    return data


try:  # pragma: no cover - exercised when dependency is present
    from pydantic_settings import BaseSettings, SettingsConfigDict  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - default execution path

    class BaseSettings:  # type: ignore[override]
        """Minimal drop-in replacement for :class:`pydantic.BaseSettings`."""

        model_config: Dict[str, Any] = {}

        def __init__(self, **kwargs: Any) -> None:
            config = getattr(self, "model_config", {})
            env_file = config.get("env_file")

            data: Dict[str, str] = {}
            if env_file:
                data.update(_read_env_file(Path(env_file)))
            data.update(os.environ)
            data.update(kwargs)

            type_hints = get_type_hints(type(self))

            for name, typ in type_hints.items():
                default = getattr(self, name, ...)
                if name in data:
                    value: Any = data[name]
                elif default is not ...:
                    value = default
                else:
                    raise KeyError(f"Missing required setting: {name}")

                if typ is Path:
                    value = Path(value)
                setattr(self, name, value)

    SettingsConfigDict = dict  # type: ignore[misc]


class Settings(BaseSettings):
    """Application configuration values."""

    model_config = SettingsConfigDict(env_file=ENV_PATH)

    BASE_DIR: Path = DEFAULT_BASE_DIR
    OBS_WS_URL: str = "ws://127.0.0.1:4455"
    OBS_WS_PASSWORD: str = "changeme"
    MEDIAMTX_PATH: Path = DEFAULT_BASE_DIR / "CAMSERVER" / "mediamtx" / "mediamtx_tcp_office.yml"
    HR_RED_MAC: Optional[str] = None
    HR_BLUE_MAC: Optional[str] = None
    SOURCE_RECORD_IDS: Optional[str] = None
    """Comma-separated list of OBS source IDs to record, e.g., "1,2,3,4"."""

    SOURCE_FILTERS: Optional[str] = None
    """Semicolon-separated scene|filter pairs, e.g., "Scene|Filter;Scene|Filter"."""


def reset_settings() -> None:
    """Reload configuration from the environment and ``.env`` file."""

    global settings
    settings = Settings()
    # Some tests manipulate ``sys.modules`` and remove optional modules such as
    # ``cyclone_modules.ObsControl.obs_control``.  Re-import them here so
    # subsequent ``importlib.reload`` calls succeed regardless of test order.
    import importlib, sys

    try:  # pragma: no cover - best effort
        mod = importlib.import_module("cyclone_modules.ObsControl.obs_control")
        sys.modules.setdefault("cyclone_modules.ObsControl.obs_control", mod)
    except Exception:
        pass


# Global settings instance used throughout the application
settings = Settings()


__all__ = ["Settings", "settings", "reset_settings"]
