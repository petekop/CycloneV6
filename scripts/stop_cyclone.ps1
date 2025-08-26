# ===== Cyclone STOP (E:\Cyclone) =====
$ErrorActionPreference = "SilentlyContinue"

# core processes
$names = 'mediamtx','obs64','python'
Get-Process | Where-Object { $names -contains $_.ProcessName } |
  Stop-Process -Force -ErrorAction SilentlyContinue

# kill tail windows
Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" |
  Where-Object { $_.CommandLine -match 'Get-Content .+FightControl\\live_data\\(red|blue)_status\.txt' } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

Write-Host "Stopped Cyclone-related processes." -ForegroundColor Green
