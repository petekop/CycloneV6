# ===== Cyclone FULL BOOT (sticky) — E:\Cyclone =====
$ErrorActionPreference = 'Stop'
$Base = 'E:\Cyclone'
$env:CYCLONE_BASE_DIR = $Base
Set-Location $Base
$py = Join-Path $Base 'venv\Scripts\python.exe'

# venv guard (3.11)
if (!(Test-Path $py)) {
  py -3.11 -m venv (Join-Path $Base 'venv')
  & $py -m pip install --upgrade pip setuptools wheel
}
& $py -m pip install Flask --disable-pip-version-check | Out-Null

# boot status file
$live = Join-Path $Base 'FightControl\live_data'
New-Item -ItemType Directory -Force $live | Out-Null
$status = Join-Path $live 'boot_status.json'
function Set-Status([int]$step,[int]$total,[string]$msg,[bool]$done=$false) {
  $obj = [ordered]@{ step=$step; total=$total; message=$msg; done=$done }
  $obj | ConvertTo-Json | Set-Content -Encoding UTF8 -Path $status
}

# start Cyclone Server (Flask) and open boot page
Set-Status 0 6 'Starting Cyclone Server…'
Start-Process -FilePath $py -ArgumentList @('-m','server_boot.app') -WorkingDirectory $Base
# wait for server
for ($i=0; $i -lt 40; $i++) {
  try { (Invoke-WebRequest -UseBasicParsing 'http://127.0.0.1:8765/status' -TimeoutSec 1) | Out-Null; break } catch { Start-Sleep 0.5 }
}
Start-Process 'http://127.0.0.1:8765/boot'

# 1) MediaMTX (sticky)
$mtxExe = 'E:\Cyclone\CAMSERVER\mediamtx\mediamtx.exe'
$mtxCfg = 'E:\Cyclone\CAMSERVER\mediamtx\mediamtx_tcp_fixed_2025.yml'
Set-Status 1 6 'Starting MediaMTX…'
if (Test-Path $mtxExe -and (Test-Path $mtxCfg)) {
  # kill old, then sticky launch in its own window
  Get-Process mediamtx -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
  Start-Process powershell -ArgumentList '-NoExit','-Command',("Set-Location '$(Split-Path $mtxExe)'; & .\$(Split-Path $mtxExe -Leaf) '$mtxCfg'") | Out-Null
} else {
  Write-Warning 'MediaMTX not started (exe or config not found).'
}

# 2) OBS
Set-Status 2 6 'Starting OBS…'
$obsLink = 'E:\Cyclone\obs64 - Shortcut.lnk'
if (Test-Path $obsLink) { Start-Process $obsLink } else { Write-Warning "OBS shortcut not found: $obsLink" }

# helper to launch python modules
function Start-PyMod([string]$mod) {
  Start-Process -FilePath $py -ArgumentList @('-u','-X','dev','-m',$mod) -WorkingDirectory $Base
}

# 3) HR red
Set-Status 3 6 'Starting HR monitor (RED)…'
Start-PyMod 'FightControl.heartrate_mon.hr_red'

# 4) HR blue
Set-Status 4 6 'Starting HR monitor (BLUE)…'
Start-PyMod 'FightControl.heartrate_mon.hr_blue'

# 5) Round Manager
Set-Status 5 6 'Starting Round Manager…'
Start-PyMod 'FightControl.round_manager'

# tails
Start-Process powershell -ArgumentList '-NoExit','-Command',("while(!(Test-Path '$live\red_status.txt')){Start-Sleep 1}; Get-Content '$live\red_status.txt' -Wait")   | Out-Null
Start-Process powershell -ArgumentList '-NoExit','-Command',("while(!(Test-Path '$live\blue_status.txt')){Start-Sleep 1}; Get-Content '$live\blue_status.txt' -Wait") | Out-Null

# finish
Set-Status 6 6 'All services up. Redirecting…' $true
Start-Process 'http://127.0.0.1:8765/index'
Write-Host "`nLaunched: MediaMTX (sticky), OBS, HR red/blue, RoundManager, and tails." -ForegroundColor Cyan
