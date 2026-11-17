; Inno Setup script (UTF-8 with BOM: the publisher name has Vietnamese letters). Build: iscc /DAppVersion=0.1.0 installer.iss (after PyInstaller made dist\StarVeil)
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{D9BBF5CF-7048-4CE3-9E04-B8D59A5EDA2E}
; AppId stays the Exif Remover one so v0.2.x installs upgrade in place (same folder, same uninstall entry).
AppName=Tinh Ảnh (StarVeil)
AppVersion={#AppVersion}
AppPublisher=Ánh sao & Bầu trời (thientrile)
AppPublisherURL=https://github.com/thientrile
AppSupportURL=https://thientrile.github.io/exif-remover/SUPPORT.html
AppCopyright=© 2026 thientrile
LicenseFile=LICENSE
DefaultDirName={autopf}\StarVeil
DefaultGroupName=Tinh Ảnh (StarVeil)
DisableProgramGroupPage=yes
; Per-user install into %LOCALAPPDATA%\Programs, no admin prompt.
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=dist
OutputBaseFilename=StarVeil-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\StarVeil.exe
SetupIconFile=assets\icon.ico
; The app passes /CLOSEAPPLICATIONS when self-updating; close it if still running.
CloseApplications=yes

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; Flags: unchecked

[Files]
Source: "dist\StarVeil\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "THIRD_PARTY_NOTICES.md"; DestDir: "{app}"; Flags: ignoreversion

[InstallDelete]
; Leftovers of the old name (v0.2.x) when upgrading in place.
Type: files; Name: "{app}\ExifRemover.exe"
Type: files; Name: "{autoprograms}\Exif Remover.lnk"
Type: files; Name: "{autodesktop}\Exif Remover.lnk"

[Icons]
Name: "{autoprograms}\Tinh Ảnh (StarVeil)"; Filename: "{app}\StarVeil.exe"
Name: "{autodesktop}\Tinh Ảnh (StarVeil)"; Filename: "{app}\StarVeil.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\StarVeil.exe"; Description: "{cm:LaunchProgram,Tinh Ảnh}"; Flags: nowait postinstall skipifsilent
; Self-update runs the installer silently with /RELAUNCH: start the new version when done.
Filename: "{app}\StarVeil.exe"; Flags: nowait; Check: Relaunch

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
