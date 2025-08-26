# patch_boot_status.ps1 - make boot route spawn .bat/.ps1/.lnk correctly
param([string]$File = "C:\Cyclone\routes\boot_status.py")

Write-Host "Patching $File" -ForegroundColor Cyan
if (!(Test-Path $File)) { Write-Error "File not found: $File"; exit 1 }

$backup = "$File.bak_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
Copy-Item $File $backup -Force
Write-Host "Backup -> $backup"

$content = Get-Content -Raw -LiteralPath $File

# Ensure imports
if ($content -notmatch "(?m)^\s*import\s+subprocess\b") {
  $content = "import subprocess`n" + $content
}
if ($content -notmatch "(?m)^\s*import\s+os\b") {
  $content = $content -replace "(?m)(^(\s*import\b.*\n)+)", "$1import os`n"
}

# Insert _wrap_command helper if missing
if ($content -notmatch "(?m)^\s*def\s+_wrap_command\s*\(") {
  $helper = @"
def _wrap_command(script_path: str):
    sp = str(script_path).strip().strip('""').strip(\"'\")
    ext = os.path.splitext(sp)[1].lower()
    if ext in ('.bat', '.cmd'):
        return ['cmd.exe', '/c', sp]
    if ext == '.ps1':
        return ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', sp]
    if ext == '.lnk':
        return ['powershell', '-NoProfile', '-Command', f"Start-Process -FilePath '{sp}'"]
    return [sp]
"@
  $content = $content -replace "(?s)(^(\s*import\b.*?\n)+)", "$1`n$helper`n"
}

# Wrap subprocess.Popen first argument with _wrap_command(...)
$regex = [regex]"subprocess\.Popen\(\s*([^\),]+)(?<rest>,[\s\S]*?)\)"
$patched = $regex.Replace($content, "subprocess.Popen(_wrap_command($1)$2)")

Set-Content -LiteralPath $File -Value $patched -Encoding UTF8
Write-Host "Patched successfully." -ForegroundColor Green
