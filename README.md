# Employee Monitoring Software (Python/Flask/MongoDB)

**[CRITICAL WARNING] Ethical and Legal Considerations:**
This software is designed to monitor computer activity, including taking screenshots and tracking application usage. Deploying such software without the explicit, informed consent of the monitored individuals is unethical and **illegal** in many regions. Ensure you fully understand and comply with all applicable laws and regulations regarding employee privacy and monitoring **before** using or deploying this software. Use this code responsibly and ethically. The author assumes no liability for misuse.

**[TECHNICAL WARNING] Stealth and Detection:**
This software runs as a background process installed via a standard installer. It is **not** designed to be truly stealthy or evade detection by technically proficient users or antivirus/security software. Antivirus programs are **highly likely** to flag the client agent (`MonitorAgent.exe`) and potentially the installer (`MonitorAgent_Setup*.exe`). Explicit exceptions in security software will be required on target machines.

## Overview

This project provides a basic system for monitoring employee computer activity. It consists of:

*   **Server (Flask on Linux/CentOS 9):**
    *   Receives data (screenshots, activity logs) from client agents.
    *   Stores data in MongoDB.
    *   Stores screenshot images on the filesystem.
    *   Provides a web UI for administrators to view employee data (timestamps displayed in IST).
    *   Basic admin login authentication.
