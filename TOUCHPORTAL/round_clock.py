# Cyclone project
# round_clock.py
# Displays live round/rest countdown timer and writes to file for OBS

import json
import time

from FightControl.round_manager import round_status
from open_utf8 import open_utf8
from paths import BASE_DIR

# CONFIG
# Resolve paths relative to the Cyclone base directory.  The base directory
# can be overridden via the ``CYCLONE_BASE_DIR`` environment variable which is
# already respected by ``paths.BASE_DIR``.
ROUND_STATUS_FILE = BASE_DIR / "FightControl" / "data" / "round_status.json"
CLOCK_DISPLAY_FILE = BASE_DIR / "FightControl" / "live_data" / "round_clock.txt"

# Format: { "round": 1, "duration": 120, "rest": 60, "status": "LIVE", "start_time": "..." }
# ``start_time`` is omitted while the timer is in the ``WAITING`` state.


def load_round_config():
    data = round_status()
    return data or None


def write_clock_text(text):
    CLOCK_DISPLAY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open_utf8(CLOCK_DISPLAY_FILE, "w") as f:
        f.write(text)


def format_time(seconds):
    return time.strftime("%M:%S", time.gmtime(seconds))


def run_timer(round_time, rest_time):
    print(f"\n🟥 ROUND TIME: {round_time}s")
    for t in range(round_time, -1, -1):
        write_clock_text(f"ROUND\n{format_time(t)}")
        time.sleep(1)

    print("\n🟦 REST TIME")
    for t in range(rest_time, -1, -1):
        write_clock_text(f"REST\n{format_time(t)}")
        time.sleep(1)

    write_clock_text("IDLE")


def main():
    config = load_round_config()
    if not config:
        print("❌ round_status.json not found.")
        return

    round_time = int(config.get("duration", 120))
    rest_time = int(config.get("rest", 60))

    # Optional: update status to LIVE
    config["status"] = "LIVE"
    with open_utf8(ROUND_STATUS_FILE, "w") as f:
        json.dump(config, f, indent=2)

    run_timer(round_time, rest_time)


if __name__ == "__main__":
    main()
