# 🚀 Start MediaMTX Cam Server
$baseDir = $env:CYCLONE_BASE_DIR
if (-not $baseDir) { $baseDir = 'E:\Cyclone' }
Start-Process `
    -FilePath (Join-Path (Join-Path (Join-Path $baseDir 'CAMSERVER') 'mediamtx') 'mediamtx.exe') `
    -ArgumentList (Join-Path (Join-Path (Join-Path $baseDir 'CAMSERVER') 'mediamtx') 'mediamtx_tcp_office.yml') `
    -WindowStyle Minimized
Start-Sleep -Seconds 2

# 🎥 Start OBS Studio
Start-Process -FilePath "$baseDir\obs64 - Shortcut.lnk" -WindowStyle Minimized
Start-Sleep -Seconds 5
