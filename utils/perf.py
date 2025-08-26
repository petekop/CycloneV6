"""Performance utilities for fighter card generation.

This module provides lightweight helpers to parse uploaded performance
CSV files and build chart-friendly structures.  Historically it also
contained a very small card composer, but that logic now lives in
``services.card_builder``.  A compatibility shim remains for callers that
still import :func:`compose_card_png`.
"""

from __future__ import annotations

import csv
import warnings
from pathlib import Path
from typing import Any, Dict


def parse_performance_csv(path: str | Path) -> Dict[str, float]:
    """Parse ``path`` and return performance metrics.

    The CSV is expected to contain a single row with metric headers such as
    ``power`` or ``endurance``.  Non-numeric values are ignored and missing
    files yield an empty dictionary.
    """

    metrics: Dict[str, float] = {}
    try:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            row = next(reader, None)
            if not row:
                return {}
            for key, val in row.items():
                if val in (None, "") or key is None:
                    continue
                try:
                    metrics[key.strip()] = float(val)
                except (TypeError, ValueError):
                    # Skip values that cannot be converted to float
                    continue
    except Exception:
        return {}
    return metrics


def build_charts_from_perf(perf: Dict[str, float], profile: Dict[str, Any]) -> Dict[str, Any]:
    """Return a JSON-serialisable charts structure.

    Only known metric keys are included and missing values are omitted so
    the consumer can render charts with whatever data is available.
    """

    radar_keys = ["power", "endurance", "speed", "agility"]
    radar = {k: perf.get(k) for k in radar_keys if perf.get(k) is not None}
    charts: Dict[str, Any] = {"radar": radar}
    if perf.get("hr_zones") is not None:
        charts["hr_zones"] = perf["hr_zones"]
    charts["fighter"] = {
        "name": profile.get("name"),
        "country": profile.get("country"),
    }
    return charts


def compose_card_png(*args, **kwargs):
    """Deprecated shim for :func:`services.card_builder.compose_card`.

    Older code imported :func:`compose_card_png` from this module.  The new
    implementation lives in :mod:`services.card_builder` under the name
    :func:`compose_card`.  This wrapper forwards arguments and issues a
    :class:`DeprecationWarning` to alert callers.
    """

    warnings.warn(
        "compose_card_png is deprecated; import compose_card from services.card_builder instead",
        DeprecationWarning,
        stacklevel=2,
    )
    from services.card_builder import compose_card

    return compose_card(*args, **kwargs)


__all__ = [
    "parse_performance_csv",
    "build_charts_from_perf",
    "compose_card_png",
]

