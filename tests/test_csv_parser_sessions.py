import importlib
import sys
from pathlib import Path

import pytest

pd = pytest.importorskip("pandas")

BASE_DIR = Path(__file__).resolve().parents[1]


def test_convert_row_to_fighter_builds_sessions(tmp_path, monkeypatch):
    monkeypatch.setenv("BASE_DIR", str(tmp_path))

    from FightControl.scripts import csv_to_fighter_json as parser

    importlib.reload(parser)

    df = pd.DataFrame(
        {
            "Full Name": ["Alice"],
            "Weight Category (KG)": ["60"],
            "Height\n": ["170"],
            "Date of Birth": ["1990-01-01"],
            "Stance": ["Orthodox"],
            "MugShot": ["url"],
            "speed_2024-01-01": [10],
            "power_2024-01-01": [5],
            "speed_2024-02-01": [11],
            "power_2024-02-01": [6],
        }
    )

    fighters = parser.parse_dataframe(df)
    assert fighters == [
        {
            "name": "Alice",
            "weight": "60",
            "height": "170",
            "dob": "1990-01-01",
            "stance": "Orthodox",
            "photo": "url",
            "sessions": [
                {"date": "2024-01-01", "performance": {"speed": 10, "power": 5}},
                {"date": "2024-02-01", "performance": {"speed": 11, "power": 6}},
            ],
        }
    ]

    # Ensure later tests do not reuse these modules with a different BASE_DIR
    sys.modules.pop("FightControl.scripts.csv_to_fighter_json", None)
    sys.modules.pop("paths", None)
