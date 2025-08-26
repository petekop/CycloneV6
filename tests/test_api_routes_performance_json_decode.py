import json
import sys
import types


def _setup_api_routes(monkeypatch, tmp_path):
    def _decorator(*_args, **_kwargs):
        def _wrap(func):
            return func
        return _wrap

    class DummyBlueprint:
        def __init__(self, *_args, **_kwargs):
            pass
        route = get = post = _decorator

    flask_stub = types.SimpleNamespace(
        Blueprint=DummyBlueprint,
        current_app=None,
        jsonify=lambda *a, **k: None,
        render_template=lambda *a, **k: None,
        request=None,
        send_file=lambda *a, **k: None,
        send_from_directory=lambda *a, **k: None,
    )
    round_summary_stub = types.SimpleNamespace(generate_round_summaries=lambda *a, **k: None)
    monkeypatch.setitem(sys.modules, "flask", flask_stub)
    monkeypatch.setitem(sys.modules, "round_summary", round_summary_stub)
    import routes.api_routes as api_routes
    monkeypatch.setattr(api_routes.api_routes, "BASE_DIR", tmp_path, raising=False)
    return api_routes


def test_append_performance_with_malformed_json(tmp_path, monkeypatch, caplog):
    api_routes = _setup_api_routes(monkeypatch, tmp_path)
    perf_path = tmp_path / "FightControl" / "data" / "performance_results.json"
    perf_path.parent.mkdir(parents=True, exist_ok=True)
    perf_path.write_text("{not valid json")
    with caplog.at_level("WARNING"):
        api_routes._append_performance("Tester", {"speed": 42})
    data = json.loads(perf_path.read_text())
    assert data == [{"fighter_name": "Tester", "performance": {"speed": 42}}]
    assert "Failed to decode" in caplog.text
