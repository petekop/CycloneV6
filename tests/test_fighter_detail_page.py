import json

import pytest

pytest.importorskip("flask")
pytestmark = pytest.mark.usefixtures("stub_optional_dependencies")

import sys
import types

# Stub PIL to avoid heavy dependency during tests
PIL = types.ModuleType("PIL")
PIL.Image = types.ModuleType("Image")
PIL.ImageDraw = types.ModuleType("ImageDraw")
PIL.ImageFont = types.ModuleType("ImageFont")
sys.modules.setdefault("PIL", PIL)
sys.modules.setdefault("PIL.Image", PIL.Image)
sys.modules.setdefault("PIL.ImageDraw", PIL.ImageDraw)
sys.modules.setdefault("PIL.ImageFont", PIL.ImageFont)

# Stub matplotlib to avoid heavy dependency during import
matplotlib = types.ModuleType("matplotlib")
matplotlib.use = lambda *a, **k: None
matplotlib.pyplot = types.ModuleType("pyplot")
sys.modules.setdefault("matplotlib", matplotlib)
sys.modules.setdefault("matplotlib.pyplot", matplotlib.pyplot)

pandas = types.ModuleType("pandas")
pandas.DataFrame = type("DataFrame", (), {})
pandas.read_csv = lambda *a, **k: None
pandas.to_datetime = lambda *a, **k: None
pandas.to_numeric = lambda *a, **k: None
sys.modules.setdefault("pandas", pandas)

import cyclone_server  # noqa: E402
from routes import fighters  # noqa: E402


def test_fighter_detail_page_includes_card_image(tmp_path, monkeypatch):
    monkeypatch.setattr(fighters, "base", tmp_path)
    monkeypatch.setattr(fighters, "safe_filename", lambda s: s)

    fighter_dir = tmp_path / "FightControl" / "fighter_data" / "test"
    fighter_dir.mkdir(parents=True)
    (fighter_dir / "profile.json").write_text(json.dumps({"name": "Test"}))
    (fighter_dir / "card_full.png").write_bytes(b"png")

    app = cyclone_server.app
    app.config["TESTING"] = True
    with app.test_client() as client:
        resp = client.get("/fighters/test")
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        assert '<img class="card" src="/fighter_data/test/card_full.png"' in html

