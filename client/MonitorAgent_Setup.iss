; Inno Setup Script for MonitorAgent
; Save this as MonitorAgent_Setup.iss in the 'client' directory

; --- Application Definitions ---
#define MyAppName "Monitor Agent"
#define MyAppVersion "1.0"
#define MyAppPublisher "nani-solutions"  ; Publisher updated
#define MyAppExeName "MonitorAgent.exe"
#define MyAppLogSubdir "MonitorAgent\Logs" ; Subdirectory under ProgramData for logs
#define MyAppConfigFileName "monitor_config.ini" ; Config file name

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
; ** Using a unique generated GUID **
AppId={{A7E8C5D2-9F1B-4A9C-8D3E-0F7B1A2C3D4E}} ; Unique GUID inserted

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
; The following Source path points to the EXE built by PyInstaller
Source: "C:\Users\Administrator\Desktop\employee-monitoring-software\client\dist\MonitorAgent.exe"; DestDir: "{app}"; Flags: ignoreversion

; Note: If you have other required files (e.g., config.ini, other DLLs), add them here too:
; Source: "C:\path\to\your\otherfile.dll"; DestDir: "{app}"

[Dirs]
; Specifies directories to be created during installation
; Create log directory under ProgramData
Name: "{commonappdata}\{#MyAppLogSubdir}"; Permissions: authusers-modify

; Create base config directory under ProgramData (e.g., C:\ProgramData\MonitorAgent)
; This directory will hold the monitor_config.ini file
Name: "{commonappdata}\{#MyAppName}"; Permissions: authusers-modify

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
; Removes the base config/log directory created under ProgramData
Type: filesandordirs; Name: "{commonappdata}\{#MyAppName}"

[UninstallRegistry]
; Removes registry keys during uninstallation
; Remove the Run key entry (only if it was created by the 'startup' task)
Root: HKLM; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueName: "{#MyAppName}"; Tasks: startup

; ======================================================================
; Custom Code Section for Employee ID and Name Input
; ======================================================================
[Code]
var
  EmployeeInfoPage: TInputQueryWizardPage;
  EmployeeID, EmployeeName: string;

// Function called when the wizard initializes
procedure InitializeWizard;
begin
  // Create a new page after the 'Select Destination Location' page
  EmployeeInfoPage := CreateInputQueryPage(wpSelectDir,
    'Employee Information', 'Please provide employee details',
    'Enter the unique Employee ID and Name for this installation.');

  // Add input fields to the page
  EmployeeInfoPage.Add('Employee ID:', False); // Field index 0, not password
  EmployeeInfoPage.Add('Employee Name:', False); // Field index 1, not password

  // Optional: Set initial values if needed (e.g., from a previous install)
  // EmployeeInfoPage.Values[0] := 'EMP';
  // EmployeeInfoPage.Values[1] := '';
end;

// Function called when the user clicks Next on any page
// We use it to validate the input on our custom page
function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True; // Assume validation passes unless proven otherwise
  if CurPageID = EmployeeInfoPage.ID then begin
    EmployeeID := Trim(EmployeeInfoPage.Values[0]);
    EmployeeName := Trim(EmployeeInfoPage.Values[1]);
    if EmployeeID = '' then begin
      MsgBox('Please enter an Employee ID.', mbError, MB_OK);
      Result := False; // Prevent moving to the next page
    end else
    if EmployeeName = '' then begin
       MsgBox('Please enter an Employee Name.', mbError, MB_OK);
       Result := False; // Prevent moving to the next page
    end;
    // Optional: Add more validation for EmployeeID format if needed
  end;
end;

// Function called after files are copied (part of the Install step)
// This is where we write the config file
procedure CurStepChanged(CurStep: TSetupStep);
var
  ConfigPath: string;
  ConfigLines: TStringList;
begin
  // Only run this code after the main installation step completes
  // (ssPostInstall runs after the [Run] section, ssInstall runs before [Run])
  // Let's use ssInstall to ensure config is written before optional [Run] execution
  if CurStep = ssInstall then begin
    // Re-capture values directly from the page just before writing
    // Ensures we have the latest input if the user went back and forth
    EmployeeID := Trim(EmployeeInfoPage.Values[0]);
    EmployeeName := Trim(EmployeeInfoPage.Values[1]);

    // Construct the path to the config file: C:\ProgramData\MonitorAgent\monitor_config.ini
    ConfigPath := ExpandConstant('{commonappdata}\{#MyAppName}\{#MyAppConfigFileName}');
    Log(Format('Writing configuration to: %s', [ConfigPath]));

    ConfigLines := TStringList.Create;
    try
      // Make sure base directory exists (created in [Dirs])
      ForceDirectories(ExtractFilePath(ConfigPath));

      ConfigLines.Add('[Agent]');
      ConfigLines.Add(Format('EmployeeID = %s', [EmployeeID]));
      ConfigLines.Add(Format('EmployeeName = %s', [EmployeeName]));
      // Add other config options here if needed in the future
      // ConfigLines.Add('ServerURL = http://...'); // Could potentially set this here too

      if SaveStringsToFile(ConfigPath, ConfigLines, False) then begin
        Log('Successfully wrote config file.');
      end else begin
        // Show error but allow install to continue; agent might fail later
        MsgBox('Warning: Failed to write configuration file to ' + ConfigPath + '.'#13#10 + 'The agent may not function correctly.', mbWarning, MB_OK);
        Log('ERROR: Failed to write config file.');
      end;
    finally
      ConfigLines.Free;
    end;
  end;
end;