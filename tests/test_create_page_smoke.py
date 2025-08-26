import sys
import types

import pytest

pytest.importorskip("flask")

# Provide minimal stubs for optional modules before importing the app
pycountry_stub = types.SimpleNamespace(
    countries=types.SimpleNamespace(get=lambda *a, **k: None),
    subdivisions=types.SimpleNamespace(get=lambda *a, **k: None),
)

sys.modules.setdefault("pycountry", pycountry_stub)
sys.modules.setdefault(
    "FightControl.fighter_routes_v2",
    types.SimpleNamespace(new_fighter=lambda *a, **k: None),
)


@pytest.fixture
def client(stub_optional_dependencies):
    import cyclone_server  # noqa: E402

    app = cyclone_server.app
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_create_page_smoke(client):
    """GET /create returns a page referencing the front logo."""
    resp = client.get("/create")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "cyclone_card_front_logo.png" in html
