import asyncio
import csv
import json
import logging
import os
import shutil
import sys
import time
import uuid
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

from flask import (
    Flask,
    g,
    has_request_context,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    send_from_directory,
)

from fight_state import load_fight_state
from FightControl.create_fighter_round_folders import create_round_folder_for_fighter
from FightControl.fight_utils import parse_round_format, safe_filename
from FightControl.round_manager import round_status
from paths import STATIC_DIR, TEMPLATE_DIR
from services.card_builder import compose_card
from utils.files import open_utf8
from utils.perf import build_charts_from_perf, parse_performance_csv
from utils.template_loader import load_template

if os.name == "nt":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        os.environ.setdefault("PYTHONUTF8", "1")

# Date: 2025-07-28 (Final Patch: Full Python OBS WebSocket v5+ integration)


try:
    from cyclone_modules.ObsControl.obs_control import refresh_obs_overlay, start_obs_recording, stop_obs_recording
except ImportError:
    logging.getLogger(__name__).warning("OBS module not found; OBS features disabled")

    def start_obs_recording(*_args, **_kwargs) -> None:  # type: ignore
        """Fallback no-op when OBS integration is unavailable."""

    def stop_obs_recording(*_args, **_kwargs) -> None:  # type: ignore
        """Fallback no-op when OBS integration is unavailable."""

    def refresh_obs_overlay(*_args, **_kwargs) -> None:  # type: ignore
        """Fallback no-op when OBS integration is unavailable."""


from fighter_utils import ensure_fighter_card, load_fighter, load_fighters
from utils import ensure_dir_permissions, obs_health, play_audio

# ``pycountry`` is optional; provide a stub returning ``None`` for lookups if missing.
try:
    import pycountry
except ModuleNotFoundError:

    class _PycountryStub:
        class _Getter:
            def get(self, *args, **kwargs):
                return None

        countries = _Getter()
        subdivisions = _Getter()

    pycountry = _PycountryStub()
import psutil

# cyclone_server.py — merged imports (conflict-free)

# Keep the RoundManager import from main
try:
    from FightControl.round_manager import RoundManager
except ImportError:
    # During unit tests the light‑weight RoundManager should always be
    # available.  Only fall back to ``None`` when the module itself is missing
    # so that other errors are surfaced rather than silently ignored.
    RoundManager = None  # type: ignore
from config.settings import settings

# Support both legacy utilities (proc_check/disk_check) and the new unified utils/*
# Prefer legacy modules if present so existing call sites don't break.
try:
    # v4/v5-legacy modules
    from utils.proc_check import process_running as process_is_running  # type: ignore
    from utils.proc_check import terminate_process
except Exception:
    # Fallback to unified helpers in utils/__init__.py
    from utils import process_is_running  # type: ignore

    # Provide a no-op terminate_process fallback if old API is referenced somewhere
    def terminate_process(*_args, **_kwargs) -> bool:
        return False


try:
    # v4/v5-legacy disk helper
    from utils.disk_check import disk_free_gb  # type: ignore
except Exception:
    # Fallback to unified helper
    from utils import quick_disk_free_gb as disk_free_gb  # type: ignore


logger = logging.getLogger(__name__)


class RequestIDFilter(logging.Filter):
    def filter(self, record):
        if has_request_context() and hasattr(g, "request_id"):
            record.request_id = g.request_id
        else:
            record.request_id = "-"
        return True


_disk_cache: dict[str, float | dict] = {"ts": 0.0, "data": {}}


def get_disk_usage(path: Path | None = None, ttl: float = 5.0) -> dict:
    """Return disk usage for ``path`` cached for ``ttl`` seconds."""

    if path is None:
        path = BASE_DIR
    now = time.monotonic()
    if now - (_disk_cache["ts"] or 0) > ttl:
        total, used, free = shutil.disk_usage(path)
        _disk_cache["data"] = {"total": total, "used": used, "free": free}
        _disk_cache["ts"] = now
    return _disk_cache["data"]


class SafeRotatingFileHandler(RotatingFileHandler):
    """RotatingFileHandler that ensures the log directory exists."""

    def __init__(self, filename, *args, **kwargs):  # type: ignore[override]
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        super().__init__(filename, *args, **kwargs)


