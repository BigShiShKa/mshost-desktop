; SPDX-FileCopyrightText: 2026 MSHost contributors
; SPDX-License-Identifier: GPL-2.0-or-later
Unicode true
!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "x64.nsh"
!include "WinVer.nsh"
!include "package-config.nsh"
Name "MSHost-Cloud ${PACKAGE_VERSION}"
OutFile "${OUTPUT_FILE}"
InstallDir "$LOCALAPPDATA\Programs\MSHost-Cloud"
InstallDirRegKey HKCU "Software\MSHost\MSHost-Cloud" "InstallDir"
RequestExecutionLevel user
SetCompressor /SOLID lzma
SetCompressorDictSize 32
ShowInstDetails show
ShowUninstDetails show
VIProductVersion "${NUMERIC_VERSION}"
VIAddVersionKey /LANG=1033 "ProductName" "MSHost-Cloud"
VIAddVersionKey /LANG=1033 "CompanyName" "MSHost"
VIAddVersionKey /LANG=1033 "FileDescription" "MSHost-Cloud Desktop Setup"
VIAddVersionKey /LANG=1033 "FileVersion" "${NUMERIC_VERSION}"
VIAddVersionKey /LANG=1033 "ProductVersion" "${PACKAGE_VERSION}"
VIAddVersionKey /LANG=1033 "LegalCopyright" "MSHost contributors; GPL-2.0-or-later"
!define MUI_ICON "${APP_ICON}"
!define MUI_UNICON "${APP_ICON}"
!define MUI_HEADERIMAGE
!define MUI_HEADERIMAGE_RIGHT
!define MUI_HEADERIMAGE_BITMAP "${ASSET_DIR}\header.bmp"
!define MUI_WELCOMEFINISHPAGE_BITMAP "${ASSET_DIR}\welcome.bmp"
!define MUI_ABORTWARNING
!define MUI_FINISHPAGE_RUN "$INSTDIR\mshost-cloud.exe"
!define MUI_FINISHPAGE_RUN_NOTCHECKED
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "${PAYLOAD_DIR}\LICENSE.txt"
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH
!insertmacro MUI_LANGUAGE "Russian"
!insertmacro MUI_LANGUAGE "English"
LangString DesktopShortcut ${LANG_ENGLISH} "Desktop shortcut"
LangString DesktopShortcut ${LANG_RUSSIAN} "Ярлык на рабочем столе"
LangString Require64 ${LANG_ENGLISH} "MSHost-Cloud requires 64-bit Windows."
LangString Require64 ${LANG_RUSSIAN} "Для MSHost-Cloud требуется 64-разрядная Windows."
LangString Require10 ${LANG_ENGLISH} "MSHost-Cloud requires Windows 10 or later."
LangString Require10 ${LANG_RUSSIAN} "Для MSHost-Cloud требуется Windows 10 или новее."
LangString ChooseEmpty ${LANG_ENGLISH} "Choose an empty folder or an existing MSHost-Cloud installation."
LangString ChooseEmpty ${LANG_RUSSIAN} "Выберите пустую папку или папку установленного MSHost-Cloud."
LangString CloseClient ${LANG_ENGLISH} "Close MSHost-Cloud before continuing."
LangString CloseClient ${LANG_RUSSIAN} "Закройте MSHost-Cloud, чтобы продолжить."
LangString NotOwned ${LANG_ENGLISH} "This folder is not a registered MSHost-Cloud installation."
LangString NotOwned ${LANG_RUSSIAN} "Эта папка не содержит установленный MSHost-Cloud."

Function .onInit
    SetShellVarContext current
    SetRegView 64
    ${IfNot} ${RunningX64}
        MessageBox MB_ICONSTOP "$(Require64)"
        Abort
    ${EndIf}
    ${IfNot} ${AtLeastWin10}
        MessageBox MB_ICONSTOP "$(Require10)"
        Abort
    ${EndIf}
FunctionEnd

Function ValidateInstallDirectory
    IfFileExists "$INSTDIR\.mshost-cloud-owned" owned check_empty
    owned:
        FileOpen $0 "$INSTDIR\.mshost-cloud-owned" r
        FileRead $0 $1 36
        FileClose $0
        StrCmp $1 "${PRODUCT_ID}" valid reject
    check_empty:
        ClearErrors
        FindFirst $0 $1 "$INSTDIR\*"
        IfErrors valid
    next_entry:
        StrCmp $1 "." continue_search
        StrCmp $1 ".." continue_search
        StrCmp $1 "" empty_found reject_open
    continue_search:
        FindNext $0 $1
        IfErrors empty_found next_entry
    empty_found:
        FindClose $0
        Goto valid
    reject_open:
        FindClose $0
    reject:
        MessageBox MB_ICONSTOP "$(ChooseEmpty)"
        SetErrorLevel 2
        Abort
    valid:
