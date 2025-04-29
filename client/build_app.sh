#!/bin/bash
echo "Building macOS APP for client_agent.py..."

# Ensure you have PyInstaller installed: pip install pyinstaller

# Create a virtual environment (optional but recommended)
# python3 -m venv venv
# source venv/bin/activate

# Install requirements
pip3 install -r requirements.txt
# Ensure macOS specific libs are installed (might need manual install based on Python/macOS version)
pip3 install pyobjc-framework-Quartz pyobjc-framework-Cocoa

# Build the APP bundle
# --windowed: Equivalent to --noconsole on Windows, creates a GUI app without a terminal
# --name: Sets the name of the output .app bundle
# Add --hidden-import if needed for pyobjc modules
pyinstaller --windowed --name MonitorAgent client_agent.py macos_specific.py

echo "---"
echo "Build complete. Find the APP bundle in the 'dist' folder."
echo "Remember to replace placeholder values (SERVER_URL, EMPLOYEE_ID, CLIENT_SECRET_KEY)"
echo "in client_agent.py BEFORE building for deployment!"
echo "---"
echo "To create a DMG (optional):"
echo "hdiutil create dist/MonitorAgent.dmg -volname \"Monitor Agent\" -srcfolder dist/MonitorAgent.app"
echo "---"
echo "NOTE: macOS requires user permission for screen recording and accessibility features."
echo "The application will likely prompt the user for these permissions when first run."
echo "---"

# Deactivate virtual environment if used
# deactivate