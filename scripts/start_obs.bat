@echo off
setlocal
set "BASE=E:\Cyclone"

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
echo   E:\Cyclone\obs64 - Shortcut.lnk
echo   E:\Cyclone\obs64.exe
echo   E:\Cyclone\OBS\obs64.exe
exit /b 1
