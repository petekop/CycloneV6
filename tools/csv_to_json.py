import argparse
import csv
import json
from typing import Iterable, List, Optional


def csv_to_json(csv_filepath: str, json_filepath: str, numeric_columns: Optional[Iterable[int]] = None) -> None:
    """Convert a CSV file to a JSON file."""
    numeric_columns = set(numeric_columns or [])
    data: List[dict] = []
    with open(csv_filepath, "r", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            for index in numeric_columns:
                try:
                    field = reader.fieldnames[index]
                except (IndexError, TypeError):
                    continue
                try:
                    row[field] = float(row[field])
                except (ValueError, KeyError):
                    pass

            # Collect Wingate Row interval power values into a list under performance
            wingate_cols = [f"Wingate Row Interval {i} Power (Watts)" for i in range(1, 9)]
            wingate_power: List[float] = []
            for col in wingate_cols:
                value = row.pop(col, None)
                if value in (None, ""):
                    continue
                try:
                    wingate_power.append(float(value))
                except ValueError:
                    continue
            if wingate_power:
                perf = row.get("performance")
                if isinstance(perf, dict):
                    perf["wingatePower"] = wingate_power
                else:
                    row["performance"] = {"wingatePower": wingate_power}

            data.append(row)

    with open(json_filepath, "w", encoding="utf-8") as jsonfile:
        json.dump(data, jsonfile, indent=4)


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert CSV to JSON.")
    parser.add_argument("csv_file", help="Path to the input CSV file")
    parser.add_argument("json_file", help="Path to the output JSON file")
    parser.add_argument(
        "-n",
        "--numeric",
        nargs="*",
        type=int,
        default=None,
        help="Indices of columns to treat as numeric (0-based)",
    )
    args = parser.parse_args()

    csv_to_json(args.csv_file, args.json_file, numeric_columns=args.numeric)


if __name__ == "__main__":
    main()
