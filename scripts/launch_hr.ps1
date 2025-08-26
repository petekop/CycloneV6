Set-Location E:\Cyclone
if (!(Test-Path .\venv\Scripts\python.exe)) {
  py -3.11 -m venv venv
  .\venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
  .\venv\Scripts\python.exe -m pip install -r requirements.txt
}
Start-Process powershell -ArgumentList '-NoExit','-Command','Set-Location E:\Cyclone; .\venv\Scripts\python.exe -u -X dev -m FightControl.heartrate_mon.hr_red'
Start-Process powershell -ArgumentList '-NoExit','-Command','Set-Location E:\Cyclone; .\venv\Scripts\python.exe -u -X dev -m FightControl.heartrate_mon.hr_blue'
Start-Process powershell -ArgumentList '-NoExit','-Command','Get-Content E:\Cyclone\FightControl\live_data\red_status.txt -Wait'
