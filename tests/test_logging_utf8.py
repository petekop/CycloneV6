import logging
import sys
import types
from logging.handlers import RotatingFileHandler


def test_setup_logging_writes_utf8(tmp_path, monkeypatch):
    """Log non-ASCII characters and ensure they are written to disk as UTF-8."""

    from config.settings import settings

    # Ensure logs are written under a temporary directory
    monkeypatch.setattr(settings, "BASE_DIR", tmp_path)

    # Stub modules with heavy dependencies before importing server
    class _StubBlueprint:
        name = "stub"

        def register(self, app, options):
            pass

    sys.modules.setdefault("routes.api_routes", types.ModuleType("routes.api_routes")).api_routes = _StubBlueprint()
    sys.modules.setdefault("round_summary", types.ModuleType("round_summary")).generate_round_summaries = (
        lambda *a, **k: None
    )
    sys.modules.setdefault("services.card_builder", types.ModuleType("services.card_builder")).compose_card = (
        lambda *a, **k: None
    )

    from cyclone_server import setup_logging

    # Remove existing handlers to avoid interference
    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)

    setup_logging()

    msg = "Spicy jalapeño 🌶️"
    root.info(msg)

    log_file = tmp_path / "logs" / "app.log"
    with open(log_file, encoding="utf-8") as fh:
        content = fh.read()

    assert msg in content


def test_setup_logging_returns_handler_and_configures_werkzeug(tmp_path, monkeypatch):
    """Ensure ``setup_logging`` uses concurrent handler and configures werkzeug."""

    from config.settings import settings

    # Ensure logs are written under a temporary directory
    monkeypatch.setattr(settings, "BASE_DIR", tmp_path)

    # Stub modules with heavy dependencies before importing server
    class _StubBlueprint:
        name = "stub"

        def register(self, app, options):
            pass

    sys.modules.setdefault("routes.api_routes", types.ModuleType("routes.api_routes")).api_routes = _StubBlueprint()
    sys.modules.setdefault("round_summary", types.ModuleType("round_summary")).generate_round_summaries = (
        lambda *a, **k: None
    )
    sys.modules.setdefault("services.card_builder", types.ModuleType("services.card_builder")).compose_card = (
        lambda *a, **k: None
    )

    # Provide a stub ConcurrentRotatingFileHandler
    class _StubHandler(RotatingFileHandler):
        pass

    stub_mod = types.ModuleType("concurrent_log_handler")
    stub_mod.ConcurrentRotatingFileHandler = _StubHandler
    monkeypatch.setitem(sys.modules, "concurrent_log_handler", stub_mod)

    from cyclone_server import setup_logging

    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)

    # Simulate first run (no WERKZEUG_RUN_MAIN)
    monkeypatch.delenv("WERKZEUG_RUN_MAIN", raising=False)
    handler1 = setup_logging()
    assert isinstance(handler1, _StubHandler)
    assert logging.getLogger("werkzeug").level == logging.WARNING
    assert sum(isinstance(h, _StubHandler) for h in root.handlers) == 1

    # Simulate Flask reloader second run
    monkeypatch.setenv("WERKZEUG_RUN_MAIN", "true")
    handler2 = setup_logging()
    assert handler2 is handler1
    assert sum(isinstance(h, _StubHandler) for h in root.handlers) == 1
