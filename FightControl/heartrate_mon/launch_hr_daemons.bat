@echo off
setlocal

set ROOT=E:\\Cyclone
set VENV=%ROOT%\venv\Scripts\python.exe

set HR_RED_MAC=A0:9E:1A:EB:9C:A5
set HR_BLUE_MAC=A0:9E:1A:EB:A2:36

start "HR RED"  powershell -NoExit -Command "Set-Location %ROOT%; $env:HR_RED_MAC='%HR_RED_MAC%';  .\venv\Scripts\python -u -X dev -m FightControl.heartrate_mon.hr_red"
start "HR BLUE" powershell -NoExit -Command "Set-Location %ROOT%; $env:HR_BLUE_MAC='%HR_BLUE_MAC%'; .\venv\Scripts\python -u -X dev -m FightControl.heartrate_mon.hr_blue"
start "RED STATUS"  powershell -NoExit -Command "Get-Content %ROOT%\FightControl\live_data\red_status.txt -Wait"
start "BLUE STATUS" powershell -NoExit -Command "Get-Content %ROOT%\FightControl\live_data\blue_status.txt -Wait"

endlocal
