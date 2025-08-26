import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path

import round_outputs


def test_move_outputs_creates_round_meta(tmp_path, monkeypatch):
    monkeypatch.setattr(round_outputs, "BASE_DIR", tmp_path)
    monkeypatch.setattr(round_outputs, "CONFIG", {})
    monkeypatch.setattr(round_outputs, "safe_filename", lambda n: n)

    def fake_move(cfg, meta):
        p = tmp_path / "moved.mp4"
        p.write_text("x")
        return [p]

    monkeypatch.setattr(round_outputs, "_move_outputs_sync", fake_move)

    date = "2025-01-01"
    for fighter in ("Red", "Blue"):
        rdir = tmp_path / "FightControl" / "fighter_data" / fighter / date / "round_1"
        rdir.mkdir(parents=True, exist_ok=True)
        (rdir / "hr_log.csv").write_text("0,100\n1,110\n")
        (rdir / "tags.csv").write_text("tag,ts\na,1\nb,2\n")

    start = datetime.utcnow() - timedelta(seconds=5)
    meta = {
        "fight_id": "F1",
        "round_no": 1,
        "red_name": "Red",
        "blue_name": "Blue",
        "date": date,
        "start": start.isoformat(),
    }
    asyncio.run(round_outputs.move_outputs_for_round(meta))

    meta_path = tmp_path / "FightControl" / "fighter_data" / "Red" / date / "round_1" / "round_meta.json"
    assert meta_path.exists()
    data = json.loads(meta_path.read_text())
    assert data["files"] == [str(tmp_path / "moved.mp4")]
    assert data["tags_count"] == 2
    assert data["hr_stats"]["min"] == 100
    assert data["hr_stats"]["max"] == 110
    assert data["duration_s"] >= 5
    blue_meta = tmp_path / "FightControl" / "fighter_data" / "Blue" / date / "round_1" / "round_meta.json"
    assert blue_meta.exists()


def test_move_outputs_logs_error_and_continues(tmp_path, monkeypatch, caplog):
    monkeypatch.setattr(round_outputs, "BASE_DIR", tmp_path)
    monkeypatch.setattr(round_outputs, "CONFIG", {})
    monkeypatch.setattr(round_outputs, "safe_filename", lambda n: n)

    def fake_move(cfg, meta):
        p = tmp_path / "moved.mp4"
        p.write_text("x")
        return [p]

    monkeypatch.setattr(round_outputs, "_move_outputs_sync", fake_move)

    date = "2025-01-01"
    for fighter in ("Red", "Blue"):
        rdir = tmp_path / "FightControl" / "fighter_data" / fighter / date / "round_1"
        rdir.mkdir(parents=True, exist_ok=True)

    original_write = Path.write_text

    def fail_write(self, data, *args, **kwargs):
        if "Red" in str(self):
            raise OSError("boom")
        return original_write(self, data, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", fail_write)

    meta = {
        "fight_id": "F1",
        "round_no": 1,
        "red_name": "Red",
        "blue_name": "Blue",
        "date": date,
        "start": datetime.utcnow().isoformat(),
    }

    with caplog.at_level("ERROR"):
        asyncio.run(round_outputs.move_outputs_for_round(meta))

    red_meta = tmp_path / "FightControl" / "fighter_data" / "Red" / date / "round_1" / "round_meta.json"
    blue_meta = tmp_path / "FightControl" / "fighter_data" / "Blue" / date / "round_1" / "round_meta.json"
    assert not red_meta.exists()
    assert blue_meta.exists()
    assert any("Failed to write round meta" in r.message for r in caplog.records)
