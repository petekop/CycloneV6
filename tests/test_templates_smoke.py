import sys
import types

import pytest

pytest.importorskip("flask")
pytestmark = pytest.mark.usefixtures("stub_optional_dependencies")

sys.modules.setdefault("pycountry", types.ModuleType("pycountry"))

from flask import render_template  # noqa: E402

import cyclone_server  # noqa: E402

app = cyclone_server.app


# Add helper routes for component templates if not already defined
if "template_card_front" not in app.view_functions:

    @app.route("/template/card-front")
    def template_card_front():
        fighter = {"name": "Test", "power": 80, "endurance": 90}
        return render_template("components/fighter_card_F.html", fighter=fighter)


if "template_card_back" not in app.view_functions:

    @app.route("/template/card-back")
    def template_card_back():
        fighter = {
            "height": "5'9\"",
            "weight": "160",
            "record": "10-2",
            "stance": "Orthodox",
            "endurance": 85,
            "hr_zones": "Z1-Z5",
        }
        return render_template("components/fighter_card_B.html", fighter=fighter)


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def _assert_no_missing_assets(response):
    html = response.get_data(as_text=True)
    assert "404" not in html


def test_select_fighter_template(client):
    resp = client.get("/select-fighter")
    assert resp.status_code == 200
    _assert_no_missing_assets(resp)


@pytest.mark.parametrize("url", ["/template/card-front", "/template/card-back"])
def test_component_templates(client, url):
    resp = client.get(url)
    assert resp.status_code == 200
    _assert_no_missing_assets(resp)
