import io

import pytest

pytest.importorskip("flask")


def _png_bytes() -> bytes:
    buf = io.BytesIO()
    buf.write(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\nIDATx\xdac\xf8\x0f\x00\x01\x01\x01\x00\x18\xdd\x8d\xbc"
        b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    return buf.getvalue()


@pytest.fixture
def client(tmp_path, monkeypatch, stub_optional_dependencies):
    from flask import Flask

    import routes.api_routes as api_routes

    monkeypatch.setattr(api_routes, "BASE_DIR", tmp_path, raising=False)
    monkeypatch.setattr(api_routes.api_routes, "BASE_DIR", tmp_path, raising=False)

    app = Flask(__name__)
    app.register_blueprint(api_routes.api_routes)
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_upload_fighter_photo(client, tmp_path):
    data = {"file": (io.BytesIO(_png_bytes()), "photo.png", "image/png")}
    resp = client.post("/api/fighter/photo", data=data, content_type="multipart/form-data")
    assert resp.status_code == 200
    payload = resp.get_json()
    assert isinstance(payload["url"], str)
    assert payload["url"].startswith("/static/uploads/")
    assert (tmp_path / "FightControl" / "static" / "uploads" / "photo.png").exists()