FunctionEnd

!macro DefineClientLockCheck PREFIX
Function ${PREFIX}EnsureClientClosed
    IfFileExists "$INSTDIR\mshost-cloud.exe" 0 done
    retry:
        System::Call 'kernel32::CreateFileW(w "$INSTDIR\mshost-cloud.exe", i 0x40000000, i 0, p 0, i 3, i 0, p 0) p .r0'
        ${If} $0 == -1
            MessageBox MB_RETRYCANCEL|MB_ICONEXCLAMATION "$(CloseClient)" IDRETRY retry
            SetErrorLevel 2
            Abort
        ${EndIf}
        System::Call 'kernel32::CloseHandle(p r0)'
    done:
FunctionEnd
!macroend
!insertmacro DefineClientLockCheck ""
!insertmacro DefineClientLockCheck "un."

Section "MSHost-Cloud" MainSection
    SectionIn RO
    Call ValidateInstallDirectory
    Call EnsureClientClosed
    SetOutPath "$INSTDIR"
    File /r "${PAYLOAD_DIR}\*"
    WriteUninstaller "$INSTDIR\Uninstall.exe"
    WriteRegStr HKCU "Software\MSHost\MSHost-Cloud" "InstallDir" "$INSTDIR"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\MSHost-Cloud" "DisplayName" "MSHost-Cloud"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\MSHost-Cloud" "DisplayVersion" "${PACKAGE_VERSION}"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\MSHost-Cloud" "Publisher" "MSHost"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\MSHost-Cloud" "InstallLocation" "$INSTDIR"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\MSHost-Cloud" "DisplayIcon" "$INSTDIR\mshost-cloud.exe,0"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\MSHost-Cloud" "UninstallString" '"$INSTDIR\Uninstall.exe"'
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\MSHost-Cloud" "QuietUninstallString" '"$INSTDIR\Uninstall.exe" /S'
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\MSHost-Cloud" "URLInfoAbout" "https://github.com/BigShiShKa/mshost-desktop"
    WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\MSHost-Cloud" "NoModify" 1
    WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\MSHost-Cloud" "NoRepair" 1
    WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\MSHost-Cloud" "EstimatedSize" ${INSTALLED_SIZE_KB}
    CreateDirectory "$SMPROGRAMS\MSHost-Cloud"
    CreateShortcut "$SMPROGRAMS\MSHost-Cloud\MSHost-Cloud.lnk" "$INSTDIR\mshost-cloud.exe"
    CreateShortcut "$SMPROGRAMS\MSHost-Cloud\Uninstall.lnk" "$INSTDIR\Uninstall.exe"
SectionEnd

Section "$(DesktopShortcut)"
    CreateShortcut "$DESKTOP\MSHost-Cloud.lnk" "$INSTDIR\mshost-cloud.exe"
SectionEnd

Function un.onInit
    SetShellVarContext current
    SetRegView 64
    IfFileExists "$INSTDIR\.mshost-cloud-owned" 0 invalid
    FileOpen $0 "$INSTDIR\.mshost-cloud-owned" r
    FileRead $0 $1 36
    FileClose $0
    StrCmp $1 "${PRODUCT_ID}" valid invalid
    invalid:
        MessageBox MB_ICONSTOP "$(NotOwned)"
        SetErrorLevel 2
        Abort
    valid:
FunctionEnd

Section "Uninstall"
    Call un.EnsureClientClosed
    !include "payload-uninstall.nsh"
    Delete "$DESKTOP\MSHost-Cloud.lnk"
    Delete "$SMPROGRAMS\MSHost-Cloud\MSHost-Cloud.lnk"
    Delete "$SMPROGRAMS\MSHost-Cloud\Uninstall.lnk"
    RMDir "$SMPROGRAMS\MSHost-Cloud"
    DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\MSHost-Cloud"
    DeleteRegValue HKCU "Software\MSHost\MSHost-Cloud" "InstallDir"
    DeleteRegKey /ifempty HKCU "Software\MSHost\MSHost-Cloud"
    ReadRegStr $0 HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "MSHost-Cloud"
    StrCmp $0 '"$INSTDIR\mshost-cloud.exe" --background' remove_autostart
    StrCmp $0 '"$INSTDIR\mshost-cloud.exe"' remove_autostart skip_autostart
    remove_autostart:
        DeleteRegValue HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "MSHost-Cloud"
    skip_autostart:
    Delete "$INSTDIR\Uninstall.exe"
    RMDir "$INSTDIR"
SectionEnd
