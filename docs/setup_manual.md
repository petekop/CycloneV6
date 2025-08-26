# Cyclone Setup Manual

This guide summarizes the steps required to install dependencies and launch the Cyclone fight control system.

## Automated installation (Windows)

```powershell
./scripts/install.ps1 -BaseDir "C:\\Cyclone" -GoogleApiKey "<key>"
./scripts/launch_cyclone.ps1
```

The installer sets `CYCLONE_BASE_DIR` and optionally `GOOGLE_API_KEY`, creates a virtual environment, installs requirements, and downloads external binaries with a 60-second timeout so the process won't hang on flaky networks. `scripts/launch_cyclone.ps1` uses `CYCLONE_BASE_DIR` and `GOOGLE_API_KEY` to start the server. The boot page automatically starts required services and shows their status. The sections below outline the manual steps.

## Prerequisites

- **Python 3.10** or newer must be installed and available on your system path.
- On Windows, PowerShell is required for the provided `.ps1` launch scripts.

## Installing dependencies

1. (Recommended) create and activate a Python virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```
2. Install the required packages using `pip` and set up commit hooks:
   ```bash
   pip install -r requirements.txt -r requirements-dev.txt
   pre-commit install
   ```
3. Copy `.env.example` to `.env` and provide your own values for the environment variables. At minimum a `GOOGLE_API_KEY` and a `CYCLONE_BASE_DIR` must be set. If you plan to use the heart-rate daemon, also define `HR_DAEMON_TOKEN`. Example:
   ```ini
   GOOGLE_API_KEY=your_key_here
   CYCLONE_BASE_DIR=/path/to/Cyclone
   HR_DAEMON_TOKEN=choose_a_secret
   CYCLONE_BLUE_H10_MAC=AA:BB:CC:DD:EE:FF
   CYCLONE_RED_H10_MAC=11:22:33:44:55:66
   ```
   Heart-rate strap MAC addresses are stored in `FightControl/heartrate_mon/config.json`, which serves as the single source of truth. The `CYCLONE_*_H10_MAC` variables override these values if set. The token secures the HR WebSocket namespace (`/ws/hr`) and HTTP endpoints (`/api/hr/*`). Send it via an `Authorization: Bearer <token>` header or add `?token=<token>` to request URLs. Socket.IO clients connect with `io('/ws/hr', { auth: { token: '<token>' } })`.
   See `README.md` for details on each variable. On Windows these steps can
   be automated with:
```powershell
./scripts/install.ps1 -BaseDir "C:\\Cyclone" -GoogleApiKey "<key>"
```

## Running the server

Activate your environment and start the Flask application from the repository root:
```bash
python cyclone_server.py
```
The server runs on **port 5050** and exposes the boot interface at `http://localhost:5050/boot`. The boot page automatically starts required services and displays their status. Launch OBS manually if it isn't running.

On Windows the preferred launcher is:
```powershell
./scripts/launch_cyclone.ps1
```

## Additional utilities

 - `FightControl/heartrate_mon/daemon.py` – unified heart-rate monitor for Polar
   straps. Launch with `python -m FightControl.heartrate_mon.daemon`.
 - `tools/hr_logger.py` – logs heart-rate data received from the daemon.
 - `tools/plot_hr.py` – generates a heart-rate graph from an existing
   `hr_data.json`. Run with `python -m tools.plot_hr <session>`.
 - `FightControl/scripts/csv_to_fighter_json.py` – converts roster CSV files
   into fighter JSON records using **pandas**.
 - `FightControl/controller_tagger.py` – polls connected controllers and logs
   coach tags or marked moments. The startup scripts run it automatically for
   controller detection and tagging.
 - `tests/` – automated test suite.

## Running tests

Activate your Python virtual environment and install the dependencies before running the automated tests.
Install the test client's Node dependencies and run `pytest`, which also executes the JavaScript WebSocket client:

```bash
source venv/bin/activate  # create it with `python -m venv venv` if needed
pip install -r requirements.txt -r requirements-dev.txt
npm install --prefix tests
pytest
```

To debug the JavaScript client separately, run:

```bash
npm test --prefix tests
```

Recorded video files are stored under `CAMSERVER/<date>/<fight>/round_X/<camera>`.
Outputs that cannot be associated with a specific camera or tag are placed in
`CAMSERVER/<date>/<fight>/round_X/misc/`. A file is considered *misc* when it
lacks tagging information identifying a camera.
CSV logs for each round are created in
`FightControl/fighter_data/<fighter>/<date>/round_X` when those folders are
generated.

Live BPM overlay files (`red_bpm.json` and `blue_bpm.json`) are written to
`FightControl/data/overlay`. Each JSON object includes a `time` value storing
the UNIX timestamp (seconds since the Unix epoch, 1 January 1970) representing
when the reading was taken.

## Touch Portal

Import the `.tpz2` files from the `TOUCHPORTAL` directory into the Touch Portal application. Edit each button to point at your server's IP and port. When the server is running, the panel will trigger fight and round logic.
