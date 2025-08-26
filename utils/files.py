from __future__ import annotations

"""Small file helpers with explicit UTF-8 handling."""

import csv
from pathlib import Path
from typing import IO


def open_utf8(path: str | Path, mode: str = "r", newline: str | None = "", **kwargs) -> IO[str]:
    """Return an open text file handle using UTF-8 encoding.

    Parameters
    ----------
    path:
        File system path to open.
    mode:
        File mode passed to :func:`open` (defaults to ``"r"``).
    newline:
        Optional newline sequence forwarded to :func:`open`.  Defaults to
        ``""`` which enables universal newline handling.  Use ``None`` to
        retain platform-specific behavior.
    **kwargs:
        Additional keyword options forwarded directly to :func:`open`.

    Returns
    -------
    IO[str]:
        An open text file handle.
    """
    return open(Path(path), mode, newline=newline, encoding="utf-8", **kwargs)


def read_csv_dicts(path: str | Path, **kwargs) -> list[dict[str, str]]:
    """Return rows from CSV ``path`` as a list of dictionaries.

    Parameters
    ----------
    path:
        File system path to the CSV file.
    **kwargs:
        Additional options forwarded to :func:`open_utf8`.

    Returns
    -------
    list[dict[str, str]]:
        The CSV rows represented as dictionaries.
    """
    with open_utf8(path, "r", newline="", **kwargs) as fh:
        reader = csv.DictReader(fh)
        return list(reader)


def csv_writer_utf8(path: str | Path, *args, **kwargs):
    """Open ``path`` for writing and return ``(file, csv.writer)``.

    The caller is responsible for closing the returned file handle.
    Additional positional and keyword arguments are forwarded to
    :class:`csv.writer`.
    """
    fh = open_utf8(path, "w", newline="")
    writer = csv.writer(fh, *args, **kwargs)
    return fh, writer


def csv_appender_utf8(path: str | Path, *args, **kwargs):
    """Open ``path`` for appending and return ``(file, csv.writer)``.

    The caller is responsible for closing the returned file handle.
    Additional positional and keyword arguments are forwarded to
    :class:`csv.writer`.
    """
    fh = open_utf8(path, "a", newline="")
    writer = csv.writer(fh, *args, **kwargs)
    return fh, writer


__all__ = ["open_utf8", "read_csv_dicts", "csv_writer_utf8", "csv_appender_utf8"]
