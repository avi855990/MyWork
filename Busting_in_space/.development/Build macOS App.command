#!/bin/zsh

cd "$(dirname "$0")"

python3 -m pip install --user -r requirements.txt
python3 -m PyInstaller \
  --noconfirm \
  --windowed \
  --name "Busting in Space" \
  --icon "app-icon.icns" \
  --add-data "background.mp3:." \
  --add-data "icon.png:." \
  shooter.py

cd dist
zip -r -X "Busting in Space macOS.zip" "Busting in Space.app"
cd ..

echo
echo "Build complete."
echo "Send this zip to another Mac:"
echo "dist/Busting in Space macOS.zip"
echo
read "reply?Press Enter to close..."
