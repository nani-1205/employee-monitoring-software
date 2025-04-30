@echo off
echo Building Windows EXE for client_agent.py using PyInstaller...
echo This EXE will later be packaged by an installer (e.g., Inno Setup).
echo ---

REM ###########################################################
REM ## Prerequisites:                                        ##
REM ## 1. Python 3 installed and accessible in PATH.         ##
REM ## 2. pip installed.                                     ##
REM ## 3. PyInstaller installed: run 'pip install pyinstaller' ##
REM ## 4. Run this script from the 'client' directory.       ##
REM ## 5. ENSURE client_agent.py is configured correctly!    ##
REM ###########################################################

REM --- Optional: Activate Virtual Environment ---
REM IF EXIST venv\Scripts\activate.bat ( call venv\Scripts\activate.bat )

REM --- Install Dependencies ---
echo Installing dependencies from requirements.txt...
pip install -r requirements.txt
IF %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to install dependencies from requirements.txt.
    goto :eof
)
echo Dependency installation complete.
echo ---

REM --- Check for PyInstaller ---
pyinstaller --version > nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo ERROR: PyInstaller is not found or not in PATH. Install with: pip install pyinstaller
    goto :eof
) else (
    echo PyInstaller found. Proceeding with build...
)
echo ---

REM --- Build the Executable ---
echo Running PyInstaller...
pyinstaller --noconsole --onefile --name=MonitorAgent client_agent.py windows_specific.py --hidden-import=win32timezone

IF %ERRORLEVEL% NEQ 0 (
    echo ERROR: PyInstaller failed to build the executable. Check output above.
    goto :BuildEnd
)
echo ---

REM --- Check for Output File ---
IF EXIST dist\MonitorAgent.exe (
  echo SUCCESS: Build completed. Executable 'MonitorAgent.exe' created in the 'dist' folder.
  echo ---
  echo NEXT STEP: Use this 'dist\MonitorAgent.exe' as the source file in your Inno Setup script (MonitorAgent_Setup.iss).
) ELSE (
  echo WARNING: Build process finished, but 'dist\MonitorAgent.exe' was not found. Check logs.
)
echo ---

:BuildEnd
REM --- Optional: Deactivate Virtual Environment ---
REM IF DEFINED VIRTUAL_ENV ( call deactivate )

REM --- Pause to see output ---
pause

:eof