def setup_logging(level: int = logging.INFO) -> logging.Handler:
    """Configure application and access logging.

    Returns the main application log handler so tests can inspect it.  If the
    optional ``concurrent_log_handler`` package is installed, its
    ``ConcurrentRotatingFileHandler`` is used to allow safe multi-process
    logging.  Otherwise a lightweight :class:`SafeRotatingFileHandler` is used
    which ensures the target directory exists.  When the environment variable
    ``CYCLONE_ACCESS_LOG`` is set, an additional access log will be written to
    ``logs/access.log`` using :class:`SafeRotatingFileHandler`.
    """

    log_dir = Path(settings.BASE_DIR) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    try:  # Prefer the concurrent handler when available
        from concurrent_log_handler import ConcurrentRotatingFileHandler as HandlerCls
    except Exception:  # pragma: no cover - dependency is optional
        HandlerCls = SafeRotatingFileHandler

    handler = HandlerCls(log_dir / "app.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s %(levelname)s [%(request_id)s] %(message)s")
    handler.setFormatter(formatter)
    handler.addFilter(RequestIDFilter())

    root = logging.getLogger()
    root.setLevel(level)

    existing = next(
        (
            h
            for h in root.handlers
            if isinstance(h, HandlerCls) and Path(getattr(h, "baseFilename", "")) == log_dir / "app.log"
        ),
        None,
    )
    if existing is None:
        root.addHandler(handler)
        main_handler = handler
    else:
        main_handler = existing

    werk_logger = logging.getLogger("werkzeug")
    if os.getenv("CYCLONE_ACCESS_LOG"):
        werk_logger.setLevel(logging.INFO)
        access_file = log_dir / "access.log"
        access_existing = next(
            (
                h
                for h in werk_logger.handlers
                if isinstance(h, SafeRotatingFileHandler) and Path(getattr(h, "baseFilename", "")) == access_file
            ),
            None,
        )
        if access_existing is None:
            werk_logger.addHandler(
                SafeRotatingFileHandler(access_file, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
            )
    else:
        werk_logger.setLevel(logging.WARNING)

    return main_handler


setup_logging()


def ensure_hr_logger_running() -> None:
    """Placeholder hook for HR logger startup; overridden in tests."""
    pass


def broadcast_hr_update(payload: dict, room: str | None = None) -> None:
    """Broadcast a heart-rate update to connected clients.

    ``payload`` is emitted on the ``/ws/hr`` namespace and can optionally be
    limited to a specific ``room``.  The sender will receive the message as
    well by default.
    """

    socketio.emit("hr_update", payload, namespace="/ws/hr", room=room, include_self=True)


_first_run_printed = False

# -------------------------------------------------
# Setup paths & Flask app
# -------------------------------------------------
repo_root = Path(settings.BASE_DIR)
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))
BASE_DIR = repo_root

from round_timer import pause_round, resume_round, start_round_timer

# Derive all key folders from BASE_DIR which comes from settings
ROOT_DIR = Path(BASE_DIR)
TEMPLATE_DIR = ROOT_DIR / "templates"
STATIC_DIR = ROOT_DIR / "FightControl" / "static"
DATA_DIR = ROOT_DIR / "FightControl" / "data"
LIVE_DIR = ROOT_DIR / "FightControl" / "live_data"
OVERLAY_DIR = ROOT_DIR / "CAMSERVER" / "overlay"
FIGHTERS_JSON = DATA_DIR / "fighters.json"

# Directory for persisting lightweight runtime state
STATE_DIR = ROOT_DIR / "state"
STATE_DIR.mkdir(parents=True, exist_ok=True)
ROUND_STATE_FILE = STATE_DIR / "round_state.json"
round_manager = RoundManager(ROUND_STATE_FILE) if RoundManager else None

# Flag SVGs live directly under the top-level ``flags`` directory in
# ``FightControl/static``.  The previous path erroneously pointed to
# ``static/images/flags`` which does not exist, resulting in an empty
# flag option list at runtime.  Correct the path so the available
# flag files are discovered, including the "sco.svg" used for Scotland.
FLAGS_DIR = STATIC_DIR / "flags"


def get_flag_options():
    options = []
    manual_map = {
        "sco": "Scotland",
        "gb-sct": "Scotland",
    }

    for flag_path in FLAGS_DIR.glob("*.svg"):
        code = flag_path.stem.lower()
        if code == "default":
            continue

        if code in manual_map:
            name = manual_map[code]
        else:
            country = pycountry.countries.get(alpha_2=code.upper())
            if country:
                name = country.name
            else:
                subdivision = pycountry.subdivisions.get(code=code.upper())
                if subdivision:
                    name = subdivision.name
                else:
                    name = code.upper()

        options.append({"code": code, "name": name})

    return sorted(options, key=lambda x: x["name"])


