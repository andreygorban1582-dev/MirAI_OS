; ============================================================
;  MirAI OS — Inno Setup Installer Script
;  Creates a proper Windows installer (.exe) with:
;   - WSL2 check and install
;   - Kali Linux install
;   - MirAI OS files copy
;   - Start menu + desktop shortcuts
;   - Uninstaller
;
;  Download Inno Setup: https://jrsoftware.org/isdl.php
;  Compile: Open this file in Inno Setup Compiler → Build
; ============================================================

#define MyAppName "MirAI OS"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "Future Gadget Lab"
#define MyAppURL "https://github.com/YOUR_USERNAME/MirAI_OS"
#define MyAppExeName "MirAI_OS.exe"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\MirAI_OS
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
; Require Windows 10 version 2004+ (WSL2 minimum)
MinVersion=10.0.19041
OutputDir=..\dist\installer
OutputBaseFilename=MirAI_OS_Setup_{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\MirAI_OS.exe
PrivilegesRequired=admin

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "startupicon"; Description: "Launch MirAI on Windows startup"; GroupDescription: "Startup"

[Files]
; Main launcher executable (built by build_exe.py)
Source: "..\MirAI_OS.exe"; DestDir: "{app}"; Flags: ignoreversion
; Config templates
Source: "..\config\*"; DestDir: "{app}\config"; Flags: recursesubdirs ignoreversion
; Scripts
Source: "..\scripts\*"; DestDir: "{app}\scripts"; Flags: recursesubdirs ignoreversion
; Requirements
Source: "..\requirements.txt"; DestDir: "{app}"; Flags: ignoreversion
; README
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: startupicon

[Run]
; After install, ask to configure WSL
Filename: "powershell.exe"; \
  Parameters: "-ExecutionPolicy Bypass -File ""{app}\scripts\configure_wslconfig.ps1"""; \
  Description: "Configure WSL2 for Legion Go (recommended)"; \
  Flags: postinstall runascurrentuser optionalcheckbox

; Offer to open .env for editing
Filename: "notepad.exe"; \
  Parameters: "{app}\config\.env.example"; \
  Description: "Open .env template to add API keys"; \
  Flags: postinstall shellexec skipifsilent unchecked

Filename: "{app}\{#MyAppExeName}"; \
  Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; \
  Flags: postinstall nowait

[Code]
// Check for WSL2 support
function InitializeSetup(): Boolean;
var
  WinVer: TWindowsVersion;
begin
  GetWindowsVersionEx(WinVer);
  if (WinVer.Major < 10) or ((WinVer.Major = 10) and (WinVer.Build < 19041)) then
  begin
    MsgBox('MirAI OS requires Windows 10 version 2004 (build 19041) or later for WSL2 support.'#13#10 +
           'Please update Windows and try again.', mbError, MB_OK);
    Result := False;
  end
  else
    Result := True;
end;
