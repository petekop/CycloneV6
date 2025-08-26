import importlib

import pytest


def load_config():
    import server_config

    importlib.reload(server_config)
    return server_config.get_server_config()


def test_debug_gating(monkeypatch):
    monkeypatch.delenv("CYCLONE_DEBUG", raising=False)
    cfg = load_config()
    assert cfg.debug is False

    monkeypatch.setenv("CYCLONE_DEBUG", "1")
    cfg = load_config()
    assert cfg.debug is True


def test_secret_key_handling(monkeypatch):
    monkeypatch.delenv("CYCLONE_SECRET_KEY", raising=False)
    monkeypatch.setenv("CYCLONE_DEBUG", "1")
    cfg = load_config()
    assert cfg.secret_key == "dev-secret"

    monkeypatch.setenv("CYCLONE_SECRET_KEY", "opensesame")
    cfg = load_config()
    assert cfg.secret_key == "opensesame"

    monkeypatch.setenv("CYCLONE_DEBUG", "0")
    monkeypatch.delenv("CYCLONE_SECRET_KEY", raising=False)
    with pytest.raises(SystemExit):
        load_config()
