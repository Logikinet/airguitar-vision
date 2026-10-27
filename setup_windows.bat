@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul
echo ==========================================================
echo    AIR GUITAR - Windows Environment Setup
 echo ==========================================================
if not exist ".venv\Scripts\python.exe" (
    py -3.11 -m venv .venv >nul 2>&1
    if errorlevel 1 (
        echo Python 3.11 launcher unavailable; trying your default Python.
        python -m venv .venv
        if errorlevel 1 goto failed
    )
)
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
echo.
echo Setup complete. Run start_windows.bat or demo_windows.bat.
pause
exit /b 0
:failed
echo.
echo Setup failed. See README.md; verify Python 3.11/3.12 and internet.
pause
exit /b 1
