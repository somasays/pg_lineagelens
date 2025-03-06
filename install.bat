@echo off
REM PostgreSQL Data Lineage Tool - Windows Installer Script (Pipenv version)

echo PostgreSQL Data Lineage Tool - Installation
echo ===========================================
echo.

REM Check for Python installation
python --version > nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Python is not installed or not in PATH.
    echo Please install Python 3.8 or newer and try again.
    echo You can download Python from https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Check for Pipenv
pipenv --version > nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Pipenv is not installed. Installing Pipenv...
    pip install pipenv
    if %ERRORLEVEL% NEQ 0 (
        echo Failed to install Pipenv.
        pause
        exit /b 1
    )
)

REM Install dependencies with Pipenv
echo Installing dependencies with Pipenv...
pipenv install
if %ERRORLEVEL% NEQ 0 (
    echo Failed to install dependencies.
    pause
    exit /b 1
)

REM Create desktop shortcut
echo Creating desktop shortcut...
set SCRIPT_DIR=%~dp0
set SHORTCUT_PATH=%USERPROFILE%\Desktop\PostgreSQL Data Lineage.lnk
powershell "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%SHORTCUT_PATH%'); $s.TargetPath = 'cmd.exe'; $s.Arguments = '/c cd /d %SCRIPT_DIR% && pipenv run start'; $s.IconLocation = '%SCRIPT_DIR%packaging\windows\pg_lineage.ico'; $s.WorkingDirectory = '%SCRIPT_DIR%'; $s.Save()"

echo.
echo Installation completed successfully!
echo You can now run the application from the desktop shortcut.
echo.
echo Alternatively, run the application with:
echo   pipenv run start
echo.

pause