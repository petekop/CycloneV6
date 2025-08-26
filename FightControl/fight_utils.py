"""Utility helpers for the FightControl package.

Avoid using generic module names that might shadow top-level utilities.
"""

import json
import os
import re
from pathlib import Path


def safe_filename(name: str) -> str:
    """Return a filesystem-safe filename.

    Any directory components are removed and disallowed characters replaced
    with underscores so the returned string can be safely joined with another
    path.
    """
    if not isinstance(name, str):
        name = str(name)

    # Remove any directory components first
    name = os.path.basename(name)

    # Replace unwanted characters with underscores. Allow alphanumerics and a
    # few common symbols used in filenames.
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name)

    # Edge case: name may become empty after sanitization
    return name or "unnamed"


# Allow decimals in the duration component which represents minutes and tolerate
# optional whitespace and different separators (x/X/×).
_ROUND_FORMAT_RE = re.compile(r"^\s*(\d+)\s*[xX×]\s*(\d+(?:\.\d+)?)\s*$")


def parse_round_format(round_format: str) -> tuple[int, int]:
    """Validate and parse a round format string like ``"3x2"``.

    The format is ``<rounds>x<minutes>`` where ``minutes`` may be a fractional
    value. Whitespace around the separator is ignored and ``x``, ``X`` or ``×``
    are all accepted as the separator. The returned duration is always
    expressed in **seconds** (e.g. ``"0.25"`` minutes maps to ``15`` seconds).

    Parameters
    ----------
    round_format:
        String describing the number of rounds and duration using the
        ``<rounds>x<minutes>`` format. Decimal minute values are allowed.

    Returns
    -------
    tuple[int, int]
        A tuple containing the number of rounds and duration in **seconds**.

    Raises
    ------
    ValueError
        If ``round_format`` does not match the expected pattern.
    """

    if not isinstance(round_format, str):
        raise ValueError("round_format must be a string like '<rounds>x<minutes>'")

    match = _ROUND_FORMAT_RE.fullmatch(round_format)
    if not match:
        raise ValueError("round_format must match '<rounds>x<minutes>' e.g., '3x2'")

    rounds, minutes = match.groups()
    seconds = int(float(minutes) * 60)
    return int(rounds), seconds


def load_round_state(path: Path) -> dict:
    """Return the persisted round state from ``path``.

    Any JSON parsing errors result in an empty dictionary being returned so a
    caller can safely assume a mapping.  Missing files are also treated as an
    empty state.
    """

    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def save_round_state(path: Path, data: dict) -> None:
    """Persist ``data`` to ``path`` ensuring the parent directory exists."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))
