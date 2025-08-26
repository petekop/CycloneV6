"""Utility to migrate current_fight.json to new fighter key names."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

DEFAULT_PATH = Path("FightControl/data/current_fight.json")


def migrate_current_fight(path: Path = DEFAULT_PATH) -> bool:
    """Rewrite old fighter keys to the new ``red_fighter``/``blue_fighter``.

    Parameters
    ----------
    path:
        Location of ``current_fight.json``. Defaults to the standard data file.

    Returns
    -------
    bool
        ``True`` if the file was updated, ``False`` otherwise.
    """

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"File not found: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {path}: {exc}")

    changed = False
    if "red" in data and "red_fighter" not in data:
        data["red_fighter"] = data.pop("red")
        changed = True
    if "blue" in data and "blue_fighter" not in data:
        data["blue_fighter"] = data.pop("blue")
        changed = True

    if changed:
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return changed


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate current_fight.json to use red_fighter/blue_fighter keys.")
    parser.add_argument(
        "--path",
        default=str(DEFAULT_PATH),
        help="Path to current_fight.json (default: %(default)s)",
    )
    args = parser.parse_args()

    updated = migrate_current_fight(Path(args.path))
    if updated:
        print("current_fight.json updated with new fighter keys")
    else:
        print("current_fight.json already uses new fighter keys")


if __name__ == "__main__":
    main()
