#!/bin/zsh

cd "$(dirname "$0")"

if [ -d "Busting in Space.app" ]; then
  open "Busting in Space.app"
  exit 0
fi

clear
echo "Busting in Space.app was not found."
echo
echo "If you opened this from inside the zip file, close this window first."
echo "Then double-click the zip or right-click it and choose Extract/Open,"
echo "open the extracted folder, and double-click this file again."
echo
read "reply?Press Enter to close..."
