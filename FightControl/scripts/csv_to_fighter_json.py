"""Convert fighter registration CSV files to ``fighters.json``.

This utility parses a CSV export from Google Forms and assembles a fighter
profile for each row.  In addition to the basic metadata, any columns whose
headers contain a ``YYYY-MM-DD`` date are grouped into test sessions.  Each
session is stored as ``{"date": <date>, "performance": {…}}`` so downstream tools
can track testing history.

The module exposes :func:`convert_row_to_fighter` for unit tests while the
``main`` function provides a CLI entry point.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

FIGHTCONTROL_DIR = Path(__file__).resolve().parents[1]
if str(FIGHTCONTROL_DIR) not in sys.path:
    sys.path.insert(0, str(FIGHTCONTROL_DIR))
REPO_ROOT = FIGHTCONTROL_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from paths import BASE_DIR

FIELD_MAP = {
    "Full Name": "name",
    "Weight Category (KG)": "weight",
    "Height\n": "height",
    "Date of Birth": "dob",
    "Stance": "stance",
    "MugShot": "photo",
}


def _clean_value(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    return "" if value is None else str(value)


DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")


def convert_row_to_fighter(row: pd.Series) -> dict:
    """Convert a row from the registration CSV into a fighter profile.

    Unknown columns containing a ``YYYY-MM-DD`` substring are grouped into
    sessions where the portion preceding the date becomes the metric name.
    """

    fighter = {key: _clean_value(row.get(csv_field)) for csv_field, key in FIELD_MAP.items()}

    sessions: dict[str, dict[str, object]] = {}
    for col, value in row.items():
        if col in FIELD_MAP or pd.isna(value) or value in (None, ""):
            continue
        match = DATE_RE.search(col)
        if not match:
            continue
        date = match.group(1)
        metric_name = DATE_RE.sub("", col).strip(" -_/\n")
        if not metric_name:
            continue
        sessions.setdefault(date, {})[metric_name] = value

    fighter["sessions"] = [{"date": d, "performance": m} for d, m in sorted(sessions.items())]
    return fighter


def parse_dataframe(df: pd.DataFrame) -> list[dict]:
    return [convert_row_to_fighter(row) for _, row in df.iterrows()]


def parse_csv(csv_path: os.PathLike[str] | str) -> list[dict]:
    df = pd.read_csv(csv_path)
    return parse_dataframe(df)


def main(csv_path: os.PathLike[str] | str | None = None) -> None:
    source_folder = BASE_DIR / "FightControl" / "downloads"
    dest_folder = BASE_DIR / "FightControl" / "data"
    csv_filename = "Form responses 1.csv" if csv_path is None else csv_path
    csv_path = csv_path or (source_folder / csv_filename)

    fighters = parse_csv(csv_path)

    dest_folder.mkdir(parents=True, exist_ok=True)
    output_path = dest_folder / "fighters.json"
    with open(output_path, "w") as f:
        json.dump(fighters, f, indent=2)

    print(f"✅ {len(fighters)} fighter(s) written to {output_path}")


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
