"""Routes for creating fighter profiles.

The module provides a Flask :class:`~flask.Blueprint` for the ``/fighters``
endpoint and, when possible, registers the same handler directly on the
global :mod:`cyclone_server.app`.  Registration is skipped after the first
request or if the view already exists, preventing side effects during tests.
The endpoint accepts standard fighter metadata and an optional CSV file with
performance metrics.
"""

from __future__ import annotations

import csv
import importlib
import io
import json
import os
from pathlib import Path

try:
    from flask import Blueprint, abort, render_template
except ImportError:  # pragma: no cover - Flask is optional for tests
    Blueprint = None
    abort = None  # type: ignore
    render_template = None  # type: ignore

from FightControl.fight_utils import safe_filename
from utils.csv_parser import parse_row
from utils.fighters_index import _atomic_json_dump, rebuild_index

__all__ = ["rebuild_index"]

# Allowed fighter fields accepted from incoming requests. Any additional
# keys provided by the client are discarded so only recognised metadata is
# persisted alongside performance metrics.
ALLOWED_FIGHTER_FIELDS = {
    "name",
    "gender",
    "sex",
    "stance",
    "country",
    "age",
    "weight",
    "height",
    "range",
    "bodyFat",
    "body_fat_pct",
    "email",
    "weightClass",
}


_DEFAULT_BASE_DIR = Path(__file__).resolve().parents[1]


def _fighters_json_path() -> Path:
    """Return the path to ``fighters.json`` honouring ``BASE_DIR`` overrides.

    ``routes.fighters`` is imported early in a number of tests where the
    ``BASE_DIR`` environment variable is mutated multiple times.  Some tests
    expect the function to respect runtime changes, while others reload the
    :mod:`paths` module once and then restore ``BASE_DIR`` for the remainder of
    the run.  To balance these requirements the helper uses the environment
    variable only when :mod:`paths` still reports the default repository root;
    otherwise the path computed by :mod:`paths` takes precedence.
    """

    env_dir = os.environ.get("BASE_DIR")
    paths_mod = importlib.import_module("paths")
    base_dir = Path(getattr(paths_mod, "BASE_DIR", _DEFAULT_BASE_DIR))
    if base_dir == _DEFAULT_BASE_DIR and env_dir:
        return Path(env_dir) / "FightControl" / "data" / "fighters.json"
    return base_dir / "FightControl" / "data" / "fighters.json"


def _parse_metrics(csv_file) -> dict:
    """Return performance metrics parsed from an uploaded CSV file.

    The CSV may contain legacy or differently cased headers.  They are
    normalised to the canonical ``speed``, ``power``, ``endurance`` and ``bpm``
    keys.  All four headers are required; if any are missing a
    :class:`ValueError` is raised.
    """

    try:
        with io.TextIOWrapper(csv_file.stream, encoding="utf-8") as stream:
            reader = csv.DictReader(stream)
            row = next(reader, None)
            if not row:
                raise ValueError("empty csv")

            def _normalise(header: str) -> str:
                return header.strip().lower().replace(" ", "_").replace("-", "_")

            aliases = {
                "speed": "speed",
                "jump_height": "speed",
                "jump": "speed",
                "power": "power",
                "deadlift_est": "power",
                "deadlift": "power",
                "endurance": "endurance",
                "yoyo_test": "endurance",
                "yoyo": "endurance",
                "bpm": "bpm",
                "hr_max": "bpm",
                "hrmax": "bpm",
            }

            normalised: dict[str, str] = {}
            for header, value in row.items():
                key = aliases.get(_normalise(header))
                if key and value not in (None, ""):
                    normalised[key] = value

            required = {"speed", "power", "endurance", "bpm"}
            if not required.issubset(normalised):
                raise ValueError("missing headers")

            metrics: dict[str, float] = {}
            for key in required:
                try:
                    metrics[key] = float(normalised[key])
                except (TypeError, ValueError):
                    raise ValueError("invalid value")

            return metrics
    except (UnicodeError, LookupError) as exc:  # pragma: no cover - defensive
        raise ValueError("invalid encoding") from exc


def _extract_fighter() -> dict:
    from flask import request

    """Normalise fighter data from the incoming request."""

    raw = request.form.to_dict() if request.form else (request.get_json(silent=True) or {})
    parsed = parse_row(raw)

    fighter = {k: v for k, v in parsed.items() if k in ALLOWED_FIGHTER_FIELDS and v not in (None, "")}
    # Normalise gender alias to the canonical "sex" field
    if "gender" in fighter and "sex" not in fighter:
        fighter["sex"] = fighter.pop("gender")

    performance: dict[str, float] = {}

    # Accept both legacy "csvFile" and current "metrics" field names.
    csv_file = request.files.get("csvFile") or request.files.get("metrics")
    if csv_file:
        performance.update(_parse_metrics(csv_file))

    # Metrics may also be supplied directly in JSON for manual entry.
    stats = raw.get("stats")
    if isinstance(stats, str):
        try:
            stats = json.loads(stats)
        except json.JSONDecodeError:
            stats = None
    if isinstance(stats, dict):
        for key in ("speed", "power", "endurance"):
            val = stats.get(key)
            try:
                if val not in (None, ""):
                    performance[key] = float(val)
            except (TypeError, ValueError):
                pass
        bpm_val = stats.get("bpm")
        if bpm_val not in (None, ""):
            try:
                performance["bpm"] = float(bpm_val)
            except (TypeError, ValueError):
                pass

    for key in ("speed", "power", "endurance"):
        val = raw.get(key)
        try:
            if val not in (None, ""):
                performance.setdefault(key, float(val))
        except (TypeError, ValueError):
            pass

    bpm_val = raw.get("bpm")
    if bpm_val in (None, ""):
        bpm_val = raw.get("hr_max")
    if bpm_val not in (None, ""):
        try:
            performance.setdefault("bpm", float(bpm_val))
        except (TypeError, ValueError):
            pass

    if performance:
        fighter["performance"] = performance

    return fighter


