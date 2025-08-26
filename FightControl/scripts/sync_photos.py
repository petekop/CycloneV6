import sys
from pathlib import Path

FIGHTCONTROL_DIR = Path(__file__).resolve().parents[1]
if str(FIGHTCONTROL_DIR) not in sys.path:
    sys.path.insert(0, str(FIGHTCONTROL_DIR))
REPO_ROOT = FIGHTCONTROL_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import json
from urllib.parse import parse_qs, urlparse

import requests

from paths import BASE_DIR

# Date: 2025-07-19


BASE_FC_DIR = BASE_DIR / "FightControl"
DATA_FOLDER = BASE_FC_DIR / "data"
PHOTO_FOLDER = DATA_FOLDER / "photos"
JSON_PATH = DATA_FOLDER / "fighters.json"

PHOTO_FOLDER.mkdir(parents=True, exist_ok=True)

# Load JSON
with open(JSON_PATH, "r") as f:
    fighters = json.load(f)


def extract_file_id(google_url):
    if "drive.google.com" not in google_url:
        return None
    parsed = urlparse(google_url)
    if "/file/d/" in google_url:
        return google_url.split("/file/d/")[1].split("/")[0]
    elif "id=" in google_url:
        return parse_qs(parsed.query).get("id", [None])[0]
    return None


def download_image(file_id, dest_path):
    dl_url = f"https://drive.google.com/uc?export=download&id={file_id}"
    try:
        r = requests.get(dl_url, stream=True)
        if r.status_code == 200:
            with open(dest_path, "wb") as f:
                for chunk in r.iter_content(1024):
                    f.write(chunk)
            return True
    except Exception as e:
        print(f"❌ Failed to download {file_id}: {e}")
    return False


# Process each fighter
for f in fighters:
    name_slug = f["name"].lower().replace(" ", "_")
    file_id = extract_file_id(f.get("photo", ""))
    if file_id:
        photo_path = PHOTO_FOLDER / f"{name_slug}.jpg"
        if not photo_path.exists():
            print(f"⬇️  Downloading photo for: {f['name']}")
            if download_image(file_id, photo_path):
                f["photo_local"] = str(photo_path.relative_to(BASE_FC_DIR))
            else:
                f["photo_local"] = ""
        else:
            f["photo_local"] = str(photo_path.relative_to(BASE_FC_DIR))
    else:
        f["photo_local"] = ""

# Save updated JSON
with open(JSON_PATH, "w") as f:
    json.dump(fighters, f, indent=2)

print("✅ All photos processed and JSON updated.")
