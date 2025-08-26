"""Automatically convert the most recent fighter CSV into ``fighters.json``.

This script mirrors :mod:`csv_to_fighter_json` but automatically locates the
latest CSV file within the downloads directory and removes it after
conversion.  Parsing is delegated to ``parse_csv`` so the same session grouping
logic is used in tests and manual runs.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd  # Imported for side-effects (ensures dependency available)

FIGHTCONTROL_DIR = Path(__file__).resolve().parents[1]
if str(FIGHTCONTROL_DIR) not in sys.path:
    sys.path.insert(0, str(FIGHTCONTROL_DIR))
REPO_ROOT = FIGHTCONTROL_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from csv_to_fighter_json import parse_csv

from paths import BASE_DIR


def main() -> None:
    download_folder = BASE_DIR / "FightControl" / "downloads"
    dest_folder = BASE_DIR / "FightControl" / "data"

    csv_files = sorted(
        download_folder.glob("*.csv"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    if not csv_files:
        print("❌ No CSV files found in the downloads folder.")
        return

    latest_csv = csv_files[0]
    print(f"[Cyclone] Found CSV: {latest_csv.name}")

    fighters = parse_csv(latest_csv)

    dest_folder.mkdir(parents=True, exist_ok=True)
    output_path = dest_folder / "fighters.json"
    with open(output_path, "w") as f:
        json.dump(fighters, f, indent=2)

    latest_csv.unlink()
    print(f"✅ {len(fighters)} fighter(s) written to {output_path}")
    print(f"🗑️ Deleted source file: {latest_csv.name}")


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
