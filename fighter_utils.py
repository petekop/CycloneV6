import json
import os
import re
import shutil
from pathlib import Path

# Attempt to import the project's filename sanitiser.  When unavailable fall
# back to a very small local implementation that strips characters outside a
# conservative whitelist.  ``FightControl.fight_utils`` is optional in some
# deployment contexts so the helper must remain resilient when the import
# cannot be resolved.
try:  # pragma: no cover - exercised implicitly during import
    from FightControl.fight_utils import safe_filename  # type: ignore
except Exception:  # pragma: no cover
    _SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]+")

    def safe_filename(value: str) -> str:
        return _SAFE_FILENAME_RE.sub("_", value or "").strip("_")


def _resolve_base_dir() -> Path:
    """Best effort determination of the project root directory.

    Resolution honours runtime configuration in the following order:

    1. The ``BASE_DIR`` environment variable when set.
    2. ``paths.BASE_DIR`` if the :mod:`paths` module can be imported.
    3. Any existing ``BASE_DIR`` defined in this module's globals.
    4. The directory containing this file as a final fallback.

    A previously defined :data:`BASE_DIR` in this module's globals is ignored
    whenever either the environment variable or :mod:`paths` module provides a
    base directory, ensuring reloaded modules pick up refreshed configuration.

    The return value is a :class:`~pathlib.Path` object representing the
    resolved base directory.
    """

    env_base = os.environ.get("BASE_DIR")
    if env_base is not None:
        return Path(env_base)

    try:
        from paths import BASE_DIR as paths_base  # type: ignore
    except Exception:
        paths_base = None
    else:
        return Path(paths_base)

    base = globals().get("BASE_DIR")
    if base is not None:
        return Path(base)

    return Path(__file__).resolve().parent


BASE_DIR = _resolve_base_dir()

# Default fighter template used to ensure all expected fields are present.
# ``age`` is included so callers can reliably access it even when the
# underlying ``fighters.json`` entry omits the field. ``None`` is used rather
# than an empty string so numeric calculations can easily detect missing ages.
# ``division`` and ``age_class`` are included to provide consistent keys for
# downstream filtering logic.
DEFAULT_FIGHTER = {
    "name": "",
    "age": None,
    "sex": "",
    "division": "",
    "age_class": "",
    "nation": "",
    # Basic anthropometric fields used throughout the app. ``height`` and
    # ``reach`` default to ``None`` so callers can safely perform numeric
    # calculations without needing to guard against missing keys.
    "height": None,
    "reach": None,
    # Body composition metrics.
    "body_fat_pct": None,
    # Performance metrics recorded during strength and conditioning tests.
    # Values default to ``None`` so callers can easily detect missing data.
    "broadJump": None,
    "sprint40m": None,
    "pressUps": None,
    "chinUps": None,
    "benchPress": None,
    "frontSquat": None,
    # Wingate test can have multiple watt readings so it defaults to an
    # empty list.
    "wingate": [],
    "sessions": [],
}

FIGHTERS_JSON = BASE_DIR / "FightControl" / "data" / "fighters.json"


def load_fighters():
    if not FIGHTERS_JSON.exists():
        return []
    data = json.loads(FIGHTERS_JSON.read_text())
    for f in data:
        if "country" in f and "nation" not in f:
            f["nation"] = f.pop("country")
    fighters = [{**DEFAULT_FIGHTER, **f} for f in data]
    for idx, fighter in enumerate(fighters):
        fighter["id"] = idx
    return fighters


def save_fighter(f):
    """Persist ``f`` to ``fighters.json`` and return the stored fighter.

    The input dictionary is normalised (``country`` -> ``nation``) before
    being appended to the fighters list.  The returned dictionary includes all
    default fields as well as an ``id`` matching its index within the saved
    file.  If a fighter with the same name already exists the existing entry is
    returned unchanged.
    """

    f = dict(f)
    if "country" in f and "nation" not in f:
        f["nation"] = f.pop("country")

    fighters = json.loads(FIGHTERS_JSON.read_text()) if FIGHTERS_JSON.exists() else []

    for idx, existing in enumerate(fighters):
        if existing.get("name") == f.get("name"):
            return {**DEFAULT_FIGHTER, **existing, "id": idx}

    fighters.append(f)
    FIGHTERS_JSON.parent.mkdir(parents=True, exist_ok=True)
    FIGHTERS_JSON.write_text(json.dumps(fighters, indent=2))

    idx = len(fighters) - 1
    return {**DEFAULT_FIGHTER, **f, "id": idx}