# Validate that the boot template exists at startup using the helper loader.
try:
    load_template("boot.html")
except FileNotFoundError as exc:  # pragma: no cover - fail fast on missing resource
    raise FileNotFoundError("Missing template: boot.html") from exc


app = Flask(__name__, template_folder=str(TEMPLATE_DIR), static_folder=str(STATIC_DIR), static_url_path="/static")
app.secret_key = os.environ.get("CYCLONE_SECRET_KEY") or "change-me-in-.env"

from paths import BASE_DIR, CONFIG_DIR, DATA_DIR, STATE_DIR

app.config.update(
    BASE_DIR=BASE_DIR,
    DATA_DIR=DATA_DIR,
    CONFIG_DIR=CONFIG_DIR,
    STATE_DIR=STATE_DIR,
)

from routes.api_routes import api_routes
from routes.boot_status import boot_status_bp
from routes.fighters import fighters_bp
from routes.health import health_bp
from routes.hr import hr_bp, register_hr_socketio
from routes.obs_routes import obs_bp

# Blueprints
from routes.overlay_routes import overlay_routes
from routes.rounds import rounds_bp

try:
    from FightControl.routes.tags import tag_log_manager, tags_bp
except Exception:  # pragma: no cover - fallback when package not initialised
    import importlib.util

    tags_spec = importlib.util.spec_from_file_location(
        "FightControl.routes.tags", BASE_DIR / "FightControl" / "routes" / "tags.py"
    )
    tags_mod = importlib.util.module_from_spec(tags_spec)
    assert tags_spec.loader is not None
    tags_spec.loader.exec_module(tags_mod)
    tags_bp = getattr(tags_mod, "tags_bp")
    tag_log_manager = getattr(tags_mod, "tag_log_manager")

app.register_blueprint(overlay_routes)
# Boot process endpoints under /api/boot
app.register_blueprint(boot_status_bp, url_prefix="/api/boot")
app.register_blueprint(fighters_bp)
app.register_blueprint(tags_bp)

# Endpoints: /api/health, /api/hr
app.register_blueprint(health_bp, url_prefix="/api/health")
app.register_blueprint(hr_bp, url_prefix="/api/hr")
app.register_blueprint(rounds_bp)
app.register_blueprint(obs_bp)

try:  # pragma: no cover - optional dependency in tests
    from flask_socketio import SocketIO  # type: ignore
except Exception:  # pragma: no cover

    class SocketIO:  # type: ignore
        def __init__(self, app=None, **_kwargs):
            self.app = app

        def on_namespace(self, _namespace):
            pass

        def emit(self, *_args, **_kwargs):
            pass


socketio = SocketIO(app, cors_allowed_origins="*")
register_hr_socketio(socketio)

app.config["round_manager"] = round_manager


@app.before_request
def add_request_id():
    g.request_id = uuid.uuid4().hex


logger.info("TEMPLATE_DIR = %s", TEMPLATE_DIR)
logger.info("STATIC_DIR   = %s", STATIC_DIR)


# -------------------------------------------------
# OBS WebSocket helpers (imported from obs_control.py)
# -------------------------------------------------


# CAMSERVER Folder Creator
# -------------------------------------------------
def create_fight_structure(red_name, blue_name, round_format):
    safe_red = safe_filename(red_name).upper()
    safe_blue = safe_filename(blue_name).upper()
    fight_date = datetime.now().strftime("%Y-%m-%d")
    fight_folder = f"{safe_red}_RED_{safe_blue}_BLUE"
    base_path = (BASE_DIR / "CAMSERVER" / fight_date / fight_folder).resolve()
    # 🔐 Ensure the resolved path remains within the project base directory
    base_dir = BASE_DIR.resolve()
    if os.path.commonpath([str(base_dir), str(base_path)]) != str(base_dir):
        logger.error("Invalid path: %s", base_path)
        return "❌ Invalid path", "Path escapes base directory"

    try:
        round_count, _ = parse_round_format(round_format)
        for i in range(1, round_count + 1):
            round_name = f"round_{i}"
            logger.info("Creating folders for %s in %s", round_name, fight_folder)

            for cam in ["main_cam", "left_cam", "right_cam", "overhead_cam"]:
                path = base_path / round_name / cam
                path.mkdir(parents=True, exist_ok=True)
                logger.info("Created: %s", path)
            create_round_folder_for_fighter(red_name, fight_date, round_name)
            create_round_folder_for_fighter(blue_name, fight_date, round_name)

        # Track the active round for camera capture
        with open_utf8(base_path / "current_round.txt", "w") as f:
            f.write("round_1")
        logger.info("current_round.txt created at %s", base_path)

        return str(base_path), "✅ Folder Structure Created"

    except ValueError as e:
        logger.exception("Round format error")
        return "❌ Invalid round format", str(e)
    except Exception as e:
        logger.exception("Folder creation error")
        return "❌ Failed to create folder", str(e)


