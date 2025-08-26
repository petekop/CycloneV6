#!/usr/bin/env python3
"""Migrate legacy .env files to the v5 format.

- Backs up an existing .env to .env.bak.
- Copies .env.example to .env when no .env is present.
- Removes keys not found in .env.example while preserving comments and order.
"""
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
EXAMPLE_PATH = ROOT / ".env.example"
BACKUP_PATH = ROOT / ".env.bak"


def parse_env(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip()
    return data


def build_env(example_lines: list[str], values: dict[str, str]) -> str:
    output_lines: list[str] = []
    for line in example_lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in line:
            output_lines.append(line)
            continue
        key, default = line.split("=", 1)
        key = key.strip()
        value = values.get(key, default.strip())
        output_lines.append(f"{key}={value}")
    return "\n".join(output_lines) + "\n"


def main() -> None:
    if not ENV_PATH.exists():
        shutil.copy(EXAMPLE_PATH, ENV_PATH)
        print(f"Created {ENV_PATH} from example")
    else:
        shutil.copy(ENV_PATH, BACKUP_PATH)
        current_values = parse_env(ENV_PATH)
        example_lines = EXAMPLE_PATH.read_text().splitlines()
        ENV_PATH.write_text(build_env(example_lines, current_values))
        print(f"Updated {ENV_PATH} (backup at {BACKUP_PATH})")

    try:
        from rebuild_fighters_index import main as rebuild_fighters_index

        rebuild_fighters_index()
    except Exception as exc:
        print(f"Failed to rebuild fighters index: {exc}")


if __name__ == "__main__":
    main()
