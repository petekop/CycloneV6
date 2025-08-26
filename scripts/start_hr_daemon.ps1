$ErrorActionPreference = 'Stop'

# Resolve base directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$baseDir = if ($env:CYCLONE_BASE_DIR) { $env:CYCLONE_BASE_DIR } else { Split-Path $scriptDir -Parent }

$pythonExe = Join-Path $baseDir 'venv\Scripts\python.exe'
$hrCandidates = @(
  (Join-Path $baseDir 'daemons\hr_daemon.py'),
  (Join-Path $baseDir 'services\hr_daemon.py'),
  (Join-Path $baseDir 'scripts\hr_daemon.py'),
  (Join-Path $baseDir 'bin\hr_daemon.exe')
) | Where-Object { Test-Path $_ }

if ($hrCandidates.Count -eq 0) { Write-Error 'HR daemon not found in expected locations.'; exit 1 }
$hrPath = $hrCandidates[0]

if ($hrPath -like '*.py') {
    if (-not (Test-Path $pythonExe)) { Write-Error "Python executable not found: $pythonExe"; exit 1 }
    Start-Process -FilePath $pythonExe -ArgumentList $hrPath -WorkingDirectory $baseDir -NoNewWindow
} else {
    Start-Process -FilePath $hrPath -WorkingDirectory $baseDir -NoNewWindow
}