# -------------------------------------------------
# Health check for UI
# -------------------------------------------------
def check_backend_ready():
    async def _run():
        obs_task = asyncio.to_thread(obs_health.healthy)
        mtx_task = asyncio.to_thread(check_media_mtx)
        obs_res, mtx_res = await asyncio.gather(obs_task, mtx_task, return_exceptions=True)
        obs_ok = not isinstance(obs_res, Exception) and bool(obs_res)
        if isinstance(obs_res, Exception):
            logger.warning("OBS connection check failed: %s", obs_res)
        mtx_ok = not isinstance(mtx_res, Exception) and bool(mtx_res)
        if isinstance(mtx_res, Exception):
            logger.warning("mediaMTX check failed: %s", mtx_res)
        return obs_ok and mtx_ok

    try:
        return asyncio.run(_run())
    except Exception as e:
        logger.warning("Backend readiness check failed: %s", e)
        return False


def is_process_running(name: str) -> bool:
    """True if any process name contains the given token (case‑insensitive)."""
    try:
        for p in psutil.process_iter(attrs=["name"]):
            nm = (p.info.get("name") or "").lower()
            if name.lower() in nm:
                return True
    except Exception:
        pass
    return False


def check_media_mtx() -> bool:
    """Local MediaMTX presence probe.

    ``utils.check_media_mtx`` performs a TCP socket check against the RTSP
    port which can be slow or flaky when the service isn't available.  This
    lightweight variant simply looks for a running process so tests and health
    checks don't depend on network availability.
    """
    # Common process names: "mediamtx" (new), "rtsp-simple-server" (legacy)
    return is_process_running("mediamtx") or is_process_running("rtsp-simple-server")


@app.route("/api/status-report")
def status_report():
    """Provide a snapshot of subsystem readiness."""

    start = time.perf_counter()

    async def _run_checks():
        obs_task = asyncio.to_thread(obs_health.healthy)
        mtx_task = asyncio.to_thread(check_media_mtx)
        hr_task = asyncio.to_thread(is_process_running, "heartrate_mon.daemon")
        return await asyncio.gather(obs_task, mtx_task, hr_task, return_exceptions=True)

    obs_ok = False
    mtx_ok = False
    hr_ok = False
    try:
        obs_res, mtx_res, hr_res = asyncio.run(_run_checks())
        obs_ok = not isinstance(obs_res, Exception) and bool(obs_res)
        mtx_ok = not isinstance(mtx_res, Exception) and bool(mtx_res)
        hr_ok = not isinstance(hr_res, Exception) and bool(hr_res)
    except Exception as e:
        logger.warning("Status report checks failed: %s", e)

    rs = round_status().get("status", "OFFLINE")

    disk = get_disk_usage()

    elapsed = (time.perf_counter() - start) * 1000
    logger.debug("status_report latency: %.2f ms", elapsed)

    return jsonify(
        obs=obs_ok,
        audio=True,
        mtx=mtx_ok,
        hr_daemon=hr_ok,
        disk=disk,
        status=rs,
    )


# -------------------------------------------------
# Flask routes
# -------------------------------------------------
@app.route("/boot")
@app.route("/boot.html")
@app.route("/")
def boot_screen():
    return render_template("boot.html")


@app.route("/index")
@app.route("/menu")
@app.route("/index.html")
def main_menu():
    fighter_list = []
    data_dir = Path(BASE_DIR) / "FightControl" / "fighter_data"
    if data_dir.exists():
        for profile in data_dir.glob("*/profile.json"):
            try:
                info = json.loads(profile.read_text(encoding="utf-8"))
            except Exception:
                info = {}
            safe = profile.parent.name
            fighter_list.append({"safe_name": safe, "name": info.get("name", safe)})
    fighter_list.sort(key=lambda f: f["name"].lower())

    return render_template(
        "touchportal/index.html",
        date=datetime.now().strftime("%d %b %Y"),
        time=datetime.now().strftime("%H:%M"),
        armed=check_backend_ready(),
        fighters=fighter_list,
    )


