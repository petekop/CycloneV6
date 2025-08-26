# Cyclone Server (Complete Modular Version)

Split cyclone modules include:

- `setup_paths.py` — All path setup, Flask app
- `fight_state.py` — Fight state utilities such as `get_session_dir`
- `utils_checks.py` — System & OBS readiness checks
- `obs_control.py` — OBS Start/Stop/Pause/Resume/Refresh (WebSocket v5+)
- `utils_fight.py` — Fighter data, round timer, audio
- `utils_bpm.py` — Heart rate monitor live reader
- `routes/` — Flask route blueprints (registered via `routes/api_routes.py`)
- `cyclone_server.py` — Serves as the entry launcher and primary Flask route container (use this to run)

---

## Installation

On Windows the project can be bootstrapped with the installer script:

```powershell
./scripts/install.ps1 -BaseDir "C:\Cyclone" -GoogleApiKey "<key>"
```


The script sets `CYCLONE_BASE_DIR` (and optionally `GOOGLE_API_KEY`), creates the virtual environment, installs requirements, copies `.env.example` to `.env` and fetches external binaries. For manual setup see `docs/environment_setup.md`.


## Starting Cyclone

Paths to external binaries are defined in `config/boot_paths.yml`.
Adjust the file if services like OBS or MediaMTX reside outside the default layout.

PowerShell may block scripts on a fresh Windows install. Allow local scripts once:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```


After installation start the server once:

```powershell
./scripts/launch_cyclone.ps1
```

The script starts the Flask server and opens the boot page, which launches required services and shows their status. If `CYCLONE_BASE_DIR` is not already defined, set it before launching:

```powershell
$env:CYCLONE_BASE_DIR="C:\\Cyclone"
./scripts/launch_cyclone.ps1
```

Alternatively run `python cyclone_server.py` on any platform. Launching the macOS app works the same way. If OBS does not start from the boot page, open it manually.


## macOS bundle

To create a standalone macOS application run:

```bash
./scripts/build_macos.sh
```

This uses PyInstaller to produce `dist/Cyclone.app`. Launching the app starts
the server and opens `http://localhost:5050/boot` in the default browser. The boot page automatically starts services and checks their status. OBS Studio must be installed separately on macOS and may need to be launched manually for recording features to work.


Windows CYCLONE_BASE_DIR Example
ini
Copy
Edit
CYCLONE_BASE_DIR=E:/Cyclone
Avoid trailing slashes. Many scripts depend on this path being correct.

Development Notes
Logs are excluded from version control via .gitignore. The application
creates the ``logs/`` directory automatically when needed, so no manual
setup is required.

Log directories incorporate sanitized fighter names so paths remain
filesystem friendly regardless of the original fighter names.

Never commit generated data in ``logs/`` or ``fighter_data/``

