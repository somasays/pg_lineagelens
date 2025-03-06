@echo off
REM PostgreSQL Data Lineage Tool - Windows Installer Build Script

echo Building Windows installer...

REM Check for NSIS
where makensis > nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo NSIS is not installed or not in PATH.
    echo Please install NSIS and try again.
    echo You can download NSIS from https://nsis.sourceforge.io/Download
    exit /b 1
)

REM Build the installer
makensis packaging\windows\installer.nsi

echo Done! Installer created: pg_lineage_setup.exe