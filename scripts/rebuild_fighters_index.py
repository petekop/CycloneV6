#!/usr/bin/env python3
"""Rebuild the fighters index.

This CLI is a thin wrapper around ``utils.fighters_index.rebuild_index``.
It accepts an optional ``--base-dir`` argument pointing to the root of a
Cyclone installation. When omitted, :mod:`paths` is used to determine the
base directory.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import paths
from utils.fighters_index import rebuild_index as _rebuild_index


FIGHTER_DATA_DIR = paths.BASE_DIR / "FightControl" / "fighter_data"
OUTPUT_PATH = paths.BASE_DIR / "FightControl" / "data" / "fighters.json"


def rebuild_index(base_dir: Path | None = None) -> Path:
    """Rebuild the fighters index for ``base_dir``.

    The optional ``base_dir`` argument is primarily a convenience for the
    command-line interface.  Tests monkeypatch :data:`FIGHTER_DATA_DIR` and
    :data:`OUTPUT_PATH` directly which keeps this helper flexible without
    requiring complex argument plumbing.
    """
    if base_dir is not None:
        fighter_dir = Path(base_dir) / "FightControl" / "fighter_data"
        output_path = Path(base_dir) / "FightControl" / "data" / "fighters.json"
    else:
        fighter_dir = FIGHTER_DATA_DIR
        output_path = OUTPUT_PATH
    _rebuild_index(fighter_dir, output_path)
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-dir",
        type=Path,
        default=None,
        help="Override the Cyclone base directory.",
    )
    args = parser.parse_args()
    output_path = rebuild_index(args.base_dir)
    print(f"Wrote fighters index to {output_path}")


if __name__ == "__main__":
    main()

