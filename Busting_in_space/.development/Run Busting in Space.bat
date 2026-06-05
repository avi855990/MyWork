@echo off
cd /d "%~dp0"
py -3 shooter.py
if errorlevel 1 (
    echo.
    echo Could not start the game with the Python launcher.
    echo Trying python instead...
    python shooter.py
)
pause
