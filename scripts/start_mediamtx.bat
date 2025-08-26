@echo off
setlocal
set "BASE=E:\Cyclone"
set "MTX=%BASE%\CAMSERVER\mediamtx\mediamtx.exe"
set "CFG=%BASE%\CAMSERVER\mediamtx\mediamtx_tcp_fixed_2025.yml"
set "LOG=%BASE%\CAMSERVER\mediamtx\logs"
if not exist "%LOG%" mkdir "%LOG%"
set "STAMP=%DATE:~-4%%DATE:~4,2%%DATE:~7,2%_%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%"
set "OUT=%LOG%\mediamtx_%STAMP%.log"

rem Kill any old instance so ports are free
taskkill /IM mediamtx.exe /F >nul 2>&1

if not exist "%MTX%" (
  echo ERROR: mediamtx.exe not found at %MTX%
  exit /b 1
)
if not exist "%CFG%" (
  echo ERROR: mediamtx config not found at %CFG%
  exit /b 1
)

echo Starting MediaMTX with %CFG%
powershell -NoProfile -Command "Start-Process -FilePath '%MTX%' -ArgumentList '%CFG%' -WorkingDirectory (Split-Path '%MTX%') -WindowStyle Minimized -RedirectStandardOutput '%OUT%' -RedirectStandardError '%OUT%'"
exit /b 0
