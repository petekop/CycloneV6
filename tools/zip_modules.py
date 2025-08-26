#!/usr/bin/env python3
"""Create zip archives for cyclone modules.

This script scans subdirectories in the top-level ``cyclone_modules/`` folder and
produces ``.zip`` archives for each one inside ``cyclone_modules/zipped``.

Test directories, log files and other common non-code artifacts are excluded
from the archives.
"""

from __future__ import annotations

import fnmatch
import logging
import zipfile
from pathlib import Path

# Directories and file patterns to ignore when building archives
EXCLUDE_DIRS = {"tests", "logs", "__pycache__", "node_modules", "zipped"}
EXCLUDE_FILE_PATTERNS = [
    "test_*.py",
    "*.pyc",
    "*.pyo",
    "*.log",
    "*.tmp",
]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def should_skip(file_path: Path) -> bool:
    """Return ``True`` if the file should be skipped."""
    return any(fnmatch.fnmatch(file_path.name, pattern) for pattern in EXCLUDE_FILE_PATTERNS)


def zip_modules() -> None:
    base_dir = Path(__file__).resolve().parents[1]
    modules_dir = base_dir / "cyclone_modules"
    output_dir = modules_dir / "zipped"

    if not modules_dir.exists():
        logger.warning("No modules directory found at %s", modules_dir)
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    for module in modules_dir.iterdir():
        if not module.is_dir() or module.name in EXCLUDE_DIRS:
            continue

        zip_path = output_dir / f"{module.name}.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for file_path in module.rglob("*"):
                if file_path.is_dir():
                    continue
                if any(part in EXCLUDE_DIRS or part.startswith(".") for part in file_path.parts):
                    continue
                if should_skip(file_path):
                    continue
                arcname = file_path.relative_to(module)
                zipf.write(file_path, arcname)
        logger.info("Created %s", zip_path)


if __name__ == "__main__":
    zip_modules()
