; UberTrack by Delta — Instalador
; Delta Silk Print

#define MyAppName "UberTrack"
#define MyAppVersion "3.2.0"
#define MyAppPublisher "Delta Silk Print"
#define MyAppExeName "UberTrack.exe"

[Setup]
AppId={{E7A3D0F1-8B2C-4A5E-9D6F-1C3B7E8A2D4F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=installer_output
OutputBaseFilename=UberTrack_Setup
SetupIconFile=icon.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Files]
Source: "dist\UberTrack\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir UberTrack agora"; Flags: nowait postinstall skipifsilent
