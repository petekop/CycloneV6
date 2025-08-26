@echo off
rem Install and configure the Cyclone fight control system.
rem Usage: install.bat BaseDir [GoogleApiKey]

if "%~1"=="" (
    echo Usage: %~nx0 BaseDir [GoogleApiKey]
    exit /b 1
)

set "BaseDir=%~1"
set "GoogleApiKey=%~2"

rem Persist environment variables
set "CYCLONE_BASE_DIR=%BaseDir%"
setx CYCLONE_BASE_DIR "%BaseDir%" /M >nul 2>&1 || (
    echo Failed to set CYCLONE_BASE_DIR at machine scope. Falling back to user scope.
    setx CYCLONE_BASE_DIR "%BaseDir%" >nul
)

if not "%GoogleApiKey%"=="" (
    set "GOOGLE_API_KEY=%GoogleApiKey%"
    setx GOOGLE_API_KEY "%GoogleApiKey%" /M >nul 2>&1 || (
        echo Failed to set GOOGLE_API_KEY at machine scope. Falling back to user scope.
        setx GOOGLE_API_KEY "%GoogleApiKey%" >nul
    )
)

rem Create virtual environment
if not exist "%BaseDir%\venv" (
    python -m venv "%BaseDir%\venv"
)

rem Activate virtual environment
call "%BaseDir%\venv\Scripts\activate.bat"

rem Install Python dependencies
if exist "%BaseDir%\requirements.txt" (
    pip install -r "%BaseDir%\requirements.txt"
)
if exist "%BaseDir%\requirements-dev.txt" (
    pip install -r "%BaseDir%\requirements-dev.txt"
)

rem Ensure .env exists
if not exist "%BaseDir%\.env" (
    if exist "%BaseDir%\sample.env" (
        copy "%BaseDir%\sample.env" "%BaseDir%\.env" >nul
    ) else if exist "%BaseDir%\.env.example" (
        copy "%BaseDir%\.env.example" "%BaseDir%\.env" >nul
    ) else (
        echo Warning: sample.env or .env.example not found; .env not created.
    )
)

rem Download external binaries
call :DownloadOrSkip "https://github.com/aler9/mediamtx/releases/latest/download/mediamtx.exe" "%BaseDir%\CAMSERVER\mediamtx\mediamtx.exe"
call :DownloadOrSkip "https://github.com/REALDRAGNET/OBSCommand/releases/latest/download/OBSCommand.exe" "%BaseDir%\tools\OBSCommand\OBSCommand.exe"
call :DownloadOrSkip "https://github.com/REALDRAGNET/Cyclone/releases/latest/download/updater.exe" "%BaseDir%\config_legacy\updates\updater.exe"

goto :eof

:DownloadOrSkip
set "Url=%~1"
set "Dest=%~2"
if exist "%Dest%" (
    echo Skipping download; %Dest% already exists.
    goto :eof
)
for %%I in ("%Dest%") do set "DestDir=%%~dpI"
if not exist "%DestDir%" (
    mkdir "%DestDir%" >nul 2>&1
)

curl -L "%Url%" -o "%Dest%" >nul 2>&1
if not exist "%Dest%" (
    powershell -Command "try { Invoke-WebRequest -Uri '%Url%' -OutFile '%Dest%' -UseBasicParsing } catch {}" >nul 2>&1
)
if not exist "%Dest%" (
    echo Failed to download %Url%. Creating placeholder.
    type nul > "%Dest%"
)

:return
exit /b 0
