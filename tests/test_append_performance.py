import json

import routes.fighters as fighters
import sys
import types


def test_append_performance(tmp_path, monkeypatch):
    monkeypatch.setattr(fighters, "_fighters_json_path", lambda: tmp_path / "fighters.json")
    perf_path = tmp_path / "performance_results.json"
    perf_path.write_text(json.dumps([{"fighter_name": "Existing", "performance": {"speed": 111}}]))
    fighters._append_performance("Tester", {"speed": 123})
    data = json.loads(perf_path.read_text())
    assert {"fighter_name": "Tester", "performance": {"speed": 123}} in data
    assert {"fighter_name": "Existing", "performance": {"speed": 111}} in data


def test_append_performance_creates_directory(tmp_path, monkeypatch):
    perf_dir = tmp_path / "missing" / "sub"
    monkeypatch.setattr(fighters, "_fighters_json_path", lambda: perf_dir / "fighters.json")
    fighters._append_performance("Tester", {"speed": 456})
    perf_path = perf_dir / "performance_results.json"
    assert perf_dir.exists()
    assert json.loads(perf_path.read_text()) == [{"fighter_name": "Tester", "performance": {"speed": 456}}]


def test_append_performance_handles_malformed_json(tmp_path, monkeypatch):
    monkeypatch.setattr(fighters, "_fighters_json_path", lambda: tmp_path / "fighters.json")
    perf_path = tmp_path / "performance_results.json"
    perf_path.write_text("{bad json")
    fighters._append_performance("Tester", {"speed": 789})
    data = json.loads(perf_path.read_text())
    assert {"fighter_name": "Tester", "performance": {"speed": 789}} in data


def test_api_append_performance_handles_malformed_json(tmp_path, monkeypatch, caplog):
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
    perf_path = tmp_path / "FightControl" / "data" / "performance_results.json"
    perf_path.parent.mkdir(parents=True, exist_ok=True)
    perf_path.write_text("{bad json")
    with caplog.at_level("WARNING"):
        api_routes._append_performance("Tester", {"speed": 789})
    data = json.loads(perf_path.read_text())
    assert {"fighter_name": "Tester", "performance": {"speed": 789}} in data
    assert "Failed to decode" in caplog.text