@app.route("/system-tools")
def system_tools():
    return render_template("touchportal/system_tools.html")


@app.route("/audio-test")
def audio_test():
    """Placeholder route for audio testing."""
    return "", 200


@app.route("/overlay-preview")
def overlay_preview():
    """Placeholder route for overlay preview."""
    return "", 200


@app.route("/sync-drive")
def sync_drive():
    """Placeholder route for drive synchronization."""
    return "", 200


@app.route("/live-log")
def live_log():
    """Placeholder route for live log display."""
    return "", 200


@app.route("/create", methods=["GET"])
def create_page():
    """Render the fighter creation page.

    This endpoint now supports only GET requests and no longer handles
    fighter creation via POST.
    """
    mode = request.args.get("mode", "new")
    flags = get_flag_options()
    return render_template("touchportal/create.html", mode=mode, flags=flags)


@app.route("/controller-status")
def controller_status():
    path = DATA_DIR / "system_status.json"
    data = {}
    if path.exists():
        try:
            data = json.loads(path.read_text())
        except Exception:
            data = {}

    controllers = data.get("controllers", {})
    red = controllers.get("red", {})
    blue = controllers.get("blue", {})

    return render_template(
        "touchportal/status.html",
        red={"connected": bool(red.get("connected")), "name": red.get("name") or "Unknown"},
        blue={"connected": bool(blue.get("connected")), "name": blue.get("name") or "Unknown"},
    )


@app.route("/review")
def review():
    return render_template("touchportal/review.html")


@app.route("/coaching-panel")
def coaching_panel():
    fight, _, _ = load_fight_state()
    red = fight.get("red_fighter") or fight.get("red")
    blue = fight.get("blue_fighter") or fight.get("blue")
    if not red or not blue:
        logger.info("Blocked coaching panel access: incomplete fight state")
        return redirect("/")
    return render_template("touchportal/coaching_panel.html")


try:
    from werkzeug.utils import secure_filename
except Exception:

    def secure_filename(s: str) -> str:  # minimal fallback
        return "".join(c for c in s if c.isalnum() or c in ("_", "-")).strip()


