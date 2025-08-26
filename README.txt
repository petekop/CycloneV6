== Cyclone Boot Fix (Windows) ==

Copy this whole folder into C:\Cyclone (keeping the 'config' and 'scripts' subfolders).

Then run in PowerShell (as your user):
  cd C:\Cyclone
  powershell -ExecutionPolicy Bypass -File .\patch_boot_status.ps1

Start server:
  .\venv\Scripts\python -u .\cyclone_server.py

Boot:
  Invoke-WebRequest http://127.0.0.1:5050/api/boot/start  | % Content
  Invoke-WebRequest http://127.0.0.1:5050/api/boot/status | % Content
