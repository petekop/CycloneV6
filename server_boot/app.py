import os, json, subprocess
from pathlib import Path
from flask import Flask, jsonify, redirect, render_template, send_from_directory

# Resolve base and key paths
BASE     = Path(os.environ.get("CYCLONE_BASE_DIR", r"E:\Cyclone"))
TEMPLATES= BASE / "templates"
STATIC   = BASE / "FightControl" / "static"
LIVE     = BASE / "FightControl" / "live_data"
STATUS   = LIVE / "boot_status.json"

# TouchPortal templates
BOOT_TPL  = "touchportal/boot.html"
INDEX_TPL = "touchportal/index.html"

app = Flask(
    __name__,
    template_folder=str(TEMPLATES),
    static_folder=str(STATIC),
    static_url_path="/static",
)

@app.route("/")
def root():
    # If not finished booting, show boot; else go to main index
    try:
        data = json.loads(STATUS.read_text(encoding="utf-8"))
        if not data.get("done"):
            return redirect("/boot")
    except Exception:
        # No status file yet -> show boot
        return redirect("/boot")
    return redirect("/index")

@app.route("/boot")
def boot():
    return render_template(BOOT_TPL)

@app.route("/index")
def index():
    return render_template(INDEX_TPL)

@app.route("/status")
def status():
    try:
        return jsonify(json.loads(STATUS.read_text(encoding="utf-8")))
    except Exception:
        return jsonify({"step": 0, "total": 1, "message": "Starting…", "done": False})

# Old boot page calls these:
@app.route("/api/status-report")
def status_report():
    # Simple mirror of /status so your old boot UI stays happy
    try:
        data = json.loads(STATUS.read_text(encoding="utf-8"))
    except Exception:
        data = {"step": 0, "total": 1, "message": "Starting…", "done": False}
    return jsonify(data)

@app.route("/overlay/<path:filename>")
def overlay_file(filename: str):
    # Serve legacy /overlay/script.js etc. from static/overlay
    return send_from_directory(str(STATIC / "overlay"), filename)

@app.route("/api/start-system", methods=["POST","GET"])
def start_system():
    # Fire-and-forget PowerShell boot
    ps1 = BASE / "scripts" / "boot_v2.ps1"
    if ps1.exists():
        subprocess.Popen(["powershell","-ExecutionPolicy","Bypass","-File", str(ps1)], cwd=str(BASE))
        return ("", 204)
    return ("boot_v2.ps1 not found", 404)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8765, debug=False)