def _append_fighter(fighter: dict) -> None:
    """Append ``fighter`` to ``fighters.json``."""

    path = _fighters_json_path()
    fighters = []
    if path.exists():
        try:
            fighters = json.loads(path.read_text())
        except json.JSONDecodeError:
            fighters = []
    fighters.append(fighter)
    _atomic_json_dump(fighters, path)


def _append_performance(name: str, performance: dict) -> None:
    """Log ``performance`` for ``name`` to ``performance_results.json``."""
    # Build the performance log path relative to the fighters JSON file
    perf_path = _fighters_json_path().with_name("performance_results.json")
    perf_path.parent.mkdir(parents=True, exist_ok=True)
    entries = []
    if perf_path.exists():
        try:
            entries = json.loads(perf_path.read_text())
        except json.JSONDecodeError:
            entries = []
    if not isinstance(entries, list):
        entries = []
    entries.append({"fighter_name": name, "performance": performance})
    perf_path.write_text(json.dumps(entries, indent=2))


def _load_fighter_detail(safe_name: str) -> tuple[dict, dict, str | None]:
    """Return profile, chart data and card image URL for ``safe_name``.

    The ``safe_name`` is sanitised to prevent path traversal. Missing
    ``profile.json`` files result in :class:`FileNotFoundError`.
    """

    safe = safe_filename(safe_name)
    fighter_dir = _fighters_json_path().parent.parent / "fighter_data" / safe

    profile_path = fighter_dir / "profile.json"
    if not profile_path.exists():
        raise FileNotFoundError
    profile = json.loads(profile_path.read_text(encoding="utf-8"))

    charts: dict = {}
    charts_path = fighter_dir / "charts.json"
    if charts_path.exists():
        try:
            charts = json.loads(charts_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            charts = {}

    card_url: str | None = None
    card_path = fighter_dir / "card_full.png"
    if card_path.exists():
        card_url = f"/fighter_data/{safe}/card_full.png"

    return profile, charts, card_url


def _render_fighter_page(safe_name: str):
    if render_template is None or abort is None:  # pragma: no cover - safety
        raise RuntimeError("Flask is required for rendering fighter pages")
    try:
        profile, charts, card_url = _load_fighter_detail(safe_name)
    except FileNotFoundError:
        return abort(404)
    return render_template(
        "touchportal/fighter_detail.html",
        profile=profile,
        charts=charts,
        card_url=card_url,
        safe_name=safe_name,
    )


# Blueprint registration ----------------------------------------------------
if Blueprint is not None:
    fighters_bp = Blueprint("fighters", __name__)

    @fighters_bp.route("/fighters", methods=["POST"])
    def add_fighter_bp():
        """Blueprint route to create a fighter."""

        from flask import jsonify

        try:
            fighter = _extract_fighter()
        except ValueError:
            return jsonify(status="error", error="Invalid metrics CSV"), 400
        _append_fighter(fighter)
        if (perf := fighter.get("performance")) and fighter.get("name"):
            _append_performance(fighter["name"], perf)
        return jsonify(status="success", fighter=fighter), 201

    @fighters_bp.route("/fighters/<safe_name>")
    def fighter_page_bp(safe_name: str):
        """Render the fighter detail page for ``safe_name``."""

        return _render_fighter_page(safe_name)

else:  # pragma: no cover - Flask not installed
    fighters_bp = None


# Direct application route --------------------------------------------------

try:  # Import the global Flask app if available
    from cyclone_server import app
except Exception:  # pragma: no cover - allows import without full app context
    app = None


if (
    app is not None
    and not getattr(app, "_got_first_request", False)
    and "add_fighter" not in getattr(app, "view_functions", {})
):

    @app.route("/fighters", methods=["POST"])
    def add_fighter():  # pragma: no cover - thin wrapper
        from flask import jsonify

        try:
            fighter = _extract_fighter()
        except ValueError:
            return jsonify(status="error", error="Invalid metrics CSV"), 400
        _append_fighter(fighter)
        if (perf := fighter.get("performance")) and fighter.get("name"):
            _append_performance(fighter["name"], perf)
        return jsonify(status="success", fighter=fighter), 201


if (
    app is not None
    and not getattr(app, "_got_first_request", False)
    and "fighter_page" not in getattr(app, "view_functions", {})
):

    @app.route("/fighters/<safe_name>")
    def fighter_page(safe_name: str):  # pragma: no cover - thin wrapper
        return _render_fighter_page(safe_name)
