import os
from pathlib import Path


def use_tmp_base_dir(path: Path):
    """Set BASE_DIR to *path* and refresh settings and paths.

    Also ensures common session directories exist under the new base.
    Returns the :mod:`paths` module for convenience.
    """
    os.environ["BASE_DIR"] = str(path)
    from config.settings import reset_settings

    reset_settings()
    import paths

    paths.refresh_paths()
    # Ensure session related directories exist
    (paths.BASE_DIR / "FightControl" / "data").mkdir(parents=True, exist_ok=True)
    (paths.BASE_DIR / "templates").mkdir(parents=True, exist_ok=True)
    return paths
