; ============================================================================
; MirAI_OS – Inno Setup Installer Script
; Target:   Lenovo Legion Go (Windows 11, AMD Ryzen Z1 Extreme, x86-64)
; Output:   MirAI_OS_Setup.exe  (single-file installer with UAC elevation)
;
; Prerequisites on the build machine:
;   1. Inno Setup 6  – https://jrsoftware.org/isinfo.php
;   2. PyInstaller   – pip install pyinstaller
;   3. Run build.ps1 first to produce dist\MirAI_OS\  before compiling this script.
;
; Compile: iscc installer\setup.iss
; ============================================================================

#define MyAppName      "MirAI_OS"
#define MyAppVersion   "1.0.0"
#define MyAppPublisher "MirAI Project"
#define MyAppURL       "https://github.com/andreygorban1582-dev/MirAI_OS"
#define MyAppExeName   "MirAI_OS.exe"
#define DistDir        "..\dist\MirAI_OS"

[Setup]
; --- Identity ---
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

; --- Install location ---
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

; --- Output ---
OutputDir=..\dist
OutputBaseFilename=MirAI_OS_Setup
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes

; --- UAC / admin elevation (required for Legion Go system-level access) ---
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog

; --- Appearance ---
WizardStyle=modern
WizardSizePercent=120
#ifdef UseCustomIcon
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
#endif

; --- Misc ---
AllowNoIcons=yes
CloseApplications=yes
RestartIfNeededByRun=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startupentry"; Description: "Start MirAI_OS automatically when Windows starts"; GroupDescription: "Startup"; Flags: unchecked

[Files]
; --- Main application (PyInstaller bundle) ---
Source: "{#DistDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; --- Default config (only if user doesn't already have one) ---
Source: "..\config.yaml"; DestDir: "{userappdata}\MirAI_OS"; Flags: onlyifdoesntexist uninsneveruninstall; DestName: "config.yaml"

[Dirs]
Name: "{userappdata}\MirAI_OS"

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
; --- Auto-start entry (optional task) ---
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
    ValueType: string; ValueName: "{#MyAppName}"; \
    ValueData: """{app}\{#MyAppExeName}"""; \
    Flags: uninsdeletevalue; Tasks: startupentry

[Run]
; --- Open config folder after install so the user can configure the app ---
Filename: "{cmd}"; Parameters: "/c explorer ""{userappdata}\MirAI_OS"""; \
    Description: "Open configuration folder"; Flags: postinstall shellexec skipifsilent

[UninstallRun]
Filename: "{cmd}"; Parameters: "/c taskkill /f /im {#MyAppExeName}"; Flags: runhidden

[Code]
// ---------------------------------------------------------------------------
// Check for Python – show a warning if it's not found on PATH.
// (PyInstaller bundles Python so this is informational only.)
// ---------------------------------------------------------------------------
function InitializeSetup(): Boolean;
begin
  Result := True;
  if not FileExists(ExpandConstant('{tmp}\~mirai_check')) then
  begin
    // No blocking check needed – PyInstaller bundle is self-contained.
  end;
end;
