# ===== Cyclone STOP (E:\Cyclone) =====
$ErrorActionPreference = 'SilentlyContinue'

# Kill core apps
$names = 'python','obs64','mediamtx'
Get-Process | Where-Object { $names -contains $_.ProcessName } |
  Stop-Process -Force -ErrorAction SilentlyContinue

# Close the two tail windows we spawned for status files
try {
  Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" |
    Where-Object { $_.CommandLine -match 'Get-Content .+FightControl\\live_data\\(red|blue)_status\.txt' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
} catch {}

Write-Host 'Stopped Cyclone-related processes.' -ForegroundColor Green
