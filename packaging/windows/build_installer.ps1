# PostgreSQL Data Lineage Tool - Windows Installer Build PowerShell Script

Write-Host "Building Windows installer..." -ForegroundColor Green

# Check for NSIS
try {
    $nsisPath = (Get-Command makensis -ErrorAction Stop).Path
    Write-Host "Found NSIS at: $nsisPath" -ForegroundColor Green
}
catch {
    Write-Host "NSIS is not installed or not in PATH." -ForegroundColor Red
    Write-Host "Please install NSIS and try again." -ForegroundColor Red
    Write-Host "You can download NSIS from https://nsis.sourceforge.io/Download" -ForegroundColor Yellow
    exit 1
}

# Build the installer
Write-Host "Running NSIS compiler..." -ForegroundColor Green
makensis packaging\windows\installer.nsi

# Check if the installer was created
if (Test-Path "pg_lineage_setup.exe") {
    Write-Host "Done! Installer created: pg_lineage_setup.exe" -ForegroundColor Green
}
else {
    Write-Host "Failed to create installer." -ForegroundColor Red
    exit 1
}

Write-Host "You can now distribute the pg_lineage_setup.exe installer." -ForegroundColor Green