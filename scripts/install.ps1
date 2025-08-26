<#
.SYNOPSIS
Install and configure the Cyclone fight control system.

.DESCRIPTION
Sets required environment variables using machine scope with a fallback to
user scope when necessary. It then creates and activates a Python virtual
environment, installs dependencies, ensures an `.env` file exists, and
downloads external binaries used by the system.

.PARAMETER BaseDir
Root directory where the Cyclone repository resides.

.PARAMETER GoogleApiKey
Optional Google API key stored as an environment variable.

.EXAMPLE
./scripts/install.ps1 -BaseDir "C:\\Cyclone" -GoogleApiKey "<key>"
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$BaseDir,
    [string]$GoogleApiKey
)

function Download-OrSkip {
    param(
        [Parameter(Mandatory=$true)][string]$Url,
        [Parameter(Mandatory=$true)][string]$Destination,
        [int]$Retries = 3
    )

    if (Test-Path $Destination) {
        Write-Host "Skipping download; $Destination already exists."
        return
    }

    $dir = Split-Path -Parent $Destination
    if (!(Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir | Out-Null
    }

    for ($i = 0; $i -lt $Retries; $i++) {
        try {
            Invoke-WebRequest -Uri $Url -OutFile $Destination -UseBasicParsing -ErrorAction Stop
            return
        }
        catch {
            if ($i -lt $Retries - 1) {
                $delay = [Math]::Min([Math]::Pow(2, $i), 30)
                Start-Sleep -Seconds $delay
            }
        }
    }

    New-Item -ItemType File -Path $Destination -Force | Out-Null
    Write-Warning "Failed to download $Url after $Retries attempts. Placeholder created at $Destination."
}

try {
    [Environment]::SetEnvironmentVariable("CYCLONE_BASE_DIR", $BaseDir, "Machine")
    if ([Environment]::GetEnvironmentVariable("CYCLONE_BASE_DIR", "Machine") -eq $BaseDir) {
        Write-Host "Set CYCLONE_BASE_DIR (Machine) -> $BaseDir"
    } else {
        throw "Machine-scope assignment did not persist."
    }
} catch {
    Write-Warning "Failed to set CYCLONE_BASE_DIR at Machine scope. Falling back to User scope. $_"
    [Environment]::SetEnvironmentVariable("CYCLONE_BASE_DIR", $BaseDir, "User")
    Write-Warning "Using User-level CYCLONE_BASE_DIR: $BaseDir"
}
$env:CYCLONE_BASE_DIR = $BaseDir

if ($PSBoundParameters.ContainsKey('GoogleApiKey') -and $GoogleApiKey) {
    try {
        [Environment]::SetEnvironmentVariable("GOOGLE_API_KEY", $GoogleApiKey, "Machine")
    } catch {
        Write-Warning "Failed to set GOOGLE_API_KEY at Machine scope. Falling back to User scope. $_"
        [Environment]::SetEnvironmentVariable("GOOGLE_API_KEY", $GoogleApiKey, "User")
    }
    $env:GOOGLE_API_KEY = $GoogleApiKey
}

# Create virtual environment
$venvPath = Join-Path $BaseDir 'venv'
if (!(Test-Path $venvPath)) {
    python -m venv $venvPath
}

# Activate virtual environment
$activate = Join-Path $venvPath 'Scripts/Activate.ps1'
if (Test-Path $activate) {
    & $activate
} else {
    Write-Host "Failed to activate virtual environment at $activate" -ForegroundColor Red
    exit 1
}

# Install Python dependencies
$requirements = Join-Path $BaseDir 'requirements.txt'
$requirementsDev = Join-Path $BaseDir 'requirements-dev.txt'
if (Test-Path $requirements) {
    python -m pip install -r $requirements
}
if (Test-Path $requirementsDev) {
    python -m pip install -r $requirementsDev
}

# Ensure .env exists
$envExample = Join-Path $BaseDir '.env.example'
$envFile = Join-Path $BaseDir '.env'
if (!(Test-Path $envFile) -and (Test-Path $envExample)) {
    Copy-Item $envExample $envFile
} elseif (!(Test-Path $envFile)) {
    Write-Warning ".env.example not found; .env was not created"
}

# Download external binaries
$mediaMtxUrl = 'https://github.com/aler9/mediamtx/releases/latest/download/mediamtx.exe'
$obsCommandUrl = 'https://github.com/REALDRAGNET/OBSCommand/releases/latest/download/OBSCommand.exe'
$updaterUrl = 'https://github.com/REALDRAGNET/Cyclone/releases/latest/download/updater.exe'

$mediaMtxDest = Join-Path $BaseDir 'CAMSERVER/mediamtx/mediamtx.exe'
$obsCommandDest = Join-Path $BaseDir 'tools/OBSCommand/OBSCommand.exe'
$updaterDest = Join-Path $BaseDir 'config_legacy/updates/updater.exe'

Download-OrSkip -Url $mediaMtxUrl -Destination $mediaMtxDest
Download-OrSkip -Url $obsCommandUrl -Destination $obsCommandDest
Download-OrSkip -Url $updaterUrl -Destination $updaterDest