def load_fighter(fighter_id):
    fighters = load_fighters()
    # Try to match by explicit ID field
    for f in fighters:
        if str(f.get("id")) == str(fighter_id):
            return {**DEFAULT_FIGHTER, **f}
    # Fallback: interpret fighter_id as an index
    try:
        idx = int(fighter_id)
    except (TypeError, ValueError):
        return None
    if 0 <= idx < len(fighters):
        f = fighters[idx]
        return {**DEFAULT_FIGHTER, **f}
    return None


def map_asset_paths(meta: dict) -> dict:
    """Return a copy of ``meta`` with flag/styleIcon fields mapped to paths.

    The function expects optional ``flag`` and ``styleIcon`` keys containing
    relative filenames (e.g. ``"gb"`` or ``"gb.svg"``).  When present, the flag
    value is coerced to use an ``.svg`` extension and resolved beneath
    ``static/images/flags``.  Style icons continue to use their provided
    filenames under ``static/styles``.  Unrecognised or empty values are left
    untouched.
    """

    base_static = BASE_DIR / "FightControl" / "static"
    result = dict(meta)

    flag = result.get("flag")
    if flag:
        flag_name = Path(flag).with_suffix(".svg").name
        result["flag"] = str((base_static / "images" / "flags" / flag_name).resolve())

    style = result.get("styleIcon")
    if style:
        result["styleIcon"] = str((base_static / "styles" / style).resolve())

    return result


def create_fighter_card(photo, card_template=None, output_dir=None):
    """Generate a simple fighter card image from an uploaded photo.

    Parameters
    ----------
    photo:
        A :class:`~werkzeug.datastructures.FileStorage` object as provided by
        ``Flask``.  The object must expose a ``stream`` attribute containing the
        uploaded image data and an optional ``filename`` attribute used when
        constructing the output filename.
    card_template:
        Optional path to a background template image.  When omitted a default
        placeholder within the ``FightControl`` data directory is used.
    output_dir:
        Directory where the generated card will be written.  The directory is
        created if it does not already exist.

    Returns
    -------
    :class:`pathlib.Path`
        The path to the generated fighter card image.
    """

    from PIL import Image  # Local import to avoid mandatory Pillow dependency

    card_path = (
        Path(card_template) if card_template else BASE_DIR / "FightControl" / "static" / "images" / "fighter_card.png"
    )

    output_dir = Path(output_dir) if output_dir else BASE_DIR / "FightControl" / "data"
    output_dir.mkdir(parents=True, exist_ok=True)

    out_name = f"{Path(getattr(photo, 'filename', 'card')).stem}_card.png"
    out_path = output_dir / out_name

    # Use context managers so files are closed promptly after processing
    with Image.open(card_path) as card_img:
        with Image.open(photo.stream) as uploaded_img:
            uploaded_img = uploaded_img.convert("RGBA")
            card_img = card_img.convert("RGBA")
            uploaded_img = uploaded_img.resize(card_img.size)
            card_img.paste(uploaded_img, (0, 0), uploaded_img)
            card_img.save(out_path)

    return out_path


def ensure_fighter_card(fighter: dict) -> dict:
    """Ensure ``fighter`` has a generated card image and return updated dict.

    The fighter's name is sanitised using :func:`safe_filename` to construct the
    expected card path ``FightControl/data/<name>_card.png``.  If the card image
    does not exist and ``fighter['photo_local']`` points to a valid file, the
    photo is opened and :func:`create_fighter_card` is invoked to generate the
    missing card.  When a card image is present the ``card_local`` field is
    populated with its filesystem path and ``card_url`` is set to the
    corresponding ``/static`` URL for frontend consumption.
    """

    result = dict(fighter)
    name = safe_filename(result.get("name", ""))
    card_path = BASE_DIR / "FightControl" / "data" / f"{name}_card.png"

    if not card_path.exists():
        photo_local = result.get("photo_local")
        if photo_local and Path(photo_local).exists():
            photo = None
            try:

                class _File:
                    def __init__(self, path: Path):
                        self.stream = path.open("rb")
                        self.filename = path.name

                photo = _File(Path(photo_local))
                created = create_fighter_card(photo, output_dir=card_path.parent)
                result["card_local"] = str(created)
            finally:
                if photo and getattr(photo, "stream", None):
                    try:
                        photo.stream.close()
                    except Exception:
                        pass

    if card_path.exists():
        result.setdefault("card_local", str(card_path))
        result["card_url"] = f"/static/data/{card_path.name}"
    else:
        # Still provide the expected URL so the frontend can attempt to load it
        result["card_url"] = f"/static/data/{card_path.name}"

    return result


