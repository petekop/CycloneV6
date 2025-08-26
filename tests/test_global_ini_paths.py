"""Ensure OBS configuration paths derive from the APPDATA environment variable."""

import configparser
import os
from pathlib import Path


def test_global_ini_uses_appdata_env(monkeypatch, tmp_path):
    """The paths in CONFIG_DIR/global.ini should expand from %APPDATA%."""
    # Point APPDATA to a temporary location for the test
    monkeypatch.setenv("APPDATA", str(tmp_path))

    cfg_path = Path(__file__).resolve().parents[1] / "config_legacy" / "global.ini"
    parser = configparser.RawConfigParser()
    # global.ini is stored with a UTF-8 BOM, so read it explicitly
    with open(cfg_path, encoding="utf-8-sig") as f:
        parser.read_file(f)

    for key in ("Configuration", "SceneCollections", "Profiles"):
        raw_value = parser.get("Locations", key)
        # The file should reference the %APPDATA% placeholder
        assert raw_value == "%APPDATA%"
        # Simulate Windows-style expansion to ensure the path resolves
        expanded = raw_value.replace("%APPDATA%", os.environ["APPDATA"])
        assert expanded == str(tmp_path)
