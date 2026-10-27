@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo First run: setting up Python environment...
    call setup_windows.bat
    if errorlevel 1 exit /b 1
)
".venv\Scripts\python.exe" -c "import PIL" >nul 2>&1
if errorlevel 1 (
    echo New Chinese UI requires Pillow. Running dependency setup...
    call setup_windows.bat
    if errorlevel 1 exit /b 1
)
".venv\Scripts\python.exe" main.py %*
if errorlevel 1 (
  echo.
  echo Error starting Air Guitar. See README.md.
  pause
  exit /b 1
)
exit /b 0
