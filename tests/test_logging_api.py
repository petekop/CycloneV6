import csv
import importlib
import json
import os
from pathlib import Path

import pytest

import paths
from FightControl.fight_utils import safe_filename

pytest.importorskip("flask")
pytestmark = pytest.mark.usefixtures("stub_optional_dependencies")

BASE_DIR = Path(__file__).resolve().parents[1]


def setup_app(tmp_path: Path):
    os.environ["BASE_DIR"] = str(tmp_path)

    data_dir = tmp_path / "FightControl" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    fight = {"red_fighter": "Red Fighter", "blue_fighter": "Blue Fighter", "fight_date": "2099-01-01"}
    (data_dir / "current_fight.json").write_text(json.dumps(fight))
    (data_dir / "current_round.txt").write_text("round_1")

    import fight_state

    paths.refresh_paths()
    importlib.reload(fight_state)

    import cyclone_server
    importlib.reload(cyclone_server)

    cyclone_server.app.config["TESTING"] = True
    client = cyclone_server.app.test_client()

    os.environ["BASE_DIR"] = str(BASE_DIR)
    return client


def bout_name(red: str = "Red Fighter", blue: str = "Blue Fighter", date: str = "2099-01-01") -> str:
    import utils_checks

    return (
        f"{date}_{safe_filename(red).upper()}_vs_{safe_filename(blue).upper()}_BOUT"
        f"{utils_checks.next_bout_number(date, red, blue) - 1}"
    )


def test_both_endpoints_write_same_file(tmp_path, boot_template, stub_utils_checks):
    client = setup_app(tmp_path)

    import cyclone_server
    import FightControl.routes.tags as tags_module
    from utils.csv_writer import DebouncedCsvWriter

    expected_path = (
        paths.BASE_DIR
        / "FightControl"
        / "logs"
        / "2099-01-01"
        / bout_name()
        / "round_1"
        / "coach_notes.csv"
    )

    class DummyManager:
        def __init__(self, path):
            self.writer = DebouncedCsvWriter(path, tags_module.FIELDS)

        def log(self, row):
            self.writer.write_row(row)
            return True

    dummy = DummyManager(expected_path)
    cyclone_server.tag_log_manager = dummy
    tags_module.tag_log_manager = dummy

    resp = client.post("/api/log-tag", json={"fighter": "red", "tag": "Jab"})
    assert resp.status_code == 200

    resp = client.post("/api/tags/log", json={"button_id": "b1", "state": "press"})
    assert resp.status_code == 200

    dummy.writer.close()
    assert expected_path.exists()
    with expected_path.open() as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == tags_module.FIELDS
        rows = list(reader)
    assert len(rows) == 2
    assert rows[0]["label"] == "Jab"
    assert rows[1]["button_id"] == "b1"


def test_log_tag_invalid_fighter(tmp_path, boot_template, stub_utils_checks):
    client = setup_app(tmp_path)
    resp = client.post("/api/log-tag", json={"fighter": "green", "tag": "Jab"})
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["status"] == "error"
