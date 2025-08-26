import importlib
import json
import sys


def test_merge_preserves_existing_keys(tmp_path):
    rt = importlib.reload(importlib.import_module("round_timer"))
    merge = rt._merge_bout_metadata
    session_dir = tmp_path
    initial = {"max_hr": {"blue": 150, "red": 100}}
    (session_dir / "bout.json").write_text(json.dumps(initial))

    merge(session_dir, {"max_hr": {"red": 200}})

    merged = json.loads((session_dir / "bout.json").read_text())
    assert merged["max_hr"] == {"blue": 150, "red": 200}

    # Clean up to avoid impacting subsequent tests
    for mod in ["round_timer", "fight_state"]:
        sys.modules.pop(mod, None)
