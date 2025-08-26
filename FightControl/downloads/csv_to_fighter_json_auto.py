import json
from pathlib import Path

import pandas as pd

from paths import BASE_DIR

# Date: 2025-07-19


# Define paths
DOWNLOAD_FOLDER = BASE_DIR / "FightControl" / "downloads"
DEST_FOLDER = BASE_DIR / "FightControl" / "data"
OUTPUT_FILENAME = "fighters.json"

# Find most recent CSV file in download folder
csv_files = sorted(DOWNLOAD_FOLDER.glob("*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)

if not csv_files:
    print("❌ No CSV files found in the downloads folder.")
    exit()

latest_csv = csv_files[0]
print(f"[Cyclone] Found CSV: {latest_csv.name}")

# Load the CSV
df = pd.read_csv(latest_csv)


# Clean and convert the data
def convert_row_to_fighter(row):
    return {
        "name": row["Full Name"].strip(),
        "weight": row["Weight Category (KG)"].strip(),
        "height": row["Height\n"].strip().replace("cm", "").strip(),
        "dob": row["Date of Birth"].strip(),
        "stance": row["Stance"].strip(),
        "photo": row["MugShot"].strip(),
    }


fighters = [convert_row_to_fighter(row) for _, row in df.iterrows()]

# Save to fighters.json
DEST_FOLDER.mkdir(parents=True, exist_ok=True)
output_path = DEST_FOLDER / OUTPUT_FILENAME
with open(output_path, "w") as f:
    json.dump(fighters, f, indent=2)

# Delete the processed CSV
latest_csv.unlink()
print(f"✅ {len(fighters)} fighter(s) written to {output_path}")
print(f"🗑️ Deleted source file: {latest_csv.name}")
