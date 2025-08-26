# Cyclone project
# Date: 2025-07-28 (Final Patch: Full Python OBS WebSocket v5+ integration)

import logging
import os
import sys
from pathlib import Path

from flask import Flask

# -------------------------------------------------
# Setup paths & Flask app
# -------------------------------------------------
# Resolve the repository root from the ``BASE_DIR`` environment variable or
# default to this file's parent directory.  When running from a PyInstaller
# bundle, ``sys._MEIPASS`` is used instead.
if bool(getattr(sys, "frozen", False)) and hasattr(sys, "_MEIPASS"):
    repo_root = Path(sys._MEIPASS)  # pragma: no cover - exercised in tests
else:
    repo_root = Path(os.environ.get("BASE_DIR", Path(__file__).resolve().parent))
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

ROOT_DIR = repo_root
TEMPLATE_DIR = ROOT_DIR / "templates"
STATIC_DIR = ROOT_DIR / "FightControl" / "static"
DATA_DIR = ROOT_DIR / "FightControl" / "data"
LIVE_DIR = ROOT_DIR / "FightControl" / "live_data"
OVERLAY_DIR = ROOT_DIR / "CAMSERVER" / "overlay"
FIGHTERS_JSON = DATA_DIR / "fighters.json"

app = Flask(
    __name__,
    template_folder=str(TEMPLATE_DIR),
    static_folder=str(STATIC_DIR),
    static_url_path="/static",
)

# Only emit debug information when explicitly requested.  This prevents
# imports from producing console noise during tests while still allowing
# developers to enable diagnostics via the ``CYCLONE_SETUP_PATHS_LOG``
# environment variable.
if os.getenv("CYCLONE_SETUP_PATHS_LOG"):
    logger = logging.getLogger(__name__)
    logger.info("TEMPLATE_DIR = %s", TEMPLATE_DIR)
    logger.info("STATIC_DIR   = %s", STATIC_DIR)

# Register blueprint (deprecated launch system removed)