*   **Client (Windows Agent):**
    *   Built into a single `.exe` file using PyInstaller.
    *   Packaged into a standard Windows installer (`setup.exe`) using Inno Setup.
    *   Installs agent to run automatically on startup (requires Admin rights during install).
    *   Periodically takes screenshots and collects active window/idle time.
    *   Sends data to the server using the server's **private IP address**.
    *   Logs activity to `C:\ProgramData\MonitorAgent\Logs\`.
    *   Requires Employee ID to be hardcoded *before* building the EXE.


## Prerequisites

### Server (CentOS 9)

*   Python 3.8+ (`python3`, `python3-pip`)
*   Development tools (`python3-devel`, `gcc` - needed for some pip installs)
*   MongoDB Server (running and accessible)
*   `git` (optional, for cloning)
*   `pytz` Python library (`pip install pytz`) - For IST display

### Client Build Machine (Windows)

*   Python 3.8+ (ensure it's added to PATH)
*   `pip` (Python package installer)
*   Python libraries: `requests`, `mss`, `pywin32` (install via `pip install -r client/requirements.txt`)
*   PyInstaller (`pip install pyinstaller`)
*   **Inno Setup 6 Compiler:** Download and install from [jrsoftware.org](https://jrsoftware.org/isinfo.php).

### Target Client Machine (Windows)

*   Compatible Windows version (Win 7/8/10/11, matching architecture - likely 64-bit).
*   Microsoft Visual C++ Redistributable (usually present, but might be needed depending on Python/library versions).
*   Network connectivity to the server's **Private IP** on port 5000.
*   Administrator rights (required for installation).
*   **Antivirus/Security Software Exceptions:** Must be configured to allow `MonitorAgent.exe` to run and make network connections.

## Setup & Installation Steps

### Step 1: Server Setup (CentOS 9)

1.  **Connect & Update:**
    *   SSH into your CentOS 9 server.
    *   Update the system: `sudo dnf update -y`
2.  **Install Dependencies:**
    *   Install Python, pip, and development tools:
        ```bash
        sudo dnf install -y python3 python3-pip python3-devel gcc
        ```
    *   Install MongoDB (Follow official MongoDB instructions for CentOS 9: [https://www.mongodb.com/docs/manual/tutorial/install-mongodb-on-red-hat/](https://www.mongodb.com/docs/manual/tutorial/install-mongodb-on-red-hat/))
    *   Start and enable MongoDB:
        ```bash
        sudo systemctl start mongod
        sudo systemctl enable mongod
        ```
    *   Verify MongoDB is running: `sudo systemctl status mongod`
    *   Install git (optional): `sudo dnf install -y git`
3.  **Get Project Code:**
    *   Navigate to where you want to store the project (e.g., `/root/`).
    *   Clone repository or copy files:
        ```bash
        # Example using git:
        # git clone -b beta https://github.com/nani-1205/employee-monitoring-software.git
        # cd employee-monitoring-software/server

        # Or copy the 'server' directory here via other means
        cd /path/to/your/server_directory
        ```
4.  **Setup Python Environment:**
    *   Create a virtual environment: `python3 -m venv venv`
    *   Activate it: `source venv/bin/activate`
    *   Install required Python packages:
        ```bash
        pip install -r requirements.txt
        pip install pytz # Install timezone library
        ```
5.  **Configure Server:**
    *   Create the environment configuration file: `cp .env.example .env` (if you have an example) or create `server/.env` manually.
    *   **Edit `server/.env`** and set **ALL** the following values securely:
        *   `SECRET_KEY`: Generate with `python -c 'import secrets; print(secrets.token_hex(16))'`
        *   `MONGO_HOST`: Usually `localhost` if DB is on the same server, or the DB server's IP.
        *   `MONGO_PORT`: Default is `27017`.
        *   `MONGO_USERNAME`: Your MongoDB user.
        *   `MONGO_PASSWORD`: Your MongoDB password.
        *   `MONGO_DB_NAME`: e.g., `employee_monitor`.
        *   `MONGO_AUTH_DB`: Usually `admin` or the DB where the user is defined.
        *   `ADMIN_USERNAME`: Desired username for the web UI login.
        *   `ADMIN_PASSWORD`: **Secure** password for the web UI login (change default!).
        *   `CLIENT_SECRET_KEY`: A strong, random secret shared with the client configuration (generate one).
        *   `FLASK_DEBUG`: Set to `False` for production.
    *   **Important:** Make sure MongoDB is configured with the specified user and password.
6.  **Prepare Storage:**
    *   The code expects `server/storage/screenshots`. It tries to create it.
    *   Ensure the user running the Flask app will have write permissions to this directory. If using PM2/Gunicorn under a specific user, you might need `sudo chown -R user:group storage` and `sudo chmod -R u+rwX storage`.
7.  **Configure Firewall (If Necessary):**
    *   You confirmed `firewalld` and `iptables` services are not active on your OS.
    *   **CRITICAL:** Ensure your **Cloud Provider's Security Group** (AWS EC2, etc.) allows **Inbound TCP traffic on port 5000** from the source IP range of your client machines (or `0.0.0.0/0` for testing - narrow later).
8.  **Run the Server:**
    *   **Using PM2 (Recommended for background running):**
        ```bash
        # Ensure you are in the server directory with venv active
        # Install PM2 if you haven't: sudo npm install pm2 -g
        pm2 start app.py --name MonitorServer --interpreter python3
        pm2 save # Make PM2 restart on server reboot
        pm2 logs MonitorServer # View logs
        ```
    *   **Directly (for testing):**
        ```bash
        # Ensure you are in the server directory with venv active
        python app.py
        ```

### Step 2: Client Build (Windows Build Machine)

1.  **Get Project Code:**
    *   Clone or copy the entire project to your Windows build machine.
2.  **Install Build Tools:**
    *   Install Python 3.8+ (ensure `pip` is included and Python is in PATH).
    *   Install Inno Setup 6 Compiler ([jrsoftware.org](https://jrsoftware.org/isinfo.php)).
3.  **Prepare Client Code:**
    *   Navigate to the `client` directory in Command Prompt or PowerShell.
    *   Install Python requirements: `pip install -r requirements.txt`
    *   Install PyInstaller: `pip install pyinstaller`
4.  **Configure Client Agent:**
    *   **CRITICAL:** Open `client/client_agent.py` in a text editor.
    *   Set the `SERVER_URL`: Use the server's **PRIVATE IP ADDRESS** (e.g., `http://10.0.1.126:5000`) since the client is in the same VPC.
    *   Set the `EMPLOYEE_ID`: Assign a **UNIQUE** ID for the specific target user/PC (e.g., `EMP002`, `JSMITHPC`). **You need to edit this before building for each different employee.**
    *   Set the `CLIENT_SECRET_KEY`: Must be **identical** to the `CLIENT_SECRET_KEY` set in the server's `.env` file.
    *   Save the file.
