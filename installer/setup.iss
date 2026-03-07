; MirAI_OS Inno Setup Installer Script
; Targets D:\MirAI_OS by default

[Setup]
AppName=MirAI OS
AppVersion=1.0
AppPublisher=MirAI_OS Project
AppPublisherURL=https://github.com/andreygorban1582-dev/MirAI_OS
DefaultDirName=D:\MirAI_OS
DefaultGroupName=MirAI OS
OutputBaseFilename=MirAI_OS_Setup
Compression=lzma
SolidCompression=yes
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\MirAI_OS.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\MirAI OS"; Filename: "{app}\MirAI_OS.exe"
Name: "{group}\Uninstall MirAI OS"; Filename: "{uninstallexe}"
Name: "{commondesktop}\MirAI OS"; Filename: "{app}\MirAI_OS.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\MirAI_OS.exe"; Description: "{cm:LaunchProgram,MirAI OS}"; Flags: nowait postinstall skipifsilent
