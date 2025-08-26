@echo off
setlocal
set "BASE=C:\Cyclone"
set "PY=%BASE%\venv\Scripts\python.exe"

if not exist "%PY%" (
  echo ERROR: Python venv not found at %PY%
  exit /b 1
)

powershell -NoProfile -Command "Start-Process -WindowStyle Minimized -FilePath '%PY%' -ArgumentList '-u','-X','dev','-m','FightControl.heartrate_mon.hr_red'  -WorkingDirectory '%BASE%'"
powershell -NoProfile -Command "Start-Process -WindowStyle Minimized -FilePath '%PY%' -ArgumentList '-u','-X','dev','-m','FightControl.heartrate_mon.hr_blue' -WorkingDirectory '%BASE%'"

exit /b 0
