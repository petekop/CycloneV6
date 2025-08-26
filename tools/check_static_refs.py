#!/usr/bin/env python3
"""Validate references to static assets in templates.

Scans the ``FightControl/static`` directory for available files and the
``templates`` directory for references to those files.  Warns about
references to missing files and files that are not referenced anywhere.

The script always exits with status code ``0`` so it can be used in CI
as a non-blocking check.
"""
from __future__ import annotations

import re
from pathlib import Path

# Regular expressions for locating static references in templates
RE_DIRECT = re.compile(r"['\"]/static/([^'\"?#]+)")
RE_URL_FOR = re.compile(r"url_for\(\s*['\"]static['\"],\s*filename=['\"]([^'\"]+)['\"]")


def _collect_static_files(static_dir: Path) -> set[str]:
    """Return a set of relative paths for all files under ``static_dir``."""
    return {
        str(path.relative_to(static_dir)).replace("\\", "/")
        for path in static_dir.rglob("*")
        if path.is_file()
    }


def _collect_template_refs(templates_dir: Path) -> set[str]:
    """Extract all static file references from templates."""
    refs: set[str] = set()
    for file in templates_dir.rglob("*"):
        if not file.is_file():
            continue
        text = file.read_text(encoding="utf-8", errors="ignore")
        refs.update(RE_DIRECT.findall(text))
        refs.update(RE_URL_FOR.findall(text))
    return refs


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    static_dir = repo_root / "FightControl" / "static"
    templates_dir = repo_root / "templates"

    static_files = _collect_static_files(static_dir)
    template_refs = _collect_template_refs(templates_dir)

    missing = sorted(template_refs - static_files)
    unused = sorted(static_files - template_refs)

    if missing:
        print("Missing static files referenced in templates:")
        for path in missing:
            print(f"  {path}")
    if unused:
        print("Static files not referenced in templates:")
        for path in unused:
            print(f"  {path}")
    if not missing and not unused:
        print("All static references matched.")

    # Always exit with status code 0 (warnings only)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
