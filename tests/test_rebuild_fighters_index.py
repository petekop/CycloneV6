import json

import scripts.rebuild_fighters_index as rfi


def test_rebuild_fighters_index(tmp_path, monkeypatch):
    fighter_dir = tmp_path / "FightControl" / "fighter_data"
    (fighter_dir / "Alice").mkdir(parents=True)
    (fighter_dir / "Alice" / "profile.json").write_text(json.dumps({"name": "Alice"}))
    (fighter_dir / "Bob").mkdir(parents=True)
    (fighter_dir / "Bob" / "profile.json").write_text(json.dumps({"name": "Bob"}))

    output = tmp_path / "FightControl" / "data" / "fighters.json"
    monkeypatch.setattr(rfi, "FIGHTER_DATA_DIR", fighter_dir)
    monkeypatch.setattr(rfi, "OUTPUT_PATH", output)

    rfi.main()

    data = json.loads(output.read_text())
    assert data == [{"name": "Alice"}, {"name": "Bob"}]
