# Simple development launcher for Cyclone
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$projectRoot = Split-Path $scriptDir -Parent
$env:CYCLONE_AUTOSTART = "1"
python "$projectRoot/cyclone_server.py"
