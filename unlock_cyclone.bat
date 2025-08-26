set CYCLONE_BASE_DIR=E:\Cyclone
@echo off
echo Unblocking all files in Cyclone directory...
powershell -Command "Set-ExecutionPolicy RemoteSigned -Scope CurrentUser -Force"
powershell -Command "Get-ChildItem \"%~dp0\" -Recurse | Unblock-File"
echo ✅ Cyclone scripts are now unblocked.
pause
