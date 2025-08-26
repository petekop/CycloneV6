# Scripts

Helper scripts for the Cyclone project.

## scripts/launch_cyclone.ps1

`scripts/launch_cyclone.ps1` starts Cyclone components. The Flask server's stdout and stderr are written to `state/flask.log` relative to the project base directory (`CYCLONE_BASE_DIR`). When the health check fails, the script outputs the last few lines from this log to the console to aid debugging.

## scripts/run_dev.ps1 / scripts/run_dev.sh

These helpers set `CYCLONE_AUTOSTART=1` and run `python cyclone_server.py` from the project root for quick development launches.

## scripts/install.ps1 / scripts/install.bat

The install scripts set up dependencies and persist environment variables. They
require a base directory argument (`--base-dir`) that points to the Cyclone
repository's root. For PowerShell, specify the parameter as `-BaseDir`; the
batch version takes the base directory as its first argument.

Examples:

```powershell
./scripts/install.ps1 -BaseDir "C:\\Cyclone"
```

```bat
scripts\install.bat C:\Cyclone
```
