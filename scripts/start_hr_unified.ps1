# Determine repository root relative to this script
$repoRoot = Resolve-Path "$PSScriptRoot\.."

# Path to the virtual environment activation script
$venvActivate = Join-Path $repoRoot 'venv\Scripts\activate.bat'

if (-not (Test-Path $venvActivate)) {
    Write-Error "Virtual environment not found at $venvActivate"
    exit 1
}

$cmdTemplate = "call `"$venvActivate`" && cd /d `"$repoRoot`" && python -m FightControl.heartrate_mon.hr_{0}"

Start-Process -FilePath "cmd.exe" -ArgumentList "/k", ($cmdTemplate -f "red") -WorkingDirectory $repoRoot
Start-Process -FilePath "cmd.exe" -ArgumentList "/k", ($cmdTemplate -f "blue") -WorkingDirectory $repoRoot

