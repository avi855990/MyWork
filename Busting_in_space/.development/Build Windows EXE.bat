@echo off
cd /d "%~dp0"

py -3 -m pip install -r requirements.txt
py -3 -m PyInstaller ^
  --noconfirm ^
  --windowed ^
  --name "Busting in Space" ^
  --add-data "background.mp3;." ^
  --add-data "icon.png;." ^
  shooter.py

powershell -NoProfile -Command "Compress-Archive -Path 'dist\Busting in Space' -DestinationPath 'dist\Busting in Space Windows.zip' -Force"

echo.
echo Build complete.
echo Send this zip to another Windows computer:
echo dist\Busting in Space Windows.zip
echo.
pause
