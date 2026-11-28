@echo off
rem Double-click this file to start the Pilot Vacation Scheduler on Windows.
cd /d "%~dp0"
set PY=python
where py >nul 2>nul && set PY=py -3
if not exist .venv\Scripts\python.exe (
  echo First start: setting things up. This takes a minute or two...
  %PY% -m venv .venv
  if errorlevel 1 goto nopython
)
.venv\Scripts\python.exe -m pip install --quiet --disable-pip-version-check -r requirements.txt
if errorlevel 1 goto failed
.venv\Scripts\python.exe run.py
pause
exit /b 0

:nopython
echo.
echo Python was not found. Install it from https://www.python.org/downloads/
echo and tick "Add python.exe to PATH" on the first screen of the installer.
pause
exit /b 1

:failed
echo.
echo Setup failed. Check your internet connection and try again.
pause
exit /b 1
