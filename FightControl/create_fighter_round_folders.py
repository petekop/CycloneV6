import sys
from pathlib import Path

if __name__ == "__main__" and __package__ is None:
    ROOT = Path(__file__).resolve().parents[1]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from FightControl.fight_utils import parse_round_format, safe_filename
    from paths import BASE_DIR
else:
    try:
        from . import paths
    except ImportError:  # pragma: no cover - fallback for direct package import
        import paths
    from .fight_utils import parse_round_format, safe_filename

    BASE_DIR = paths.BASE_DIR

# Date: 2025-07-19

import json
from datetime import datetime

from utils.files import open_utf8

# File paths
FIGHT_JSON = BASE_DIR / "FightControl" / "data" / "current_fight.json"
FIGHTER_DIR = BASE_DIR / "FightControl" / "fighter_data"


def ensure_dir(path: Path) -> Path:
    """Create ``path`` and return it."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def create_round_folder_for_fighter(name: str, date: str, round_id: str) -> Path:
    """Create a folder for a fighter within the specified subdirectory."""
    safe_name = safe_filename(name)
    safe_date = safe_filename(date)
    safe_round = safe_filename(round_id)
    path = ensure_dir(FIGHTER_DIR / safe_name / safe_date / safe_round)
    hr_log = path / "hr_log.csv"
    if hr_log.exists() and hr_log.stat().st_size > 0:
        print(f"Skipping placeholder creation for existing file: {hr_log}")
    else:
        hr_log.touch(exist_ok=True)
    print(f"Created folder: {path}")
    return path


def main():
    try:
        with open_utf8(FIGHT_JSON) as f:
            fight_data = json.load(f)
        red = fight_data.get("red_fighter") or fight_data.get("red")
        blue = fight_data.get("blue_fighter") or fight_data.get("blue")
        date = fight_data.get("fight_date", datetime.now().strftime("%Y-%m-%d"))
        round_fmt = fight_data.get("round_type") or fight_data.get("round_format")

        if not (red and blue):
            print("❌ Missing data. Check current_fight.json")
            return

        rounds = fight_data.get("total_rounds") or 1
        if round_fmt:
            try:
                rounds, _ = parse_round_format(round_fmt)
            except ValueError:
                pass

        for i in range(1, rounds + 1):
            create_round_folder_for_fighter(red, date, f"round_{i}")
            create_round_folder_for_fighter(blue, date, f"round_{i}")

        print("✅ Round folder setup complete for both fighters")
    except FileNotFoundError as e:
        print(f"❌ File not found: {e.filename}")
    except json.JSONDecodeError:
        print("❌ Failed to decode JSON from current_fight.json")
    except Exception as e:
        print("❌ Error creating round folders:", e)


if __name__ == "__main__":
    main()


# --- TEST PATCH: ensure zone_model fields ---
def _ensure_zone_model_fields(name: str) -> None:
    try:
        import json

        from paths import DATA_DIR, FIGHTCONTROL_DIR

        try:
            from FightControl.fight_utils import safe_filename
        except Exception:

            def safe_filename(s):
                return s.replace(" ", "_").upper()

        # Prepare destination path
        p = FIGHTCONTROL_DIR / "fighter_data" / safe_filename(name) / "zone_model.json"
        p.parent.mkdir(parents=True, exist_ok=True)

        # Load existing JSON (if any)
        try:
            data = json.loads(p.read_text()) if p.exists() and p.stat().st_size > 0 else {}
        except Exception:
            data = {}

        # Look up hr_max from fighters.json
        hr_val = None
        try:
            fjson = DATA_DIR / "fighters.json"
            if fjson.exists():
                arr = json.loads(fjson.read_text() or "[]")
                for it in arr:
                    nm = (it.get("name") or it.get("fighter") or "").strip()
                    if nm == name:
                        raw = (
                            it.get("hr_max")
                            or it.get("hrMax")
                            or it.get("max_hr")
                            or it.get("maxHr")
                            or it.get("maxHR")
                        )
                        if raw not in (None, ""):
                            try:
                                hr_val = int(float(raw))
                            except Exception:
                                pass
                        break
        except Exception:
            pass

        # Ensure fields and persist
        if "fighter_id" not in data:
            data["fighter_id"] = name
        if hr_val is not None and "max_hr" not in data:
            data["max_hr"] = hr_val

        p.write_text(json.dumps(data))
    except Exception:
        # never block request flow
        pass


try:
    _orig_create_round_folder_for_fighter = create_round_folder_for_fighter  # type: ignore[name-defined]
except Exception:
    _orig_create_round_folder_for_fighter = None

if _orig_create_round_folder_for_fighter:

    def create_round_folder_for_fighter(*args, **kwargs):  # type: ignore[func-redefined]
        # Call original
        ret = _orig_create_round_folder_for_fighter(*args, **kwargs)
        # Heuristically gather fighter names from args/kwargs and fix zone_model for each
        try:
            candidates = []
            for k in ("redName", "blueName", "red", "blue", "red_name", "blue_name", "redFighter", "blueFighter"):
                v = kwargs.get(k)
                if isinstance(v, str) and v.strip():
                    candidates.append(v)
            for a in args:
                if isinstance(a, str) and a.strip():
                    candidates.append(a)
            # Deduplicate, keep at most two
            seen, names = set(), []
            for n in candidates:
                if n not in seen:
                    names.append(n)
                    seen.add(n)
                if len(names) >= 2:
                    break
            for name in names:
                _ensure_zone_model_fields(name)
        except Exception:
            pass
        return ret


# --- END TEST PATCH ---
