# launch_cyclone.ps1
# Launch HR daemons (RED/BLUE) in separate terminals, then Cyclone server, then Chrome app-mode index page.

$ErrorActionPreference = 'Stop'

# --- Resolve base dir ---
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$baseDir   = if ($env:CYCLONE_BASE_DIR) { $env:CYCLONE_BASE_DIR } else { Split-Path $scriptDir -Parent }
$env:CYCLONE_BASE_DIR = $baseDir

# --- Paths ---
$pythonExe    = Join-Path $baseDir 'venv\Scripts\python.exe'
$serverScript = Join-Path $baseDir 'cyclone_server.py'
$baseUrl      = 'http://127.0.0.1:5050'
$indexUrl     = "$baseUrl/index"
$healthUrl    = "$baseUrl/api/health"
$bootStartUrl = "$baseUrl/api/boot/start"
$bootStatusUrl = "$baseUrl/api/boot/status"

# Load boot paths and resolve HR daemon path
$bootPathsFile = Join-Path $baseDir 'config\boot_paths.yml'
$hrDaemon = $null
if (Test-Path $bootPathsFile) {
  try {
    $bootPaths = Get-Content $bootPathsFile | ConvertFrom-Yaml
    $hrPath = $bootPaths.hr_daemon.exe
    if ($hrPath) {
      if (-not (Test-Path $hrPath)) {
        $hrPath = Join-Path $baseDir $hrPath
      }
      if (Test-Path $hrPath) {
        $hrDaemon = (Resolve-Path $hrPath).Path
      } else {
        Write-Warning "HR daemon path not found: $hrPath"
      }
    } else {
      Write-Warning "HR daemon executable not specified in $bootPathsFile"
    }
  } catch {
    Write-Warning "Failed to parse boot paths from $bootPathsFile: $_"
  }
} else {
  Write-Warning "Boot paths file not found: $bootPathsFile"
}

# --- Sanity checks ---
if (-not (Test-Path $pythonExe))    { Write-Error "Python venv not found: $pythonExe";    exit 1 }
if (-not (Test-Path $serverScript)) { Write-Error "Server script not found: $serverScript"; exit 1 }

# Ensure Cyclone autostarts inside server
$env:CYCLONE_AUTOSTART = "1"

# --- Start Flask server ---
Start-Process -FilePath $pythonExe `
  -ArgumentList @($serverScript) `
  -WorkingDirectory $baseDir `
  -NoNewWindow

# --- Wait for server health ---
$timeout = [TimeSpan]::FromSeconds(60)
$sw = [Diagnostics.Stopwatch]::StartNew()
while ($true) {
  try {
    Invoke-RestMethod -Uri $healthUrl -TimeoutSec 2 | Out-Null
    break
  } catch {
    if ($sw.Elapsed -ge $timeout) {
      Write-Error "Timed out waiting for Cyclone health check at $healthUrl"
      exit 1
    }
    Start-Sleep -Seconds 1
  }
}

# --- Kick off boot sequence ---
try {
  Invoke-RestMethod -Uri $bootStartUrl -Method Post -TimeoutSec 5 | Out-Null
} catch {
  Write-Error "Failed to start boot sequence: $_"
  exit 1
}

# --- Poll boot status until READY ---
$sw.Restart()
while ($true) {
  try {
    $resp = Invoke-RestMethod -Uri $bootStatusUrl -TimeoutSec 2
    $errors = @()
    if ($resp.services) {
      foreach ($kv in $resp.services.GetEnumerator()) {
        if ($kv.Value -eq 'ERROR') { $errors += $kv.Key }
      }
      if ($errors.Count -gt 0) {
        Write-Error "Boot failed for: $($errors -join ', ')"
        exit 1
      }
    }
    if ($resp.ready) { break }
  } catch {
    # ignore polling errors
  }
  if ($sw.Elapsed -ge $timeout) {
    Write-Error "Timed out waiting for Cyclone boot to complete"
    exit 1
  }
  Start-Sleep -Seconds 1
}

# --- Open index page in Chrome app mode ---
$chrome = Get-Command 'chrome.exe' -ErrorAction SilentlyContinue
if ($chrome) {
  Start-Process -FilePath $chrome.Source -ArgumentList "--app=$indexUrl"
} else {
  Start-Process $indexUrl
}
