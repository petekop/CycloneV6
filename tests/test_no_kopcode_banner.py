"""Ensure the legacy KOPCODE banner does not appear in the codebase."""

import subprocess
from pathlib import Path


def test_no_kopcode_banner() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    banned = "KOPCODE CYCLONE V1"
    files = subprocess.check_output(["git", "ls-files"], cwd=repo_root, text=True).splitlines()
    offenders: list[str] = []
    for rel_path in files:
        if rel_path.endswith(".py") and rel_path != "tests/test_no_kopcode_banner.py":
            text = (repo_root / rel_path).read_text(encoding="utf-8", errors="ignore")
            if banned in text:
                offenders.append(rel_path)
    assert not offenders, f"{banned} found in: {', '.join(offenders)}"

