; Inno Setup Script for MonitorAgent
; Save this as MonitorAgent_Setup.iss in the 'client' directory

; --- Application Definitions ---
#define MyAppName "Monitor Agent"
#define MyAppVersion "1.0"
#define MyAppPublisher "nani-solutions"  ; Publisher updated
#define MyAppExeName "MonitorAgent.exe"
#define MyAppLogSubdir "MonitorAgent\Logs" ; Subdirectory under ProgramData for logs

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
; ** Using a unique generated GUID **
AppId={{A7E8C5D2-9F1B-4A9C-8D3E-0F7B1A2C3D4E}} ; <-- UNIQUE GUID INSERTED

AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
; Default installation directory in Program Files (auto-detects x64 or x86)
DefaultDirName={autopf}\{#MyAppName}
; Default Start Menu group name
DefaultGroupName={#MyAppName}
; Allow user to choose not to create Start Menu icons (uninstaller link is still created)
AllowNoIcons=yes
; Installer requires administrator privileges to run
PrivilegesRequired=admin
; Specifies the directory where the final installer EXE will be saved
OutputDir=.\InstallerOutput
; Base name for the installer executable
OutputBaseFilename=MonitorAgent_Setup_v{#MyAppVersion}
; Use good compression
Compression=lzma
SolidCompression=yes
; Use a modern wizard interface
WizardStyle=modern
; Optional: Specify an icon for Add/Remove Programs entry
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
; Defines optional tasks the user can select during installation
; Task to control registry key creation for startup
Name: "startup"; Description: "Run Monitor Agent automatically on Windows startup"; GroupDescription: "Startup Options:"; Flags: checkedonce

[Files]
; Specifies the files to be installed
; Copy your built EXE from the PyInstaller dist folder to the installation directory ({app})
; *** Path updated based on previous build logs ***
Source: "C:\Users\Administrator\Desktop\employee-monitoring-software\client\dist\MonitorAgent.exe"; DestDir: "{app}"; Flags: ignoreversion  ; <-- Path updated

; Note: If you have other required files (e.g., config.ini, other DLLs), add them here too:
; Source: "C:\path\to\your\otherfile.dll"; DestDir: "{app}"

[Dirs]
; Specifies directories to be created during installation
; Create the log directory under C:\ProgramData\MonitorAgent\Logs
; This uses the {commonappdata} constant (usually C:\ProgramData)
; Permissions: grant Authenticated Users modify rights so the agent process (even if run as standard user later) can write logs
Name: "{commonappdata}\{#MyAppLogSubdir}"; Permissions: authusers-modify

[Icons]
; Optional: Create Start Menu icons (comment out the first line if not needed)
; Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"

; Mandatory: Creates the Uninstaller entry in the Start Menu group
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"

[Registry]
; Writes registry keys during installation
; Add to Run key for auto-start IF the 'startup' task is checked during install
; Using HKLM (HKEY_LOCAL_MACHINE) requires admin rights (which the installer requests)
; This ensures the agent attempts to run for any user logging into the machine
Root: HKLM; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "{#MyAppName}"; ValueData: """{app}\{#MyAppExeName}"""; Tasks: startup

[Run]
; Commands to execute after the installation finishes
; Optional: Run the agent immediately after installation completes
; Flags: nowait - don't wait for the process to exit
;        postinstall - run after files are copied
;        skipifsilent - don't run if installing silently
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Specifies files and directories to be deleted during uninstallation
; Removes the main application installation directory and all its contents
Type: filesandordirs; Name: "{app}"
; Removes the log directory created under ProgramData
Type: filesandordirs; Name: "{commonappdata}\{#MyAppLogSubdir}"

[UninstallRegistry]
; Removes registry keys during uninstallation
; Remove the Run key entry (only if it was created by the 'startup' task)
Root: HKLM; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueName: "{#MyAppName}"; Tasks: startup