5.  **Build the Executable:**
    *   Open Command Prompt or PowerShell **in the `client` directory**.
    *   Run the build script: `.\build_exe.bat` (use `.\` in PowerShell).
    *   Verify `MonitorAgent.exe` is created in the `client\dist\` folder.
6.  **Configure the Installer Script:**
    *   Open `client/MonitorAgent_Setup.iss` in a text editor.
    *   Verify the `Source:` line in the `[Files]` section correctly points to the `.exe` you just built (e.g., `Source: "C:\path\to\project\client\dist\MonitorAgent.exe"`).
    *   Verify/change the `AppId` GUID (use a unique one for your app).
    *   Verify/change `MyAppPublisher`.
    *   Save the file.
7.  **Build the Installer:**
    *   Open the Inno Setup Compiler application.
    *   Go to "File" -> "Open" and select `client/MonitorAgent_Setup.iss`.
    *   Go to "Build" -> "Compile".
    *   Verify `MonitorAgent_Setup_v1.0.exe` (or similar) is created in `client\InstallerOutput\`.

### Step 3: Client Installation (Target Windows PC)

1.  **Copy Installer:** Transfer the generated `MonitorAgent_Setup_vX.X.exe` from the `InstallerOutput` folder to the target Windows PC (the employee's machine).
2.  **Run Installer as Admin:**
    *   Right-click on the `MonitorAgent_Setup_vX.X.exe` file.
    *   Select "**Run as administrator**".
    *   Click **Yes** on the User Account Control (UAC) prompt.
3.  **Follow Wizard:** Proceed through the installation wizard. Ensure the "Run Monitor Agent automatically on Windows startup" task is **checked** if you want it to auto-start.
4.  **Antivirus/Firewall:** During or immediately after installation, Windows Defender or other security software might block or quarantine `MonitorAgent.exe`. You **must** configure the security software on the target PC to **allow** or create an **exception** for:
    *   The file: `C:\Program Files (x86)\Monitor Agent\MonitorAgent.exe` (or similar path).
    *   The process: `MonitorAgent.exe`.
    *   Network connections made by `MonitorAgent.exe` to your server's private IP and port 5000.

### Step 4: Verification

1.  **Server:** Check the server logs (`pm2 logs MonitorServer`) to ensure it's running without errors.
2.  **Client:**
    *   Restart the target Windows PC.
    *   After it boots up and the user logs in, wait a minute or two.
    *   Open **Task Manager** (`Ctrl+Shift+Esc`) and check if `MonitorAgent.exe` is running in the Processes/Details tab.
    *   Check the client log file for activity and connection status: `C:\ProgramData\MonitorAgent\Logs\monitor_agent_EMP00X.log` (replace `EMP00X` with the ID you used; `ProgramData` is hidden by default). Look for successful posts or connection errors.
3.  **Web UI:**
    *   Open your web browser and go to the server's **Public IP** address on port 5000 (e.g., `http://0.0.0.0:5000`). You use the Public IP here because you are accessing it from *your* browser, outside the VPC.
    *   Log in using the `ADMIN_USERNAME` and `ADMIN_PASSWORD` from the server's `.env` file.
    *   The dashboard should now list the employee (using the `EMPLOYEE_ID`). Click "View Details" to see activity logs and screenshots (allow time for them to be generated and uploaded). Timestamps should be in IST.

## Usage

*   **Monitoring:** Once installed correctly and allowed by security software, the client agent runs automatically in the background after user login. It sends data periodically based on the intervals set in `client_agent.py`.
*   **Viewing Data:** Access the web dashboard via the server's **Public IP** and port 5000. Log in as admin. Navigate the dashboard and employee detail pages.
*   **Uninstallation:** Use the standard Windows "Apps & features" (Settings) or "Programs and Features" (Control Panel) to find "Monitor Agent" and uninstall it. Administrator rights will be required via UAC prompt. Stopping the agent process via Task Manager first is recommended.

## Security Considerations

*   **HTTPS:** The current setup uses HTTP. **Strongly recommended:** Set up a reverse proxy (like Nginx or Caddy) on the server to handle HTTPS/TLS encryption for both the web UI and the API endpoints.
*   **Secrets:** Keep the `.env` file secure. Do not commit it to version control. Use strong, unique passwords and keys.
*   **Permissions:** Run the server process under a non-root user with minimal privileges. Ensure file permissions for storage are appropriate. Client installation requires admin rights.
*   **Network:** Restrict the source IP in the Cloud Security Group rule for port 5000 to only known client IP ranges if possible, instead of `0.0.0.0/0`.
*   **Input Validation:** Server-side code should rigorously validate all data received from clients.

## Troubleshooting


*   **Client Not Appearing:** Check client logs (`C:\ProgramData\MonitorAgent\Logs\*`), check Task Manager, check antivirus/firewall on client, check network connectivity (using Private IP) from client to server (`Test-NetConnection`), check server logs (`pm2 logs MonitorServer`).
*   **Data Not Saving:** Check server logs for database errors, check MongoDB connection/authentication, check server disk space.
*   **Installer Errors:** Check Inno Setup documentation, ensure paths in `.iss` are correct, ensure admin rights are used.
*   **Timestamp Issues:** Ensure server has `pytz` installed, check server logs for parsing errors, verify client sends UTC.