Run ``python scripts/rebuild_fighters_index.py`` after adding or modifying
fighter profiles. The script scans ``FightControl/fighter_data/*/profile.json``
and rebuilds ``FightControl/data/fighters.json``.

When adding standalone Python scripts, ensure the repository root is importable:

```python
from pathlib import Path
import sys

repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))
```

Running Tests

Install both the standard and development requirements to run the full test suite:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
pre-commit install
python scripts/migrate_env_to_v5.py
npm install --prefix tests
pytest
```

To debug Node test client separately:

```bash
npm test --prefix tests
WS_URL=ws://localhost:4455 npm test --prefix tests
```

Running the Server

```bash
python cyclone_server.py
```

The boot page automatically starts required services and displays their status. The server only auto-starts when `CYCLONE_AUTOSTART=1` (default `0` to keep imports and tests quiet). Example on PowerShell:

```powershell
$env:CYCLONE_AUTOSTART="1"; python cyclone_server.py
```

For convenience, development scripts set this automatically:

```powershell
./scripts/run_dev.ps1
```

```bash
./scripts/run_dev.sh
```

Tests set `CYCLONE_AUTOSTART=0` automatically.

Web UI: http://localhost:5050/boot

If OBS is not running after boot, launch it manually.

### Debugging and Logs

Install [`concurrent-log-handler`](https://pypi.org/project/concurrent-log-handler/) for
process-safe log rotation:

```bash
pip install concurrent-log-handler
```

Set `CYCLONE_DEBUG=1` to enable Flask debug mode and the auto-reloader. The
server defaults to `CYCLONE_DEBUG=0` and `use_reloader=False` to avoid
double-starting processes.

When the optional access log handler is available, enable HTTP request logs
with `CYCLONE_ACCESS_LOG=1`. Access logs are written to `logs/access.log`.

## OBS WebSocket Configuration

Cyclone uses [`python-dotenv`](https://pypi.org/project/python-dotenv/) to
load settings from a `.env` file. Configure the OBS WebSocket connection with
these variables:

- `OBS_WS_URL` – full WebSocket URL. If set, it overrides host/port.
- `OBS_WS_HOST` / `OBS_WS_PORT` – host and port for the WebSocket server.
- `OBS_WS_PASSWORD` – OBS WebSocket password if authentication is enabled.
- `OBS_CONNECT_TIMEOUT` – seconds to wait when connecting (default: 5).

Examples:

```bash
# Full URL style
OBS_WS_URL=ws://127.0.0.1:4455
OBS_WS_PASSWORD=changeme
# Seconds to wait when connecting (default: 5)
OBS_CONNECT_TIMEOUT=5
```

```bash
# Host/port style
OBS_WS_HOST=127.0.0.1
OBS_WS_PORT=4455
OBS_WS_PASSWORD=changeme
# Seconds to wait when connecting (default: 5)
OBS_CONNECT_TIMEOUT=5
```

`OBS_CONNECT_TIMEOUT` controls how long Cyclone waits for the initial OBS
connection. Increase this value on slower machines if connections frequently
time out.

Heart-rate monitor MAC addresses are configured in `FightControl/heartrate_mon/config.json`:

```json
{"red": "<MAC>", "blue": "<MAC>"}
```

This file is the single source of truth for strap addresses. `FightControl/heartrate_mon/daemon.py` falls back to the `CYCLONE_RED_H10_MAC` and `CYCLONE_BLUE_H10_MAC` environment variables if the file is missing or a value is empty. `.env` can still be used to define these variables along with other API keys.

## HR WebSocket / HTTP Auth

Both the HR WebSocket namespace (`/ws/hr`) and the corresponding HTTP endpoints (`/api/hr/*`) require an authentication token. Set `HR_DAEMON_TOKEN` in your environment or `.env` and supply it when connecting:

- **Bearer header**: `Authorization: Bearer <token>`
- **Query string**: `?token=<token>`
- **Socket.IO**: `io('/ws/hr', { auth: { token: '<token>' } })`

Any request to `/ws/hr` or `/api/hr/*` without the token will be rejected.


Utilities
FightControl/heartrate_mon/daemon.py — Unified heart-rate daemon for Polar straps. Run with ``python -m FightControl.heartrate_mon.daemon``.

tools/hr_logger.py — Logs heart-rate data received from the daemon. Run with ``python tools/hr_logger.py``.

tools/plot_hr.py — Plots heart-rate logs from ``hr_logger.py``.

controller_tagger.py — Logs tag/bookmark input via gamepad

csv_to_fighter_json.py — Convert CSV to fighter roster

codex.py — GPT-style code generator CLI (needs GOOGLE_API_KEY)

zip_modules.py — Auto-zip each cyclone_modules/ subdir (for packaging)

APIs
Fighters
http
Copy
Edit
GET /api/fighters
Returns all fighters from data/fighters.json.

Round Summaries
http
Copy
Edit
GET /api/round/summary
Returns a JSON payload describing the current round.

When ``image`` and ``session`` query parameters or a filename path are
supplied the corresponding summary image is streamed.

Folder Layout
Videos: CAMSERVER/<date>/<fight>/round_X/<camera>.mkv

Logs: FightControl/fighter_data/<name>/<date>/<round>/coach_notes.csv

Overlays: FightControl/data/overlay/{red_bpm.json, blue_bpm.json}

Overlay files now include a time field (UNIX epoch seconds).

## OBS Recording

1. **Add Source Record filters**

   - In OBS, add a *Source Record* filter to each camera scene (`main_cam`, `left_cam`, `right_cam`, `overhead_cam`) so every feed records independently.
   - Point each filter's `path` to a staging directory such as `${CYCLONE_BASE_DIR}/FightControl/current_fight/round_1`.
   - Use a deterministic `filename_formatting` like `%CCYY-%MM-%DD %hh-%mm-%ss %SOURCE_NAME` so Cyclone can identify the files.

2. **Configure `config/obs_outputs.json`** (or `config_legacy/obs_outputs.json`)

   ```json
   {
     "ws_url": "ws://127.0.0.1:4455",
     "outputs": ["main_cam", "left_cam", "right_cam", "overhead_cam"],
     "output_to_corner": {
       "main_cam": "neutral",
       "left_cam": "red",
       "right_cam": "blue",
       "overhead_cam": "neutral"
     },
     "source_records": {
       "main": 1,
       "left": 2,
       "right": 3,
       "overhead": 4
     },
     "staging_root": "${CYCLONE_BASE_DIR}/FightControl/current_fight",
     "dest_root": "${CYCLONE_BASE_DIR}/FightControl/fighter_data",
     "move_poll": {
       "max_wait_s": 30,
       "stable_s": 2,
       "glob_ext": "*.mkv"
     }
   }
   ```

   - `outputs` – names of the Source Record outputs (must match the filter names). Add your real output names to this array.
   - `output_to_corner` – maps each output to the fighter corner (`red`, `blue`, or `neutral`) which decides the final `fighter_data/<corner>` folder.
   - `source_records` – numeric IDs for the Source Record filters used by each camera. These IDs can be found in OBS's *Source Record* filter settings.
   - `staging_root` – temporary directory where OBS writes the files.
   - `dest_root` – root directory where Cyclone moves recordings after they finish.

3. **File flow**

   `OBS → staging → Cyclone move → fighter_data/<corner>/round_<n>/...`

Import the scene collection in `config_legacy/basic/scenes/4Cam_MediaSource.json` or update your own configuration. Adjust paths to match your environment (for example, Windows drive letters or POSIX separators).

### OBS WebSocket helper

The `utils.obs_ws` module offers a reusable OBS WebSocket client. It keeps a
single connection open, automatically reconnecting if needed. In addition to
starting and stopping outputs, it provides helpers for common tasks:

- `get_last_output_path(output_name)` – fetches the file path of the most
  recent recording for a given output.
- `set_text_source(source_name, text)` – updates the text displayed by a text
  source without disturbing other settings.

Create one `ObsWs` instance and reuse it for multiple calls to avoid repeated
handshakes.

Docker
Build:

bash
Copy
Edit
docker build -t cyclone .
Run:

bash
Copy
Edit
docker run --env-file .env -p 5050:5050 cyclone
Or use Docker Compose:

yaml
Copy
Edit
version: '3'
services:
  cyclone:
    build: .
    env_file: .env
    ports:
      - "5050:5050"
vbnet
Copy
Edit
