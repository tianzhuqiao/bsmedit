;NSIS script for BSMEdit installer
;Written by Tianzhu Qiao

;--------------------------------
;Include Modern UI

  !include "MUI2.nsh"

;--------------------------------
;General

  !define VERSION "3.0.1"
  !define MAINAPP "bsmedit"
  ;Name and file
  Name "SystemC Simulation Module Edit ${VERSION}"
  OutFile "release\${MAINAPP}_install_${VERSION}.exe"

  ;Default installation folder
  InstallDir "$PROGRAMFILES\${MAINAPP}"
  
  ;Get installation folder from registry if available
  InstallDirRegKey HKCU "Software\${MAINAPP}" ""

  ;Request application privileges for Windows Vista
  RequestExecutionLevel admin

;--------------------------------
;Page header
  !define MUI_ICON "${NSISDIR}\Contrib\Graphics\Icons\orange-install.ico"
  !define MUI_UNICON  "${NSISDIR}\Contrib\Graphics\Icons\orange-uninstall.ico"
  !define MUI_HEADERIMAGE_BITMAP   "${NSISDIR}\Contrib\Graphics\Header\orange.bmp"
  !define MUI_HEADERIMAGE_UNBITMAP   "${NSISDIR}\Contrib\Graphics\Header\orange-uninstall.bmp"
  !define MUI_WELCOMEFINISHPAGE_BITMAP    "${NSISDIR}\Contrib\Graphics\Wizard\orange.bmp"
  !define MUI_UNWELCOMEFINISHPAGE_BITMAP    "${NSISDIR}\Contrib\Graphics\Wizard\orange.bmp"
;--------------------------------
;Interface Settings

  !define MUI_ABORTWARNING

;--------------------------------
;Variables

  Var StartMenuFolder
;--------------------------------

;Pages
  !insertmacro MUI_PAGE_WELCOME
  !insertmacro MUI_PAGE_LICENSE ".\License";"${NSISDIR}\Docs\Modern UI\License.txt"
  !insertmacro MUI_PAGE_COMPONENTS
  !insertmacro MUI_PAGE_DIRECTORY

  ;Start Menu Folder Page Configuration
  !define  MUI_STARTMENUPAGE_DEFAULTFOLDER ${MAINAPP}
  !define MUI_STARTMENUPAGE_REGISTRY_ROOT "HKCU" 
  !define MUI_STARTMENUPAGE_REGISTRY_KEY "Software\${MAINAPP}" 
  !define MUI_STARTMENUPAGE_REGISTRY_VALUENAME "Start Menu Folder"
  !insertmacro MUI_PAGE_STARTMENU Application $StartMenuFolder

  !insertmacro MUI_PAGE_INSTFILES
  !insertmacro MUI_PAGE_FINISH 

  !insertmacro MUI_UNPAGE_WELCOME
  !insertmacro MUI_UNPAGE_CONFIRM
  !insertmacro MUI_UNPAGE_INSTFILES
  !insertmacro MUI_UNPAGE_FINISH
;--------------------------------
;Languages
 
  !insertmacro MUI_LANGUAGE "English"

;--------------------------------
InstType "Full"
InstType "Minimal"

;Installer Sections

Section "${MAINAPP}" SecMain
SectionIn 1 2 RO
  SetOutPath "$INSTDIR"
  
  ;ADD YOUR OWN FILES HERE...
  File .\${MAINAPP}.py
  File /r .\bsm
  File /r .\main
  File /r .\examples
  File /r .\systemc-2.1
  File /r .\xsc
  File /r .\libs
  File .\License
  File .\readme.txt
  ;FILE /r .\xsc
  ;Store installation folder
  WriteRegStr HKCU "Software\${MAINAPP}" "" $INSTDIR
  
  ;Create uninstaller
  WriteUninstaller "$INSTDIR\Uninstall.exe"

  !insertmacro MUI_STARTMENU_WRITE_BEGIN Application
    
    ;Create shortcuts
    CreateDirectory "$SMPROGRAMS\$StartMenuFolder"

    CreateShortCut "$SMPROGRAMS\$StartMenuFolder\${MAINAPP}.lnk" "$INSTDIR\${MAINAPP}.py"
    CreateShortCut "$SMPROGRAMS\$StartMenuFolder\Uninstall.lnk" "$INSTDIR\Uninstall.exe"
  
  !insertmacro MUI_STARTMENU_WRITE_END

SectionEnd
;Section "SystemC Library" SecSystemCLib
;SectionIn 1
;  SetOutPath "$INSTDIR"
;  
;  ;ADD YOUR OWN FILES HERE...
;  File /r .\include
;  File /r .\lib
;  
;  ;Store installation folder
;  
;
;SectionEnd

Section "Example project" SecExampleProj
SectionIn 1
  SetOutPath "$INSTDIR"
  
  ;ADD YOUR OWN FILES HERE...
  File /r .\examples
  
  ;Store installation folder

SectionEnd

;--------------------------------
;Descriptions

  ;Language strings
  LangString DESC_SecMain        ${LANG_ENGLISH} "${MAINAPP} main program."
  ;LangString DESC_SecSystemCLib  ${LANG_ENGLISH} "SystemC Library needed to build your own simulation program."
  LangString DESC_SecExampleProj ${LANG_ENGLISH} "Example project to show how to build the simulation."

  ;Assign language strings to sections
    !insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
    !insertmacro MUI_DESCRIPTION_TEXT ${SecMain}        $(DESC_SecMain)
    ;!insertmacro MUI_DESCRIPTION_TEXT ${SecSystemCLib}  $(DESC_SecSystemCLib)
    !insertmacro MUI_DESCRIPTION_TEXT ${SecExampleProj} $(DESC_SecExampleProj)
  !insertmacro MUI_FUNCTION_DESCRIPTION_END

;--------------------------------
;Uninstaller Section

Section "Uninstall"

  ;ADD YOUR OWN FILES HERE...
  ;main
  Delete   $INSTDIR\${MAINAPP}.py
  RMDIR  /r $INSTDIR\bsm
  RMDIR  /r $INSTDIR\main
  Delete   $INSTDIR\License
  DELETE   $INSTDIR\readme.txt
 ;RMDIR /r $INSTDIR\xsc
  
  ;systemc library
  ;RMDIR /r $INSTDIR\include
  ;RMDIR /r $INSTDIR\lib
  ;example
  RMDIR /r $INSTDIR\examples
  
  ;application data
  ;RMDIR /r $APPDATA\bsmedit

  ;uninstall
  Delete $INSTDIR\Uninstall.exe
  RMDir  $INSTDIR

  !insertmacro MUI_STARTMENU_GETFOLDER Application $StartMenuFolder
  Delete "$SMPROGRAMS\$StartMenuFolder\${MAINAPP}.lnk"
  Delete "$SMPROGRAMS\$StartMenuFolder\Uninstall.lnk"
  RMDir $SMPROGRAMS\$StartMenuFolder

  DeleteRegKey /ifempty HKCU "Software\${MAINAPP}"

SectionEnd
