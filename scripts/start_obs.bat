@echo off
setlocal
set "BASE=C:\Cyclone"

if exist "%BASE%\obs64 - Shortcut.lnk" (
  powershell -NoProfile -Command "Start-Process -FilePath '%BASE%\obs64 - Shortcut.lnk' -WindowStyle Minimized"
  exit /b 0
)

if exist "%BASE%\obs64.exe" (
  powershell -NoProfile -Command "Start-Process -FilePath '%BASE%\obs64.exe' -WorkingDirectory '%BASE%' -WindowStyle Minimized"
  exit /b 0
)

if exist "%BASE%\OBS\obs64.exe" (
  powershell -NoProfile -Command "Start-Process -FilePath '%BASE%\OBS\obs64.exe' -WorkingDirectory '%BASE%\OBS' -WindowStyle Minimized"
  exit /b 0
)

echo ERROR: OBS not found. Looked for:
echo   C:\Cyclone\obs64 - Shortcut.lnk
echo   C:\Cyclone\obs64.exe
echo   C:\Cyclone\OBS\obs64.exe
exit /b 1
