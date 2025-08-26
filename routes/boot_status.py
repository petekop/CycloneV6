from __future__ import annotations
import os, json, socket, subprocess
from pathlib import Path
from typing import Dict, Any
from flask import Blueprint, jsonify, current_app

BASE_DIR = Path(os.environ.get("CYCLONE_BASE_DIR") or Path(__file__).resolve().parents[1]).resolve()

def _load_paths() -> Dict[str, Dict[str, str]]:
    cfg = BASE_DIR / "config" / "boot_paths.yml"
    if not cfg.exists():
        return {}
    txt = cfg.read_text(encoding="utf-8")
    # Minimal YAML: sections + key: value
    out: Dict[str, Dict[str, str]] = {}
    section: str | None = None
    for line in txt.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line.startswith(" "):
            section = line.strip().rstrip(":")
            out[section] = {}
        else:
            if ":" in line and section:
                k, v = line.split(":", 1)
                out[section][k.strip()] = v.strip().strip('"')
    return out

PATHS = _load_paths()

def _wrap_command(script_path: str):
    sp = str(script_path).strip().strip('"').strip("'")
    ext = os.path.splitext(sp)[1].lower()
    if ext in (".bat", ".cmd"):
        return ["cmd.exe", "/c", sp]
    if ext == ".ps1":
        return ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", sp]
    if ext == ".lnk":
        return ["powershell", "-NoProfile", "-Command", f"Start-Process -FilePath '{sp}'"]
    return [sp]

def _is_port_open(port: int, host: str="127.0.0.1", timeout: float=0.25) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False

def _tasklist_contains(name: str) -> bool:
    try:
        out = subprocess.check_output(["tasklist"], creationflags=subprocess.CREATE_NO_WINDOW).decode(errors="ignore").lower()
        return name.lower() in out
    except Exception:
        return False

PROCS: Dict[str, subprocess.Popen] = {}
STATE: Dict[str, str] = {"mediamtx": "WAIT", "obs": "WAIT", "hr_daemon": "WAIT"}

def _service_ready(name: str) -> bool:
    if name == "obs":
        port = int(os.environ.get("OBS_WS_PORT", "4455"))
        return _is_port_open(port) or _tasklist_contains("obs64.exe")
    if name == "mediamtx":
        return _is_port_open(8554) or _tasklist_contains("mediamtx.exe")
    if name == "hr_daemon":
        live = BASE_DIR / "FightControl" / "live_data"
        rs = (live / "red_status.txt")
        bs = (live / "blue_status.txt")
        red = rs.read_text(errors="ignore").strip() if rs.exists() else ""
        blue = bs.read_text(errors="ignore").strip() if bs.exists() else ""
        return bool(red or blue)
    return False

def _spawn(name: str) -> None:
    spec = PATHS.get(name)
    if not spec:
        current_app.logger.warning(f"Service {name} not in boot_paths.yml"); return
    script = spec.get("script")
    if not script:
        current_app.logger.warning(f"Service {name} has no script"); return
    full = (BASE_DIR / script).resolve()
    envv = os.environ.copy()
    envv["CYCLONE_BASE_DIR"] = str(BASE_DIR)
    cmd = _wrap_command(str(full))
    try:
        PROCS[name] = subprocess.Popen(cmd, cwd=str(BASE_DIR), env=envv,
                                       creationflags=subprocess.CREATE_NEW_CONSOLE)
        current_app.logger.info(f"Spawned service {name} -> {full}")
    except Exception as e:
        current_app.logger.exception(f"Error spawning {name}: {e}")
        STATE[name] = "ERROR"

def _kick(name: str) -> None:
    if STATE.get(name) == "READY":
        return
    if _service_ready(name):
        STATE[name] = "READY"
        return
    _spawn(name)

def _progress() -> int:
    total = len(STATE); ready = sum(1 for v in STATE.values() if v == "READY")
    return int((ready / max(total,1)) * 100)

bp = Blueprint("boot_status", __name__)

@bp.route("/api/boot/start", methods=["GET"])
def boot_start():
    try:
        for n in list(STATE.keys()):
            _kick(n)
        return boot_status()
    except Exception as e:
        current_app.logger.exception("boot_start failed")
        return jsonify(message=str(e), progress=_progress(), ready=False, services=STATE), 500

@bp.route("/api/boot/status", methods=["GET"])
def boot_status():
    try:
        for n in list(STATE.keys()):
            if _service_ready(n):
                STATE[n] = "READY"
        return jsonify(message="", progress=_progress(), ready=all(v=="READY" for v in STATE.values()), services=STATE)
    except Exception as e:
        current_app.logger.exception("boot_status failed")
        return jsonify(message=str(e), progress=_progress(), ready=False, services=STATE), 500

def register(app):
    try: app.register_blueprint(bp)
    except Exception: pass
def init_app(app): register(app)
