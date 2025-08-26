import pytest

pytest.importorskip("flask")


@pytest.fixture
def app(stub_optional_dependencies):
    import cyclone_server

    cyclone_server.app.config["TESTING"] = True
    return cyclone_server.app


@pytest.fixture
def client(app):
    with app.test_client() as client:
        yield client


REMOVED = [
    b"/static/js/fight_entry.js",
    b"/static/js/performance_history.js",
    b"/static/style.css",
    b"/static/css/style.css",
]

PAGES = [
    "/",
    "/boot",
    "/boot.html",
    "/index",
    "/index.html",
    "/menu",
    "/system-tools",
    "/create",
    "/controller-status",
    "/review",
    "/coaching-panel",
    "/select-fighter",
    "/fighter-carousel",
    "/create-edit-cyclone",
    "/enter-fighters",
]


def test_pages_do_not_reference_removed_assets(client):
    for path in PAGES:
        rv = client.get(path)
        if rv.status_code not in (200, 302, 301):
            continue
        body = rv.data
        for needle in REMOVED:
            assert needle not in body, f"{path} references removed asset {needle!r}"
