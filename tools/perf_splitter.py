#!/usr/bin/env python3
"""Split perf JSON-line logs into separate files by key.

Provided in the mission specification.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import TextIO


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Split perf logs into multiple files based on a key"
    )
    parser.add_argument("input", type=Path, help="Input perf log (JSON lines)")
    parser.add_argument(
        "-k",
        "--key",
        default="pid",
        help="Key within each JSON object used to determine output file",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("."),
        help="Directory where split files will be written",
    )
    return parser.parse_args()


def process_line(
    line: str, key: str, handles: dict[str, TextIO], outdir: Path
) -> None:
    """Write a single JSON record to the file identified by ``key``."""
    if not line.strip():
        return
    record = json.loads(line)
    value = str(record.get(key, "unknown"))
    handle = handles.get(value)
    if handle is None:
        out_path = outdir / f"{value}.jsonl"
        handle = out_path.open("a", encoding="utf-8")
        handles[value] = handle
    handle.write(json.dumps(record) + "\n")


def main() -> None:
    args = parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    handles: dict[str, TextIO] = {}
    try:
        with args.input.open("r", encoding="utf-8") as src:
            for line in src:
                process_line(line, args.key, handles, args.output)
    finally:
        for handle in handles.values():
            handle.close()


if __name__ == "__main__":
    main()
