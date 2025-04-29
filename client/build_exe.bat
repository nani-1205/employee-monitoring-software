@echo off
echo Building Windows EXE for client_agent.py...
echo ---

REM ###########################################################
REM ## Prerequisites:                                        ##
REM ## 1. Python 3 installed and accessible in PATH.         ##
REM ## 2. pip installed.                                     ##
REM ## 3. PyInstaller installed: run 'pip install pyinstaller' ##
REM ## 4. Run this script from the 'client' directory.       ##
REM ###########################################################

REM --- Optional: Activate Virtual Environment ---
REM If you created a virtual environment (e.g., 'venv'), activate it first:
REM echo Activating virtual environment (if applicable)...
REM IF EXIST venv\Scripts\activate.bat (
REM     call venv\Scripts\activate.bat
REM     echo Virtual environment activated.
REM ) ELSE (
REM     echo No virtual environment 'venv' found or already active.
REM )
REM echo ---

REM --- Install Dependencies ---
echo Installing dependencies from requirements.txt...
pip install -r requirements.txt
IF %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to install dependencies from requirements.txt. Please check the file and network connection.
    goto :eof
)
echo Dependency installation complete.
echo ---

REM --- Check for PyInstaller ---
pyinstaller --version > nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo ERROR: PyInstaller is not found or not in PATH.
    echo Please install it using: pip install pyinstaller
    goto :eof
) else (
    echo PyInstaller found. Proceeding with build...
)
echo ---

REM --- Build the Executable ---
REM Parameters explained:
REM   --noconsole : Run without a visible console window (background process). Crucial for monitoring.
REM   --onefile   : Package everything into a single .exe file. Easier deployment.
REM   --name      : Specify the name of the output executable file.
REM   --hidden-import=win32timezone : Explicitly include modules PyInstaller might miss, common with pywin32.
REM   client_agent.py    : Your main script.
REM   windows_specific.py: Include platform-specific code (PyInstaller usually detects this, but explicit is safer).

echo Running PyInstaller...
pyinstaller --noconsole --onefile --name=MonitorAgent client_agent.py windows_specific.py --hidden-import=win32timezone

IF %ERRORLEVEL% NEQ 0 (
    echo ERROR: PyInstaller failed to build the executable. Check the output above for specific errors.
    goto :BuildEnd
)
echo ---

REM --- Check for Output File ---
IF EXIST dist\MonitorAgent.exe (
  echo SUCCESS: Build completed. Executable 'MonitorAgent.exe' created in the 'dist' folder.
) ELSE (
  echo WARNING: Build process finished, but the expected output file 'dist\MonitorAgent.exe' was not found. Check PyInstaller logs above.
)
echo ---

:BuildEnd
REM --- Important Reminders ---
echo [REMINDER] Ensure you have replaced placeholder values in client_agent.py:
echo   - SERVER_URL
echo   - EMPLOYEE_ID (Must be unique per installation)
echo   - CLIENT_SECRET_KEY (Must match the server configuration)
echo [REMINDER] The final EXE might require Administrator privileges to run correctly
echo          (e.g., for capturing screenshots or active window info reliably).
echo ---

REM --- Optional: Deactivate Virtual Environment ---
REM IF DEFINED VIRTUAL_ENV (
REM     echo Deactivating virtual environment...
REM     call deactivate
REM )

REM --- Pause to see output ---
pause

:eof