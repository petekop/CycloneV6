import json

from utils.fighters_index import rebuild_index


def test_rebuild_index(tmp_path):
    fighter_dir = tmp_path / "FightControl" / "fighter_data"
    (fighter_dir / "Alice").mkdir(parents=True)
    (fighter_dir / "Alice" / "profile.json").write_text(json.dumps({"name": "Alice"}))
    (fighter_dir / "Bob").mkdir(parents=True)
    (fighter_dir / "Bob" / "profile.json").write_text(json.dumps({"name": "Bob"}))

    output = tmp_path / "FightControl" / "data" / "fighters.json"
    rebuild_index(fighter_dir, output)

    data = json.loads(output.read_text())
    assert data == [{"name": "Alice"}, {"name": "Bob"}]
