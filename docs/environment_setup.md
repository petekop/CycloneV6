🚀 Windows Quick Start
powershell
Copy
Edit
./scripts/install.ps1 -BaseDir "C:\\Cyclone" -GoogleApiKey "<key>"
./scripts/launch_cyclone.ps1
install.ps1 sets CYCLONE_BASE_DIR and optionally GOOGLE_API_KEY, creates the virtual environment, installs requirements, and downloads required binaries.
It uses a 60-second timeout for each download to avoid hanging if the network becomes unresponsive.

scripts/launch_cyclone.ps1 activates that environment (using CYCLONE_BASE_DIR), starts the server, and opens the boot page. The boot page automatically starts required services and reports their status. Launch OBS manually if needed.

The manual steps below describe the equivalent process.

🛠 1. Create a Python Virtual Environment (Manual Alternative)
bash
Copy
Edit
python -m venv venv
source venv/bin/activate  # or .\venv\Scripts\Activate on Windows
pip install -r requirements.txt
pip install -r requirements-dev.txt  # for dev and test tools
pre-commit install  # set up git hooks
⚙️ 2. Configure Environment Variables
Copy `.env.example` to `.env` and set the values for your system.

Required:

GOOGLE_API_KEY – for tools like tools/codex.py that use Google's AI

CYCLONE_BASE_DIR – path to the Cyclone root

HR_DAEMON_TOKEN – auth token for the HR WebSocket namespace (`/ws/hr`) and HTTP endpoints (`/api/hr/*`)

Include the token with HTTP requests via an `Authorization: Bearer <token>` header or by adding `?token=<token>` to the query string.
Socket.IO clients should connect with `io('/ws/hr', { auth: { token: '<token>' } })`.

OBS WebSocket (loaded automatically from `.env`):

- `OBS_WS_HOST` / `OBS_WS_PORT` or `OBS_WS_URL` – location of the OBS WebSocket server.
- `OBS_WS_PASSWORD` – password for OBS WebSocket.
- `OBS_CONNECT_TIMEOUT` – seconds to wait when connecting (default: 5).

Optional packages:

matplotlib – enables HR graph generation in cyclone_modules/HRLogger/hr_logger.py

pandas – enables CSV roster conversion in FightControl/scripts/csv_to_fighter_json.py

concurrent-log-handler – provides process-safe log rotation for Cyclone's
application and access logs

💡 On Windows, these steps are automated with:

powershell
Copy
Edit
./scripts/install.ps1 -BaseDir "C:\\Cyclone" -GoogleApiKey "<key>"
📦 3. Obtain External Executables
Cyclone relies on several external binaries. You must download these manually and place them in the correct folders:

🎥 MediaMTX
Used for multi-camera streaming.

Download: MediaMTX releases

Extract and place mediamtx in CAMSERVER/mediamtx

On Unix:

bash
Copy
Edit
chmod +x CAMSERVER/mediamtx/mediamtx
🎮 OBSCommand
Used to control OBS via CLI.

Download: OBSCommand releases

Place OBSCommand.exe in tools/OBSCommand

🔄 Updater
Download updater.exe from Cyclone release assets

Place it in config_legacy/updates

🌐 4. Launch the Server
From the Cyclone root:

bash
Copy
Edit
python cyclone_server.py
The boot page automatically starts required services and shows their status.

For development, use the helper script:

bash
Copy
Edit
./run_dev
It launches the server with auto-reload enabled.

Set `CYCLONE_DEBUG=1` to enable Flask's debugger and reloader. The default is
`CYCLONE_DEBUG=0`, which runs Cyclone with `use_reloader=False`.

When the optional access log handler is installed, enable HTTP request logs
by setting `CYCLONE_ACCESS_LOG=1`. Logs are written to `logs/access.log`.
⚡ Windows Helper Scripts
Instead of running Python directly, you can use:

powershell
Copy
Edit
./scripts/launch_cyclone.ps1
This script:

- Activates the environment (based on CYCLONE_BASE_DIR)
- Starts the Flask server and opens the boot interface

The boot page handles service startup and status checks. If OBS does not start, launch it manually.
