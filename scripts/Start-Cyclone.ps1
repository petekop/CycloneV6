# ===== Start-Cyclone.ps1 =====
param([string]$Base = "E:\Cyclone")
$ErrorActionPreference = "SilentlyContinue"
$env:CYCLONE_BASE_DIR = $Base

$py = Join-Path $Base 'venv\Scripts\python.exe'
$bootUrl = 'http://127.0.0.1:8765/boot'

# ensure Flask server is running
$up = $false
try { $up = (Invoke-WebRequest -UseBasicParsing $bootUrl -TimeoutSec 1).StatusCode -eq 200 } catch {}
if (-not $up) {
  Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force
  Start-Process $py -ArgumentList @('-m','server_boot.app') -WorkingDirectory $Base | Out-Null
  do { Start-Sleep 0.5 } until ((Test-NetConnection 127.0.0.1 -Port 8765 -WarningAction SilentlyContinue).TcpTestSucceeded)
}

# open old TouchPortal boot and kick the system boot
Start-Process $bootUrl
try {
  Invoke-WebRequest -Method POST -UseBasicParsing 'http://127.0.0.1:8765/api/start-system' -TimeoutSec 2 | Out-Null
} catch {}

Write-Host "Boot page opened. System boot kicked." -ForegroundColor Green