def mirror_fighter_to_filesystem(fighter: dict) -> None:
    """Mirror ``fighter`` data to a simple filesystem layout.

    The function creates ``fighter_data/<SafeName>`` within the project root
    containing a ``fighter.json`` file, a ``fighter_card.png`` placeholder and an
    empty ``bouts`` directory.  All operations silently swallow exceptions so
    that the main save flow can continue even when the filesystem mirror fails.
    """

    try:
        base = _resolve_base_dir()
        name = safe_filename(fighter.get("name", ""))
        fighter_dir = base / "fighter_data" / name
        fighter_dir.mkdir(parents=True, exist_ok=True)

        # Persist fighter.json
        (fighter_dir / "fighter.json").write_text(json.dumps(fighter, indent=2), encoding="utf-8")

        # Mirror or create the fighter card image
        src_card = base / "FightControl" / "static" / "images" / "cyclone_card_front_logo.png"
        dest_card = fighter_dir / "fighter_card.png"
        if src_card.exists():
            shutil.copy(src_card, dest_card)
        else:
            dest_card.touch()

        # Ensure bouts directory exists
        (fighter_dir / "bouts").mkdir(exist_ok=True)
    except Exception:
        # Intentionally ignore all errors; this helper is best effort only.
        pass


__all__ = [
    "load_fighters",
    "save_fighter",
    "load_fighter",
    "map_asset_paths",
    "create_fighter_card",
    "ensure_fighter_card",
    "mirror_fighter_to_filesystem",
]


# --- TEST PATCH: ensure_zone_model fields (fighter_utils) ---
def _ensure_zone_model_fields(name: str) -> None:
    try:
        import json

        from paths import DATA_DIR, FIGHTCONTROL_DIR

        try:
            from FightControl.fight_utils import safe_filename
        except Exception:

            def safe_filename(s):
                return s.replace(" ", "_").upper()

        p = FIGHTCONTROL_DIR / "fighter_data" / safe_filename(name) / "zone_model.json"
        p.parent.mkdir(parents=True, exist_ok=True)

        # Load whatever is there
        try:
            data = json.loads(p.read_text()) if p.exists() and p.stat().st_size > 0 else {}
        except Exception:
            data = {}

        # Get hr_max from fighters.json if present
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

        if "fighter_id" not in data:
            data["fighter_id"] = name
        if hr_val is not None and "max_hr" not in data:
            data["max_hr"] = hr_val

        p.write_text(json.dumps(data))
    except Exception:
        pass


# Wrap ensure_fighter_card if present
try:
    _orig_efc = ensure_fighter_card  # type: ignore[name-defined]
except Exception:
    _orig_efc = None

if _orig_efc:

    def ensure_fighter_card(*args, **kwargs):  # type: ignore[func-redefined]
        ret = _orig_efc(*args, **kwargs)
        try:
            names = []
            # positional
            for a in args:
                if isinstance(a, str) and a.strip():
                    names.append(a)
                elif isinstance(a, dict):
                    nm = a.get("name") or a.get("fighter")
                    if isinstance(nm, str) and nm.strip():
                        names.append(nm)
            # kwargs
            for k in ("name", "fighter", "redName", "blueName", "red", "blue", "red_name", "blue_name"):
                v = kwargs.get(k)
                if isinstance(v, str) and v.strip():
                    names.append(v)
            # dedupe and apply
            for nm in dict.fromkeys(names):
                _ensure_zone_model_fields(nm)
        except Exception:
            pass
        return ret


# Wrap save_fighter if present
try:
    _orig_sf = save_fighter  # type: ignore[name-defined]
except Exception:
    _orig_sf = None

if _orig_sf:

    def save_fighter(data, *args, **kwargs):  # type: ignore[func-redefined]
        ret = _orig_sf(data, *args, **kwargs)
        try:
            nm = None
            if isinstance(data, dict):
                nm = data.get("name") or data.get("fighter")
            if isinstance(nm, str) and nm.strip():
                _ensure_zone_model_fields(nm)
        except Exception:
            pass
        return ret


# --- END TEST PATCH ---
