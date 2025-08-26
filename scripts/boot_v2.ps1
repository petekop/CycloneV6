# ===== Cyclone FULL BOOT (robust) — E:\Cyclone =====
$ErrorActionPreference = 'Stop'
$Base = 'E:\Cyclone'
$py   = Join-Path $Base 'venv\Scripts\python.exe'
Set-Location $Base
$env:CYCLONE_BASE_DIR = $Base

# HR MON config (create only if missing)
$cfg = Join-Path $Base 'FightControl\heartrate_mon\config.json'
if (!(Test-Path $cfg)) {
  $obj = [ordered]@{ red = 'A0:9E:1A:EB:9C:A5'; blue = 'A0:9E:1A:EB:A2:36' }
  $obj | ConvertTo-Json | Set-Content -Encoding ASCII -Path $cfg
}

# venv (Python 3.11)
if (!(Test-Path $py)) {
  py -3.11 -m venv (Join-Path $Base 'venv')
  & $py -m pip install --upgrade pip setuptools wheel
  if (Test-Path (Join-Path $Base 'requirements.txt')) {
    & $py -m pip install -r (Join-Path $Base 'requirements.txt')
  }
}

function Start-PyMod([string]$mod) {
  Start-Process -FilePath $py -ArgumentList @('-u','-X','dev','-m',$mod) -WorkingDirectory $Base
}

# ---- MediaMTX (sticky window, positional YAML arg) ----
$mtxExe = 'E:\Cyclone\CAMSERVER\mediamtx\mediamtx.exe'
$mtxCfg = 'E:\Cyclone\CAMSERVER\mediamtx\mediamtx_tcp_fixed_2025.yml'
if ((Test-Path $mtxExe) -and (Test-Path $mtxCfg)) {
  Get-Process mediamtx -ErrorAction SilentlyContinue | Stop-Process -Force
  $mtxDir = Split-Path $mtxExe
  $cmd = "Set-Location '$mtxDir'; & '.\mediamtx.exe' '$mtxCfg'; Write-Host ('MediaMTX exited with code ' + `$LASTEXITCODE) -ForegroundColor Yellow"
  Start-Process powershell -ArgumentList '-NoExit','-Command',$cmd
} else {
  Write-Warning 'MediaMTX not started (exe or config not found).'
}

# OBS via shortcut
if (Test-Path 'E:\Cyclone\obs64 - Shortcut.lnk') {
  Start-Process 'E:\Cyclone\obs64 - Shortcut.lnk'
} else {
  Write-Warning 'OBS shortcut not found: E:\Cyclone\obs64 - Shortcut.lnk'
}

# Core services
Start-PyMod 'FightControl.heartrate_mon.hr_red'
Start-PyMod 'FightControl.heartrate_mon.hr_blue'
Start-PyMod 'FightControl.round_manager'

# Tails (wait for files so no path errors)
$live = Join-Path $Base 'FightControl\live_data'
New-Item -ItemType Directory -Force $live | Out-Null
Start-Process powershell -ArgumentList '-NoExit','-Command',("while(!(Test-Path '$live\red_status.txt')){Start-Sleep 1};  Get-Content '$live\red_status.txt'  -Wait")
Start-Process powershell -ArgumentList '-NoExit','-Command',("while(!(Test-Path '$live\blue_status.txt')){Start-Sleep 1}; Get-Content '$live\blue_status.txt' -Wait")

Write-Host "`nLaunched: MediaMTX (sticky), OBS, HR red/blue, RoundManager, and tails." -ForegroundColor Cyan
