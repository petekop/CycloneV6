"""CSV parsing utilities for fighter data.

This module provides helpers to parse CSV rows and files while
normalising header names to internal keys, performing unit conversions
and gracefully handling missing values. It is intentionally lightweight
and does not depend on pandas.
"""

from __future__ import annotations

import csv
import re
from typing import IO, Any, Dict, Iterable, List, Mapping, Optional

# Map normalised header names to internal keys
HEADER_MAP = {
    "name": "name",
    # Normalise common aliases for biological sex
    "gender": "sex",
    "sex": "sex",
    "stance": "stance",
    "country": "country",
    "age": "age",
    "weight": "weight",
    "weightclass": "weightClass",
    "height": "height",
    "range": "range",
    "distance": "distance",
    "bodyfat": "body_fat_pct",
    "bodyfatpct": "body_fat_pct",
    "email": "email",
    # Performance test metrics
    "broadjump": "broadJump",
    "sprint40m": "sprint40m",
    "pressups": "pressUps",
    "chinups": "chinUps",
    "benchpress": "benchPress",
    "frontsquat": "frontSquat",
    "wingate": "wingate",
}

UNIT_FACTORS = {
    "lbs": 0.453592,  # pounds to kilograms
    "in": 2.54,  # inches to centimetres
    "miles": 1.60934,  # miles to kilometres
}

UNIT_PATTERNS = {
    "lbs": re.compile(r"\b(lbs|pounds?)\b"),
    "in": re.compile(r"\b(in|inches?)\b"),
    "miles": re.compile(r"\b(miles?)\b"),
}


def _normalise_header(header: str) -> (str, Optional[str]):
    """Return (normalised_header, unit) for ``header``.

    Units encoded in the header (e.g. "weight (lbs)") are detected and
    stripped.  The remaining text is lower-cased and stripped of common
    separators so it can be looked up in :data:`HEADER_MAP`.
    """
    h = header.strip().lower()
    unit = None
    for u, pattern in UNIT_PATTERNS.items():
        if pattern.search(h):
            unit = u
            h = pattern.sub("", h)
    h = re.sub(r"[^a-z0-9]+", "", h)
    return h, unit


def _convert(value: str, unit: Optional[str]) -> Any:
    """Convert ``value`` according to ``unit`` if possible."""
    if unit is None:
        # try to coerce to float if numeric
        try:
            return float(value)
        except ValueError:
            return value
    try:
        num = float(value)
    except ValueError:
        return None
    factor = UNIT_FACTORS.get(unit)
    return num * factor if factor is not None else num


def parse_row(row: Mapping[str, Any]) -> Dict[str, Any]:
    """Parse a single CSV row into internal representation.

    ``row`` should map column headers to values.  Unknown headers are
    ignored.  Empty values are converted to ``None``.  Numeric values are
    converted to ``float`` and known units are converted to their SI
    equivalents.
    """
    result: Dict[str, Any] = {}
    for header, raw in row.items():
        if header is None:
            continue
        norm, unit = _normalise_header(str(header))
        key = HEADER_MAP.get(norm)
        if not key:
            continue
        if raw in (None, ""):
            result[key] = None
            continue
        value = str(raw).strip()
        result[key] = _convert(value, unit)
    return result


def parse_csv(file: IO[str]) -> List[Dict[str, Any]]:
    """Parse ``file`` containing CSV data into a list of fighters."""
    reader = csv.DictReader(file)
    return [parse_row(row) for row in reader]


__all__ = ["parse_row", "parse_csv"]
