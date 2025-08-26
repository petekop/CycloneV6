import importlib

import pytest

import routes.fighters as fighters


def test_fighters_json_path_updates_after_env_changes(monkeypatch, tmp_path_factory):
    base1 = tmp_path_factory.mktemp("base1")
    base2 = tmp_path_factory.mktemp("base2")

    monkeypatch.setenv("BASE_DIR", str(base1))
    p1 = fighters._fighters_json_path()
    assert p1.is_relative_to(base1)

    monkeypatch.setenv("BASE_DIR", str(base2))
    p2 = fighters._fighters_json_path()
    assert p2.is_relative_to(base2)


def test_add_fighter_uses_updated_base_dir(monkeypatch, tmp_path_factory):
    flask = pytest.importorskip("flask")
    base1 = tmp_path_factory.mktemp("base1")
    base2 = tmp_path_factory.mktemp("base2")

    monkeypatch.setenv("BASE_DIR", str(base1))
    import fighter_utils
    import paths
    import routes.fighters as fighters_module

    importlib.reload(paths)
    importlib.reload(fighter_utils)
    importlib.reload(fighters_module)
    app = flask.Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(fighters_module.fighters_bp)
    client = app.test_client()

    resp = client.post("/fighters", json={"name": "One"})
    assert resp.status_code == 201
    assert (base1 / "FightControl" / "data" / "fighters.json").exists()

    monkeypatch.setenv("BASE_DIR", str(base2))
    resp = client.post("/fighters", json={"name": "Two"})
    assert resp.status_code == 201
    assert (base2 / "FightControl" / "data" / "fighters.json").exists()
