import os, json, subprocess
from pathlib import Path
from flask import Flask, jsonify, redirect, render_template, send_from_directory

# Resolve BASE
p = Path(__file__).resolve()
BASE = Path(os.environ.get("CYCLONE_BASE_DIR") or p)
BASE = BASE.parents[1] if BASE.is_file() and len(BASE.parents) > 1 else BASE

TEMPLATES = BASE / "templates"
STATIC    = BASE / "FightControl" / "static"
LIVE      = BASE / "FightControl" / "live_data"
STATUS    = LIVE / "boot_status.json"

app = Flask(__name__,
            template_folder=str(TEMPLATES),
            static_folder=str(STATIC),
            static_url_path="/static")

@app.route("/")
def root():
    try:
        data = json.loads(STATUS.read_text(encoding="utf-8"))
        if not data.get("done"):
            return redirect("/boot")
    except Exception:
        pass
    return redirect("/index")

@app.route("/boot")
def boot():
    return render_template("touchportal/boot.html")

@app.route("/index")
def index():
    return render_template("index.html")

@app.route("/status")
def status():
    try:
        return jsonify(json.loads(STATUS.read_text(encoding="utf-8")))
    except Exception:
        return jsonify({"step":0,"total":1,"message":"Starting…","done":False})

# ---- compatibility for old boot.js ----
@app.route("/api/status-report")
def api_status_report():
    return status()

@app.route("/api/start", methods=["POST","GET"])
@app.route("/api/start-boot", methods=["POST","GET"])
@app.route("/api/start-system", methods=["POST","GET"])
def api_start():
    ps1 = BASE / "scripts" / "boot_v2.ps1"
    if ps1.exists():
        subprocess.Popen(["powershell","-ExecutionPolicy","Bypass","-File", str(ps1)], cwd=str(BASE))
        return ("", 204)
    return ("boot_v2.ps1 not found", 404)

# serve /overlay/* referenced by old boot
@app.route("/overlay/<path:filename>")
def overlay_file(filename: str):
    return send_from_directory(str(STATIC / "overlay"), filename)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8765, debug=False)
