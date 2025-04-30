; Inno Setup Script for MonitorAgent
; Save this as MonitorAgent_Setup.iss in the 'client' directory

; --- Application Definitions ---
#define MyAppName "Monitor Agent"
#define MyAppVersion "1.0"
#define MyAppPublisher "nani-solutions"
#define MyAppExeName "MonitorAgent.exe"
#define MyAppLogSubdir "MonitorAgent\Logs"
#define MyAppConfigFileName "monitor_config.ini" ; Config file name

[Setup]
AppId={{A7E8C5D2-9F1B-4A9C-8D3E-0F7B1A2C3D4E}} ; Unique GUID
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
PrivilegesRequired=admin
OutputDir=.\InstallerOutput
OutputBaseFilename=MonitorAgent_Setup_v{#MyAppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "startup"; Description: "Run Monitor Agent automatically on Windows startup"; GroupDescription: "Startup Options:"; Flags: checkedonce

[Files]
; Source path to the EXE built by PyInstaller - UPDATE IF NEEDED
Source: "C:\Users\Administrator\Desktop\employee-monitoring-software\client\dist\MonitorAgent.exe"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
; Create log directory
Name: "{commonappdata}\{#MyAppLogSubdir}"; Permissions: authusers-modify
; Create config directory (same place as logs for simplicity, or use {app})
; Let's put config in {app} - Program Files - requires admin to write later if needed
; No, let's keep config writeable - put it with logs
Name: "{commonappdata}\{#MyAppName}"; Permissions: authusers-modify ; Base dir for config

[Icons]
; Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}" ; Optional Program icon
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"

[Registry]
Root: HKLM; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "{#MyAppName}"; ValueData: """{app}\{#MyAppExeName}"""; Tasks: startup

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
Type: filesandordirs; Name: "{commonappdata}\{#MyAppName}" ; Remove config/log base dir

[UninstallRegistry]
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
  end;
end;

// Function called just before the installation process begins (after user confirms)
// We store the captured values here. They'll be written to file later.
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssInstall then begin
    // Re-capture values just in case (though NextButtonClick should ensure they are set)
    EmployeeID := Trim(EmployeeInfoPage.Values[0]);
    EmployeeName := Trim(EmployeeInfoPage.Values[1]);
    Log(Format('Captured Employee ID: %s, Name: %s', [EmployeeID, EmployeeName]));
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
  if CurStep = ssPostInstall then begin
    // Construct the path to the config file: C:\ProgramData\MonitorAgent\monitor_config.ini
    ConfigPath := ExpandConstant('{commonappdata}\{#MyAppName}\{#MyAppConfigFileName}');
    Log(Format('Writing configuration to: %s', [ConfigPath]));

    ConfigLines := TStringList.Create;
    try
      ConfigLines.Add('[Agent]');
      ConfigLines.Add(Format('EmployeeID = %s', [EmployeeID]));
      ConfigLines.Add(Format('EmployeeName = %s', [EmployeeName]));
      // Add other config options here if needed in the future
      // ConfigLines.Add('ServerURL = http://...'); // Could potentially set this here too

      if SaveStringsToFile(ConfigPath, ConfigLines, False) then begin
        Log('Successfully wrote config file.');
      end else begin
        MsgBox('Failed to write configuration file to ' + ConfigPath + '.'#13#10 + 'The agent may not function correctly.', mbError, MB_OK);
        Log('ERROR: Failed to write config file.');
      end;
    finally
      ConfigLines.Free;
    end;
  end;
end;