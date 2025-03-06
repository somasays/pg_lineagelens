; PostgreSQL Data Lineage Tool - NSIS Installer Script

!include "MUI2.nsh"
!include "LogicLib.nsh"

; Basic definitions
Name "PostgreSQL Data Lineage Tool"
OutFile "pg_lineage_setup.exe"
Unicode True
InstallDir "$PROGRAMFILES\PostgreSQL Data Lineage"
InstallDirRegKey HKCU "Software\PostgreSQL Data Lineage" ""
RequestExecutionLevel admin

; Interface settings
!define MUI_ABORTWARNING
!define MUI_ICON "packaging\windows\pg_lineage.ico"
!define MUI_UNICON "packaging\windows\pg_lineage.ico"
!define MUI_WELCOMEFINISHPAGE_BITMAP "packaging\windows\installer-sidebar.bmp"
!define MUI_HEADERIMAGE
!define MUI_HEADERIMAGE_BITMAP "packaging\windows\installer-header.bmp"
!define MUI_HEADERIMAGE_RIGHT

; Pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "LICENSE"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

; Languages
!insertmacro MUI_LANGUAGE "English"

; Check for Python
Function CheckPython
    nsExec::ExecToStack "python --version"
    Pop $0
    Pop $1
    ${If} $0 != 0
        MessageBox MB_YESNO|MB_ICONQUESTION "Python was not found on your system. The PostgreSQL Data Lineage Tool requires Python 3.8 or newer.$\n$\nWould you like to download Python now?" IDYES download IDNO done
        download:
            ExecShell "open" "https://www.python.org/downloads/"
        done:
    ${EndIf}
FunctionEnd

; Install the application
Section "Install"
    SetOutPath "$INSTDIR"
    
    ; Write files
    File /r "dist\pg_lineage\*.*"
    
    ; Create shortcuts
    CreateDirectory "$SMPROGRAMS\PostgreSQL Data Lineage"
    CreateShortcut "$SMPROGRAMS\PostgreSQL Data Lineage\PostgreSQL Data Lineage.lnk" "$INSTDIR\pg_lineage.exe" "" "$INSTDIR\pg_lineage.exe" 0
    CreateShortcut "$SMPROGRAMS\PostgreSQL Data Lineage\Uninstall.lnk" "$INSTDIR\uninstall.exe" "" "$INSTDIR\uninstall.exe" 0
    CreateShortcut "$DESKTOP\PostgreSQL Data Lineage.lnk" "$INSTDIR\pg_lineage.exe" "" "$INSTDIR\pg_lineage.exe" 0
    
    ; Write registry keys
    WriteRegStr HKCU "Software\PostgreSQL Data Lineage" "" $INSTDIR
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\PostgreSQLDataLineage" "DisplayName" "PostgreSQL Data Lineage Tool"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\PostgreSQLDataLineage" "UninstallString" "$\"$INSTDIR\uninstall.exe$\""
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\PostgreSQLDataLineage" "DisplayIcon" "$INSTDIR\pg_lineage.exe"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\PostgreSQLDataLineage" "Publisher" "PostgreSQL Data Lineage"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\PostgreSQLDataLineage" "DisplayVersion" "1.0.0"
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\PostgreSQLDataLineage" "NoModify" 1
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\PostgreSQLDataLineage" "NoRepair" 1
    
    ; Create uninstaller
    WriteUninstaller "$INSTDIR\uninstall.exe"
SectionEnd

; Uninstaller
Section "Uninstall"
    ; Remove shortcuts
    Delete "$SMPROGRAMS\PostgreSQL Data Lineage\PostgreSQL Data Lineage.lnk"
    Delete "$SMPROGRAMS\PostgreSQL Data Lineage\Uninstall.lnk"
    RMDir "$SMPROGRAMS\PostgreSQL Data Lineage"
    Delete "$DESKTOP\PostgreSQL Data Lineage.lnk"
    
    ; Remove files
    RMDir /r "$INSTDIR"
    
    ; Remove registry keys
    DeleteRegKey HKCU "Software\PostgreSQL Data Lineage"
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\PostgreSQLDataLineage"
SectionEnd

; On initialization, check for Python
Function .onInit
    Call CheckPython
FunctionEnd