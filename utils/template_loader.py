from pathlib import Path


def load_template(name: str) -> str:
    """Return contents of template ``name``.

    The function searches for ``resources/templates/<name>`` relative to this
    module and the current working directory.  The first matching file is
    returned as text.  A :class:`FileNotFoundError` is raised if the template
    cannot be located.
    """
    candidates = [
        Path(__file__).with_name("resources") / "templates" / name,
        Path.cwd() / "resources" / "templates" / name,
    ]
    for path in candidates:
        if path.exists():
            return path.read_text(encoding="utf-8")
    raise FileNotFoundError(f"Template '{name}' not found in any of: {', '.join(str(p) for p in candidates)}")
