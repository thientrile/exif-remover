; Inno Setup script. Build: iscc /DAppVersion=0.1.0 installer.iss (after PyInstaller made dist\ExifRemover)
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{D9BBF5CF-7048-4CE3-9E04-B8D59A5EDA2E}
AppName=Exif Remover
AppVersion={#AppVersion}
AppPublisher=thientrile
AppPublisherURL=https://github.com/thientrile/exif-remover
DefaultDirName={autopf}\Exif Remover
DefaultGroupName=Exif Remover
DisableProgramGroupPage=yes
; Per-user install into %LOCALAPPDATA%\Programs, no admin prompt.
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=dist
OutputBaseFilename=ExifRemover-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\ExifRemover.exe

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; Flags: unchecked

[Files]
Source: "dist\ExifRemover\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "THIRD_PARTY_NOTICES.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\Exif Remover"; Filename: "{app}\ExifRemover.exe"
Name: "{autodesktop}\Exif Remover"; Filename: "{app}\ExifRemover.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\ExifRemover.exe"; Description: "{cm:LaunchProgram,Exif Remover}"; Flags: nowait postinstall skipifsilent
