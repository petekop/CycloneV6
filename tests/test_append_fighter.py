import json

import routes.fighters as fighters


def test_append_fighter_handles_malformed_json(tmp_path, monkeypatch):
    fighter_path = tmp_path / "fighters.json"
    fighter_path.write_text("{broken")
    monkeypatch.setattr(fighters, "_fighters_json_path", lambda: fighter_path)
    fighters._append_fighter({"name": "Tester"})
    data = json.loads(fighter_path.read_text())
    assert {"name": "Tester"} in data
