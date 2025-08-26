import importlib
import os

import pytest

import paths
from utils.template_loader import load_template

pytest.importorskip("flask")


def setup_app(tmp_path):
    os.environ["BASE_DIR"] = str(tmp_path)
    boot = tmp_path / "templates" / "boot.html"
    boot.parent.mkdir(parents=True, exist_ok=True)
    boot.write_text(load_template("boot.html"))
    importlib.reload(paths)
    import cyclone_server

    importlib.reload(cyclone_server)
    cyclone_server.app.config["TESTING"] = True
    return cyclone_server.app.test_client()


def test_api_create_cyclone_basic(tmp_path, stub_optional_dependencies):
    original_base = paths.BASE_DIR
    client = setup_app(tmp_path)
    profile = {"name": "Alice"}
    resp = client.post("/api/create-cyclone", json=profile)
    assert resp.status_code in (200, 201)
    data = resp.get_json()
    assert "fighter_id" in data
    assert "charts" in data
    assert "assets" in data
    os.environ["BASE_DIR"] = str(original_base)
    paths.refresh_paths()
