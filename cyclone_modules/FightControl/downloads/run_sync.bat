@echo off
echo [Cyclone] Running fighter sync...

REM Adjust this to your actual Python path if needed
set PYTHON_EXE=python

REM Determine base directory from environment or script location
if defined CYCLONE_BASE_DIR (
    set "BASE_DIR=%CYCLONE_BASE_DIR%"
) else (
    for %%I in ("%~dp0..\..\..") do set "BASE_DIR=%%~fI"
)

REM Ensure the Python script can locate project modules
set "CYCLONE_BASE_DIR=%BASE_DIR%"
pushd "%BASE_DIR%"

REM Run the conversion script
%PYTHON_EXE% -m FightControl.scripts.csv_to_fighter_json

popd
echo Done. Fighters.json updated.
pause
