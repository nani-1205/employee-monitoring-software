@echo off
echo Building Windows EXE for client_agent.py...

REM Ensure you have PyInstaller installed: pip install pyinstaller

REM Create a virtual environment (optional but recommended)
REM python -m venv venv
REM .\venv\Scripts\activate

REM Install requirements
pip install -r requirements.txt
pip install pywin32  REM Ensure windows specific is installed

REM Build the EXE
REM --noconsole: Prevents console window from appearing (more "stealthy")
REM --onefile: Creates a single executable file
REM --name: Sets the name of the output executable
REM --hidden-import: Sometimes needed if PyInstaller misses imports (e.g., for pywin32)
pyinstaller --noconsole --onefile --name=MonitorAgent client_agent.py windows_specific.py --hidden-import=win32timezone

echo ---
echo Build complete. Find the EXE in the 'dist' folder.
echo Remember to replace placeholder values (SERVER_URL, EMPLOYEE_ID, CLIENT_SECRET_KEY)
echo in client_agent.py BEFORE building for deployment!
echo Also, you might need admin rights to run the final EXE for monitoring features.
echo ---

REM Deactivate virtual environment if used
REM deactivate

pause