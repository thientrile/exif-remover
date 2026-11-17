; Inno Setup script (UTF-8 with BOM: the publisher name has Vietnamese letters). Build: iscc /DAppVersion=0.1.0 installer.iss (after PyInstaller made dist\ExifRemover)
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{D9BBF5CF-7048-4CE3-9E04-B8D59A5EDA2E}
AppName=Exif Remover
AppVersion={#AppVersion}
AppPublisher=Ánh sao & Bầu trời (thientrile)
AppPublisherURL=https://github.com/thientrile
AppSupportURL=https://github.com/thientrile/exif-remover/issues
AppCopyright=© 2026 thientrile
LicenseFile=LICENSE
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
SetupIconFile=assets\icon.ico
; The app passes /CLOSEAPPLICATIONS when self-updating; close it if still running.
CloseApplications=yes

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
; Self-update runs the installer silently with /RELAUNCH: start the new version when done.
Filename: "{app}\ExifRemover.exe"; Flags: nowait; Check: Relaunch

[Code]
function Relaunch: Boolean;
var
  i: Integer;
begin
  Result := False;
  for i := 1 to ParamCount do
    if CompareText(ParamStr(i), '/RELAUNCH') = 0 then
      Result := True;
end;
