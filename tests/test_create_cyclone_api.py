import importlib
import io
import json
import os
from pathlib import Path
from typing import Callable

import pytest
from PIL import Image

import paths
from utils.template_loader import load_template

pytest.importorskip("flask")

BASE_DIR = Path(__file__).resolve().parents[1]


def _png_bytes(color=(0, 0, 0)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (2, 2), color).save(buf, format="PNG")
    return buf.getvalue()


def setup_app(tmp_path) -> tuple[object, Path, Callable[[str], str]]:
    os.environ["BASE_DIR"] = str(tmp_path)

    fc_dir = tmp_path / "FightControl"
    images_dir = fc_dir / "static" / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    img = _png_bytes()
    (images_dir / "cyclone_card_front_logo.png").write_bytes(img)
    (images_dir / "cyclone_card_back.png").write_bytes(img)

    boot = tmp_path / "templates" / "boot.html"
    boot.parent.mkdir(parents=True, exist_ok=True)
    boot.write_text(load_template("boot.html"))

    import cyclone_server
    import fighter_utils as fc_utils
    import routes.api_routes as api_routes

    importlib.reload(paths)
    importlib.reload(fc_utils)
    importlib.reload(api_routes)
    importlib.reload(cyclone_server)

    cyclone_server.app.config["TESTING"] = True
    client = cyclone_server.app.test_client()

    return client, fc_dir, fc_utils.safe_filename


def _post_create_cyclone(client, profile, csv_bytes=None, photo_bytes=None):
    data = {"profile": json.dumps(profile)}
    if csv_bytes is not None:
        data["perf_csv"] = (io.BytesIO(csv_bytes), "performance.csv")
    if photo_bytes is not None:
        data["photo"] = (io.BytesIO(photo_bytes), "photo.png")
    return client.post("/api/create-cyclone", data=data)


def _check_required_files(folder: Path, expect_perf_csv: bool = True) -> None:
    required = ["profile.json", "charts.json", "card_full.png", "card_meta.json"]
    if expect_perf_csv:
        required.append("performance.csv")
    for fn in required:
        assert (folder / fn).exists(), f"{fn} missing"


def test_create_cyclone_with_csv(tmp_path):
    client, fc_dir, safe_filename = setup_app(tmp_path)
    profile = {"name": "Alice"}
    csv_bytes = b"metric,value\nspeed,90\n"
    photo_bytes = _png_bytes()
    resp = _post_create_cyclone(client, profile, csv_bytes=csv_bytes, photo_bytes=photo_bytes)
    assert resp.status_code == 200
    fighter_id = resp.get_json()["fighter_id"]
    assert fighter_id == safe_filename(profile["name"])
    folder = fc_dir / "fighter_data" / fighter_id
    _check_required_files(folder, expect_perf_csv=True)
    os.environ["BASE_DIR"] = str(BASE_DIR)
    paths.refresh_paths()


def test_create_cyclone_without_csv(tmp_path):
    client, fc_dir, safe_filename = setup_app(tmp_path)
    profile = {"name": "Bob"}
    photo_bytes = _png_bytes()
    resp = _post_create_cyclone(client, profile, photo_bytes=photo_bytes)
    assert resp.status_code == 200
    fighter_id = resp.get_json()["fighter_id"]
    assert fighter_id == safe_filename(profile["name"])
    folder = fc_dir / "fighter_data" / fighter_id
    _check_required_files(folder, expect_perf_csv=False)
    os.environ["BASE_DIR"] = str(BASE_DIR)
    paths.refresh_paths()
