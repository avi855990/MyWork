@echo off
setlocal EnableExtensions

pushd "%~dp0" >nul 2>&1
set "ROOT=%CD%"
set "DEV=%ROOT%\.development"
set "GAME_EXE=%DEV%\dist\Busting in Space\Busting in Space.exe"
set "BUILD_LOG=%DEV%\windows-build.log"
set "PYTHON_INSTALLER_URL=https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe"
set "PYTHON_INSTALLER=%TEMP%\busting-python-installer.exe"

if not exist "%DEV%\shooter.py" (
    echo The game files were not found.
    echo.
    echo If you opened this from inside the zip file, close this window first.
    echo Then right-click "Busting in space.zip" and choose "Extract All...".
    echo After extraction, open the extracted folder and double-click this file again.
    echo.
    pause
    exit /b 1
)

if exist "%GAME_EXE%" (
    start "" "%GAME_EXE%"
    exit /b 0
)

call :find_python
if errorlevel 1 (
    call :install_python
    call :find_python
)

if errorlevel 1 (
    echo Could not install or find Python automatically.
    echo Please install Python 3 from https://www.python.org/downloads/ and run this file again.
    pause
    exit /b 1
)

echo Preparing Busting in Space for Windows. This may take a few minutes...
echo Logs are saved to "%BUILD_LOG%".

pushd "%DEV%" >nul
%PYTHON_CMD% -m pip install --upgrade pip > "%BUILD_LOG%" 2>&1
%PYTHON_CMD% -m pip install -r requirements.txt >> "%BUILD_LOG%" 2>&1
if errorlevel 1 goto build_failed

%PYTHON_CMD% -m PyInstaller ^
  --noconfirm ^
  --windowed ^
  --name "Busting in Space" ^
  --add-data "background.mp3;." ^
  --add-data "icon.png;." ^
  shooter.py >> "%BUILD_LOG%" 2>&1
if errorlevel 1 goto build_failed
popd >nul

if exist "%GAME_EXE%" (
    start "" "%GAME_EXE%"
    exit /b 0
)

echo Build finished, but the game executable was not found.
echo Check "%BUILD_LOG%" for details.
pause
exit /b 1

:build_failed
popd >nul
echo Windows build failed.
echo Check "%BUILD_LOG%" for details.
pause
exit /b 1

:find_python
set "PYTHON_CMD="
py -3 --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=py -3"
    exit /b 0
)

python --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=python"
    exit /b 0
)

if exist "%LocalAppData%\Programs\Python\Python312\python.exe" (
    set "PYTHON_CMD="%LocalAppData%\Programs\Python\Python312\python.exe""
    exit /b 0
)

exit /b 1

:install_python
echo Python was not found. Installing Python automatically...

echo Trying winget...
winget --version >nul 2>&1
if not errorlevel 1 (
    winget install --id Python.Python.3.12 --exact --silent --accept-package-agreements --accept-source-agreements
    call :find_python
    if not errorlevel 1 exit /b 0
)

echo Winget was unavailable or did not finish the install.
echo Downloading Python directly...
powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%PYTHON_INSTALLER_URL%' -OutFile '%PYTHON_INSTALLER%'"
if errorlevel 1 exit /b 1

start /wait "" "%PYTHON_INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 Include_launcher=1 Include_pip=1
if errorlevel 1 exit /b 1

exit /b 0
