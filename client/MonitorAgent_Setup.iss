; Inno Setup Script for MonitorAgent
; Save this as MonitorAgent_Setup.iss in the 'client' directory

#define MyAppName "Monitor Agent"
#define MyAppVersion "1.0"
#define MyAppPublisher "nani-solutions"  ; <-- REPLACE THIS
#define MyAppExeName "MonitorAgent.exe"
#define MyAppLogSubdir "MonitorAgent\Logs" ; Subdirectory under ProgramData

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
; ** Generate a new GUID and replace the placeholder below **
; Example: AppId={{12345678-ABCD-1234-ABCD-1234567890AB}}
AppId={{12345678-ABCD-1234-ABCD-1234567890AB}} ; <-- REPLACE THIS with a real GUID
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}  ; Installs to Program Files (x64 or x86)
DefaultGroupName={#MyAppName}
AllowNoIcons=yes ; Don't require Start Menu icons if not wanted
PrivilegesRequired=admin ; Requires admin rights to install
OutputDir=.\InstallerOutput  ; Where the final setup.exe will be created
OutputBaseFilename=MonitorAgent_Setup_v{#MyAppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName} ; Icon for Add/Remove Programs (optional)

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
; Task to control registry key creation for startup
Name: "startup"; Description: "Run Monitor Agent automatically on Windows startup"; GroupDescription: "Startup Options:"; Flags: checkedonce

[Files]
; Copy your built EXE to the installation directory ({app})
; *** IMPORTANT: Update the Source path below to your actual built EXE location ***
Source: "C:\Users\Administrator\Desktop\employee-monitoring-software\client\dist\MonitorAgent.exe"; DestDir: "{app}"; Flags: ignoreversion  ; <-- REPLACE SOURCE PATH
; Note: If you have other required files (e.g., config.ini), add them here too.

[Dirs]
; Create the log directory under C:\ProgramData\MonitorAgent\Logs
; Grant Authenticated Users modify rights so the agent can write logs
Name: "{commonappdata}\{#MyAppLogSubdir}"; Permissions: authusers-modify

[Icons]
; Optional: Create Start Menu icons (comment out if not needed)
; Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"

; Mandatory: Uninstaller entry in Start Menu
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"

[Registry]
; Add to Run key for auto-start IF the 'startup' task is checked during install
; Using HKLM requires admin rights (which the installer already requests)
; Ensures it runs for any user logging in
Root: HKLM; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "{#MyAppName}"; ValueData: """{app}\{#MyAppExeName}"""; Tasks: startup

[Run]
; Run the agent immediately after installation (optional, remove if not desired)
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Files/Dirs to delete during uninstall
Type: filesandordirs; Name: "{app}" ; Removes the installation directory
Type: filesandordirs; Name: "{commonappdata}\{#MyAppLogSubdir}" ; Removes the log directory

[UninstallRegistry]
; Remove the Run key during uninstall (only if it was added by the startup task)
Root: HKLM; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueName: "{#MyAppName}"; Tasks: startup