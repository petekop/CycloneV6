from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import Iterable

paths_mod = importlib.import_module("paths")
importlib.reload(paths_mod)


def _atomic_json_dump(data: Iterable, path: Path) -> None:
    """Write JSON ``data`` to ``path`` atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(list(data), indent=2))
    tmp.replace(path)


def rebuild_index(
    fighter_data_dir: Path | None = None,
    output_path: Path | None = None,
) -> None:
    """Rebuild the fighters index from ``fighter_data`` profiles."""
    base = paths_mod.BASE_DIR
    fighter_data_dir = fighter_data_dir or base / "FightControl" / "fighter_data"
    output_path = output_path or paths_mod.FIGHTERS_JSON

    fighters: list[dict] = []
    for profile_path in sorted(fighter_data_dir.glob("*/profile.json")):
        try:
            fighters.append(json.loads(profile_path.read_text()))
        except json.JSONDecodeError:
            pass
        except OSError:
            pass

    _atomic_json_dump(fighters, output_path)
