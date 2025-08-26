$ErrorActionPreference = 'Stop'

# Resolve base directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$baseDir = if ($env:CYCLONE_BASE_DIR) { $env:CYCLONE_BASE_DIR } else { Split-Path $scriptDir -Parent }

$mtxExe = Join-Path $baseDir 'CAMSERVER/mediamtx/mediamtx.exe'
$mtxCfg = Join-Path $baseDir 'CAMSERVER/mediamtx/mediamtx_tcp_office.yml'

if (-not (Test-Path $mtxExe)) { Write-Error "MediaMTX binary not found: $mtxExe"; exit 1 }
if (-not (Test-Path $mtxCfg)) { Write-Error "MediaMTX config not found: $mtxCfg"; exit 1 }

Start-Process -FilePath $mtxExe -ArgumentList $mtxCfg -WorkingDirectory (Split-Path $mtxExe -Parent) -NoNewWindow
