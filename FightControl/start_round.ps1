$baseDir = $env:CYCLONE_BASE_DIR
if (-not $baseDir) {
    $baseDir = Split-Path -Parent $PSScriptRoot
}
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Error "Python interpreter not found in PATH."
    exit 1
}
$command = 'from FightControl.round_manager import start_round_sequence; start_round_sequence()'
Start-Process -FilePath $python.Source -ArgumentList @('-c', $command) -WorkingDirectory $baseDir
