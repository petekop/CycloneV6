$ErrorActionPreference = 'Stop'

# Resolve base directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$baseDir = if ($env:CYCLONE_BASE_DIR) { $env:CYCLONE_BASE_DIR } else { Split-Path $scriptDir -Parent }

$obsCandidates = @(
  (Join-Path $baseDir 'obs64 - Shortcut.lnk'),
  (Join-Path $baseDir 'obs64.exe'),
  (Join-Path $baseDir 'OBS/obs64.exe')
) | Where-Object { Test-Path $_ }

if ($obsCandidates.Count -eq 0) { Write-Error 'OBS executable not found in expected locations.'; exit 1 }
$obsExe = $obsCandidates[0]

Start-Process -FilePath $obsExe -WorkingDirectory (Split-Path $obsExe -Parent) -NoNewWindow