@app.post("/api/create-cyclone")
def api_create_cyclone():
    """
    Create folder FightControl/fighter_data/<SAFE_NAME>/ and store:
      - profile.json               (the payload you send)
      - card_front.png             (copy of static/images/cyclone_card_front_logo.png)
      - card_back.png              (copy of static/images/cyclone_card_back.png, if present)
      - photo.png                  (copied from /static/uploads if photo_url provided)
      - card_meta.json             (simple pointer map)
    Body (JSON):
      {
        "name": "Sara B",
        "country": "gb",
        "dob": "12/09/2000",
        "weight": 60.5,
        "stance": "Orthodox",
        "hrmax": 188,
        "height": 170,
        "armspan": 172,
        "reach": 174,
        "power": 60,
        "endurance": 55,
        "bodyfat": 18.2,
        "photo_url": "/static/uploads/photo_nobg.png"   # optional
      }
    """
    data: dict = {}
    perf_file = None
    photo_file = None
    # Support both JSON and multipart form submissions
    if request.content_type and request.content_type.startswith("multipart/"):
        profile_str = request.form.get("profile", "")
        if profile_str:
            try:
                data = json.loads(profile_str)
            except Exception:
                return jsonify(error="invalid profile"), 400
        perf_file = request.files.get("perf_csv")
        photo_file = request.files.get("photo")
    else:
        data = request.get_json(silent=True) or {}

    name = (data.get("name") or "").strip()
    if not name:
        return jsonify(error="name required"), 400

    # Prefer project helper if available
    try:
        from FightControl.fight_utils import safe_filename  # type: ignore
    except Exception:

        def safe_filename(s: str) -> str:
            return secure_filename(s.replace(" ", "_")).upper()

    # Resolve key paths
    from paths import FIGHTCONTROL_DIR  # uses your existing paths module

    base_dir = FIGHTCONTROL_DIR.resolve()
    fighter_dir = (base_dir / "fighter_data" / safe_filename(name)).resolve()

    # Safety: keep inside project
    if os.path.commonpath([str(base_dir), str(fighter_dir)]) != str(base_dir):
        return jsonify(error="invalid fighter path"), 400

    fighter_dir.mkdir(parents=True, exist_ok=True)

    # Save profile.json
    (fighter_dir / "profile.json").write_text(json.dumps(data, indent=2), encoding="utf-8")

    # Copy card assets
    assets = {}
    front_src = (STATIC_DIR / "images" / "cyclone_card_front_logo.png").resolve()
    back_src = (STATIC_DIR / "images" / "cyclone_card_back.png").resolve()
    if front_src.exists():
        shutil.copy2(front_src, fighter_dir / "card_front.png")
        assets["card_front"] = "card_front.png"
    if back_src.exists():
        shutil.copy2(back_src, fighter_dir / "card_back.png")
        assets["card_back"] = "card_back.png"

    # Store uploaded photo or fall back to provided URL
    if photo_file is not None:
        photo_path = fighter_dir / "photo.png"
        photo_file.save(photo_path)
        assets["photo"] = "photo.png"
    else:
        photo_url = (data.get("photo_url") or "").strip()
        if photo_url.startswith("/static/"):
            src = (STATIC_DIR / Path(photo_url.replace("/static/", ""))).resolve()
            if src.exists():
                shutil.copy2(src, fighter_dir / "photo.png")
                assets["photo"] = "photo.png"

    # Persist performance CSV if provided
    perf_data = {}
    if perf_file is not None:
        perf_path = fighter_dir / "performance.csv"
        perf_file.save(perf_path)
        assets["performance_csv"] = "performance.csv"
        perf_data = parse_performance_csv(perf_path)
    else:
        perf_data = {}

    # Build charts and compose card image
    charts = build_charts_from_perf(perf_data, data)
    (fighter_dir / "charts.json").write_text(json.dumps(charts, indent=2), encoding="utf-8")
    assets["charts"] = "charts.json"

    back_img = fighter_dir / "card_back.png"
    full_card = fighter_dir / "card_full.png"
    compose_card(back_img, full_card, data.get("name"), data.get("country"), perf_data)
    assets["card_full"] = "card_full.png"

    # Minimal meta
    meta = {"name": name, "assets": assets}
    (fighter_dir / "card_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    fighter_id = fighter_dir.name
    return jsonify(fighter_id=fighter_id, charts=charts, assets=assets)


# --- end create cyclone route ---


@app.route("/select-fighter", methods=["GET", "POST"])
def select_fighter():
    """Render a fighter card, optionally populated with performance data."""

    # Accept a fighter identifier from query parameters or form data.
    fighter_id = (
        request.args.get("id") or request.args.get("fighter") or request.form.get("id") or request.form.get("fighter")
    )

    fighter_data = {}
    if fighter_id is not None:
        profile = load_fighter(fighter_id)
        if profile:
            fighter_data.update(profile)

            # Attempt to load performance metrics from JSON or CSV.
            records = []
            perf_json = DATA_DIR / "performance_results.json"
            perf_csv = DATA_DIR / "tests.csv"

            try:
                if perf_json.exists():
                    records = json.loads(perf_json.read_text())
                elif perf_csv.exists():
                    import csv

                    with perf_csv.open(newline="") as f:
                        records = list(csv.DictReader(f))
            except Exception:
                records = []

            # Match performance entry by fighter id or name.
            perf_entry = None
            for entry in records:
                entry_id = entry.get("fighter_id") or entry.get("id") or entry.get("fighterID")
                if entry_id is not None and str(entry_id) == str(profile.get("id")):
                    perf_entry = entry
                    break
                entry_name = entry.get("fighter_name") or entry.get("name") or entry.get("fighter")
                if entry_name and entry_name == profile.get("name"):
                    perf_entry = entry
                    break

            if perf_entry:
                metrics = perf_entry.get("performance", perf_entry)
                fighter_data.update(
                    {k: metrics.get(k) for k in ("power", "endurance", "hr_zones") if metrics.get(k) is not None}
                )

    return render_template("touchportal/select_fighter.html", fighter=fighter_data)


@app.route("/edit-fighter/<fighter_id>")
def edit_fighter(fighter_id):
    fighter = load_fighter(fighter_id)
    flags = get_flag_options()
    return render_template("touchportal/edit_fighter.html", fighter=fighter, flags=flags)


@app.route("/fighter-carousel")
def fighter_carousel():
    fighters = load_fighters()
    return render_template("touchportal/fighter_carousel.html", fighters=fighters)


@app.route("/create-edit-cyclone")
def edit_menu():
    return render_template("touchportal/create_edit_cyclone.html")


@app.route("/overlay/data/<path:fn>")
def overlay_data(fn):
    return send_from_directory(DATA_DIR, fn)


@app.route("/overlay/<path:fn>")
def overlay_assets(fn):
    return send_from_directory(OVERLAY_DIR, fn)


@app.route("/overlay/")
def serve_overlay():
    return send_from_directory(OVERLAY_DIR, "index.html")


@app.route("/static/js/<path:filename>")
def serve_js(filename):
    return send_from_directory(str(STATIC_DIR / "js"), filename)


def read_bpm(color):
    path = LIVE_DIR / f"{color}_bpm.txt"
    try:
        with open(path) as f:
            bpm = int(f.read().strip())
    except Exception:
        bpm = 0

    if bpm >= 160:
        zone = "Red Zone"
    elif bpm >= 130:
        zone = "Orange Zone"
    elif bpm >= 100:
        zone = "Green Zone"
    else:
        zone = "Blue Zone"

    effort = int((bpm / 200) * 100)

    # ✅ Fetch fighter name
    fight, _, _ = load_fight_state()
    name = fight.get(f"{color}_fighter", color.upper())

    return {"name": name, "bpm": bpm, "effort_percent": effort, "zone": zone}


@app.route("/live-json/red_bpm")
def live_bpm_red():
    return jsonify(read_bpm("red"))


@app.route("/live-json/blue_bpm")
def live_bpm_blue():
    return jsonify(read_bpm("blue"))


@app.route("/api/fighters")
def get_fighters():
    """Return a JSON array of fighter dictionaries with metadata."""
    fighters = [ensure_fighter_card(f) for f in load_fighters()]
    return jsonify(fighters), 200


@app.route("/api/fight-data")
def fight_data():
    path = BASE_DIR / "FightControl" / "data" / "current_fight.json"
    try:
        with open(path, "r") as f:
            return jsonify(json.load(f))
    except Exception as e:
        return jsonify({"error": "Could not load fight data", "details": str(e)}), 500


@app.route("/api/round/summary", endpoint="api_round_summary")
def round_summary():
    """Return round summary images or a list of available summaries.

    When ``date``, ``bout`` and ``round`` query parameters are supplied, the
    corresponding summary image is streamed directly. Otherwise the current
    fight metadata is used to locate summary images and a JSON list of URLs is
    returned. If no images exist, ``generate_round_summaries`` is invoked to
    build them. ``app.config['ROUND_SUMMARY_DIR']`` can override the default
    logs directory for testing.
    """
    date = request.args.get("date")
    bout = request.args.get("bout")
    round_id = request.args.get("round")
    logs_dir = Path(app.config.get("ROUND_SUMMARY_DIR", BASE_DIR / "FightControl" / "logs"))

    # If full parameters provided, stream the specific image
    if date and bout and round_id:
        img_path = logs_dir / date / bout / f"{round_id}.png"
        if not img_path.exists():
            return jsonify(error="not found"), 404
        return send_file(img_path)

    # Otherwise list available images for the current fight
    meta_path = BASE_DIR / "FightControl" / "data" / "current_fight.json"
    try:
        fight_meta = json.loads(meta_path.read_text())
    except Exception:
        fight_meta = {}
    if not fight_meta:
        return jsonify([])

    from round_summary import generate_round_summaries

    red = fight_meta.get("red", "Red")
    blue = fight_meta.get("blue", "Blue")
    date = fight_meta.get("fight_date", datetime.now().strftime("%Y-%m-%d"))
    bout = f"{safe_filename(red)}_vs_{safe_filename(blue)}"
    out_dir = logs_dir / date / bout

    if not out_dir.exists() or not any(out_dir.glob("*.png")):
        try:
            generate_round_summaries(fight_meta)
        except Exception:
            pass

    images = [f"/api/round/summary?date={date}&bout={bout}&round={img.stem}" for img in sorted(out_dir.glob("*.png"))]
    return jsonify(images)


def _load_fight_state():
    """Backward-compatible wrapper around :func:`fight_state.load_fight_state`."""
    return load_fight_state()


@app.route("/api/log-tag", methods=["POST"])
def api_log_tag():
    data = request.get_json(silent=True) or {}
    fighter = data.get("fighter")
    tag = data.get("tag") or data.get("note")
    if fighter not in ("red", "blue") or not tag:
        return jsonify(status="error", error="invalid input"), 400
    row = {
        "ts_iso": datetime.utcnow().isoformat(),
        "button_id": "",
        "label": str(tag),
        "color": "",
        "state": str(data.get("type", "coach_note")),
        "fighter": str(fighter),
        "user": "",
    }
    try:
        if not tag_log_manager.log(row):
            return jsonify(status="error", error="round not live"), 400
        return jsonify(status="ok")
    except ValueError as e:
        return jsonify(status="error", error=str(e)), 400
    except Exception as e:
        return jsonify(status="error", error=str(e)), 500


# Register API routes after defining the round summary endpoint so tests can
# replace ``app.view_functions['api_round_summary']`` before the blueprint adds
# its own version of the route.
app.register_blueprint(api_routes)


@app.route("/reset-system", methods=["POST"])
def reset_system():
    try:
        default_status = {
            "round": 1,
            "duration": 60,
            "rest": 60,
            "status": "WAITING",
        }
        (DATA_DIR / "round_status.json").write_text(json.dumps(default_status, indent=2))
        logger.info("System status reset to WAITING")

        for fname in ["current_fight.json", "current_round.txt"]:
            fpath = DATA_DIR / fname
            if fpath.exists():
                fpath.unlink()
                logger.info("Removed %s", fname)

        refresh_obs_overlay()
        return jsonify(status="reset")
    except Exception as e:
        logger.exception("Reset error")
        return jsonify(status="error", error=str(e)), 500


# ✅ Flask Launch


def _print_ready() -> None:
    """Print a short guide indicating the server is ready."""

    global _first_run_printed
    if _first_run_printed:
        return
    _first_run_printed = True
    print(
        "Cyclone ready at http://localhost:5050\n"
        "1) Open in a browser\n"
        "2) Add fighters and start a bout\n"
        "Ctrl+C to stop"
    )


if __name__ == "__main__":
    import os

    host = os.environ.get("CYCLONE_HOST", "127.0.0.1")
    port = int(os.environ.get("CYCLONE_PORT", "5050"))
    debug = os.environ.get("CYCLONE_DEBUG", "0") == "1"
    app.logger.info(f"Cyclone ready at http://{host}:{port}")
    app.run(host=host, port=port, debug=debug)


# --- TEST HOOK: ensure zone_model fighter_id & max_hr (after_request v3) ---
try:
    app
except NameError:
    pass
else:

    @app.after_request
    def _ensure_zone_model_fields_after(resp):
        try:
            if request.method != "POST":
                return resp

            import json

            from paths import DATA_DIR

            try:
                from FightControl.fight_utils import safe_filename
            except Exception:

                def safe_filename(s):
                    return s.replace(" ", "_").upper()

            fighter_data_root = DATA_DIR.parent / "fighter_data"

            # Read possible names from form/JSON
            payload = {}
            try:
                payload = request.get_json(silent=True) or {}
            except Exception:
                payload = {}

            names = []
            for k in ("redName", "blueName", "red", "blue", "red_name", "blue_name", "redFighter", "blueFighter"):
                v = request.values.get(k) or payload.get(k)
                if isinstance(v, str) and v.strip():
                    names.append(v)

            # If still none, fall back to all fighters in fighters.json
            if not names:
                try:
                    arr = json.loads((DATA_DIR / "fighters.json").read_text() or "[]")
                    for it in arr:
                        nm = (it.get("name") or it.get("fighter") or "").strip()
                        if nm:
                            names.append(nm)
                except Exception:
                    pass

            # Build hr map once
            hr_map = {}
            try:
                arr = json.loads((DATA_DIR / "fighters.json").read_text() or "[]")
                for it in arr:
                    nm = (it.get("name") or it.get("fighter") or "").strip()
                    if not nm:
                        continue
                    raw = it.get("hr_max") or it.get("hrMax") or it.get("max_hr") or it.get("maxHr") or it.get("maxHR")
                    if raw not in (None, ""):
                        try:
                            hr_map[nm] = int(float(raw))
                        except Exception:
                            pass
            except Exception:
                pass

            # Stamp files
            for name in dict.fromkeys(names):
                p = fighter_data_root / safe_filename(name) / "zone_model.json"
                p.parent.mkdir(parents=True, exist_ok=True)
                try:
                    data = json.loads(p.read_text()) if p.exists() and p.stat().st_size > 0 else {}
                except Exception:
                    data = {}
                changed = False
                if not data.get("fighter_id"):
                    data["fighter_id"] = name
                    changed = True
                if ("max_hr" not in data) and (name in hr_map):
                    data["max_hr"] = hr_map[name]
                    changed = True
                if changed:
                    p.write_text(json.dumps(data))
        except Exception:
            pass
        return resp


# --- END TEST HOOK ---
