import requests
import time
import mss
import platform
import threading
import sys
import io
import os
from datetime import datetime, timezone
import logging
import configparser # Import configparser

# --- Configuration (Defaults/Placeholders - will be overridden by config file) ---
# Server URL might still be hardcoded, or could also be moved to config.ini
SERVER_URL = "http://10.0.1.142:5000" # <-- USE PRIVATE IP IF IN SAME VPC, OR PUBLIC IP
CLIENT_SECRET_KEY = "YOUR_STRONG_SHARED_SECRET_BETWEEN_SERVER_AND_CLIENTS" # <-- REPLACE this secret key

# --- Global Variables for Configured Values ---
# Initialize with defaults or None, will be set by load_configuration()
CONFIGURED_EMPLOYEE_ID = "UNKNOWN_EMP_ID"
CONFIGURED_EMPLOYEE_NAME = "Unknown Employee"
CONFIG_FILE_PATH = "" # Will be set in load_configuration

# --- Logging Setup ---
# Logs will still go to C:\ProgramData\MonitorAgent\Logs
PROGRAMDATA_PATH = os.environ.get('PROGRAMDATA', 'C:\\ProgramData')
LOG_DIR_BASE = os.path.join(PROGRAMDATA_PATH, 'MonitorAgent', 'Logs')
CONFIG_DIR_BASE = os.path.join(PROGRAMDATA_PATH, 'MonitorAgent') # Config base dir

try:
    os.makedirs(LOG_DIR_BASE, exist_ok=True)
except OSError as e:
    sys.stderr.write(f"ERROR: Cannot create log directory {LOG_DIR_BASE}: {e}\n")
    if getattr(sys, 'frozen', False):
        log_dir = os.path.dirname(sys.executable)
    else:
        log_dir = os.path.dirname(__file__)
    log_filepath = os.path.join(log_dir, f"monitor_agent_UNKNOWN_fallback.log") # Use default if ID unknown
else:
     # Log filename will be updated after reading config
     log_filepath = os.path.join(LOG_DIR_BASE, f"monitor_agent_UNKNOWN.log")

# --- Configure Logging (Initial setup, will reconfigure filename later) ---
log_handlers = [logging.StreamHandler(sys.stdout)]
try:
    # Use a temporary file handler until config is read
    temp_file_handler = logging.FileHandler(log_filepath)
    log_handlers.append(temp_file_handler)
except Exception as e:
    sys.stderr.write(f"ERROR: Cannot create initial file handler for {log_filepath}: {e}\n")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(threadName)s] - %(message)s',
    handlers=log_handlers,
    force=True # Force reconfiguration if needed
)
logger = logging.getLogger(__name__)
logger.info(f"Initial logging setup. Log file intended path: {log_filepath}")


# --- Load Configuration Function ---
def load_configuration():
    global CONFIGURED_EMPLOYEE_ID, CONFIGURED_EMPLOYEE_NAME, CONFIG_FILE_PATH, logger, log_filepath

    config_filename = "monitor_config.ini"
    # Config file expected in C:\ProgramData\MonitorAgent\monitor_config.ini
    CONFIG_FILE_PATH = os.path.join(CONFIG_DIR_BASE, config_filename)
    logger.info(f"Attempting to load configuration from: {CONFIG_FILE_PATH}")

    if not os.path.exists(CONFIG_FILE_PATH):
        logger.error(f"Configuration file not found: {CONFIG_FILE_PATH}")
        # Stick with defaults/placeholders - agent might not work correctly
        return False

    config = configparser.ConfigParser()
    try:
        config.read(CONFIG_FILE_PATH)
        if 'Agent' in config:
            CONFIGURED_EMPLOYEE_ID = config['Agent'].get('EmployeeID', CONFIGURED_EMPLOYEE_ID)
            CONFIGURED_EMPLOYEE_NAME = config['Agent'].get('EmployeeName', CONFIGURED_EMPLOYEE_NAME)
            logger.info(f"Configuration loaded: ID='{CONFIGURED_EMPLOYEE_ID}', Name='{CONFIGURED_EMPLOYEE_NAME}'")

            # --- Reconfigure Log Filename ---
            new_log_filepath = os.path.join(LOG_DIR_BASE, f"monitor_agent_{CONFIGURED_EMPLOYEE_ID}.log")
            if new_log_filepath != log_filepath:
                 logger.info(f"Updating log file path to: {new_log_filepath}")
                 # Remove old handler, add new one
                 root_logger = logging.getLogger()
                 old_handler = None
                 for h in root_logger.handlers:
                     if isinstance(h, logging.FileHandler) and getattr(h, 'baseFilename', '') == log_filepath:
                         old_handler = h
                         break
                 if old_handler:
                     root_logger.removeHandler(old_handler)
                     old_handler.close()

                 try:
                     new_file_handler = logging.FileHandler(new_log_filepath)
                     # Use the same formatter as basicConfig
                     formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(threadName)s] - %(message)s')
                     new_file_handler.setFormatter(formatter)
                     root_logger.addHandler(new_file_handler)
                     log_filepath = new_log_filepath # Update global path
                     logger.info("Successfully reconfigured file logger.")
                 except Exception as e:
                     logger.error(f"Failed to create new file handler for {new_log_filepath}: {e}")
                     # Attempt to re-add the old handler if possible? Or just log to console.
                     if old_handler:
                         root_logger.addHandler(old_handler) # Put back the old one if new failed


            return True
        else:
            logger.error(f"Missing [Agent] section in configuration file: {CONFIG_FILE_PATH}")
            return False

    except configparser.Error as e:
        logger.error(f"Error parsing configuration file {CONFIG_FILE_PATH}: {e}")
        return False
    except Exception as e:
         logger.error(f"Unexpected error loading configuration: {e}", exc_info=True)
         return False


# --- Platform Specific Imports ---
# (Keep this section exactly as it was)
try:
    if platform.system() == "Windows":
        from windows_specific import get_active_window_title, get_idle_time
        logger.info("Imported Windows specific functions.")
    elif platform.system() == "Darwin": # macOS
        from macos_specific import get_active_window_title, get_idle_time
        logger.info("Imported macOS specific functions.")
    else:
        logger.warning(f"Unsupported OS '{platform.system()}' for detailed activity tracking.")
        def get_active_window_title(): return "N/A (Unsupported OS)"
        def get_idle_time(): return 0
except ImportError as e:
    logger.error(f"Could not import platform specific module: {e}. Activity/Idle tracking may fail.")
    def get_active_window_title(): return "N/A (Import Error)"
    def get_idle_time(): return 0


# --- Global State ---
last_screenshot_time = 0
identity_reported = False # Flag to ensure identity is reported only once

# --- Core Functions ---
def get_utc_timestamp_iso():
    # (Keep this function exactly as it was)
    now_utc = datetime.now(timezone.utc)
    iso_string = now_utc.isoformat(timespec='seconds')
    logger.debug(f"Generated timestamp: {iso_string}")
    return iso_string

# --- NEW Function: Report Identity ---
def send_identity_report():
    """Sends Employee ID and Name to the server."""
    global CONFIGURED_EMPLOYEE_ID, CONFIGURED_EMPLOYEE_NAME, SERVER_URL, CLIENT_SECRET_KEY, identity_reported

    # Use configured values read from file
    employee_id = CONFIGURED_EMPLOYEE_ID
    employee_name = CONFIGURED_EMPLOYEE_NAME

    if employee_id == "UNKNOWN_EMP_ID":
        logger.error("Cannot report identity: Employee ID is unknown (config load failed?).")
        return False

    logger.info(f"Attempting to report identity for ID: {employee_id}, Name: {employee_name}")

    payload = {
        "employee_id": employee_id,
        "name": employee_name,
        "timestamp_utc": get_utc_timestamp_iso() # Include timestamp for context
    }
    headers = {'X-Client-Secret': CLIENT_SECRET_KEY, 'Content-Type': 'application/json'}

    try:
        url = f"{SERVER_URL}/api/report_identity" # New endpoint
        logger.info(f"Posting identity report to {url}")
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        response.raise_for_status()
        logger.info(f"Identity report sent successfully. Status: {response.status_code}, Response: {response.text}")
        identity_reported = True # Mark as reported
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send identity report: {e}")
        if e.response is not None:
             logger.error(f"Server response: Status={e.response.status_code}, Text={e.response.text}")
        return False # Will retry on next agent start
    except Exception as e:
        logger.error(f"An unexpected error occurred sending identity report: {e}", exc_info=True)
        return False


def send_activity_report():
    """Collects and sends activity data to the server."""
    # Uses CONFIGURED_EMPLOYEE_ID directly now
    employee_id = CONFIGURED_EMPLOYEE_ID
    # ... rest of the function is the same, just uses employee_id variable ...
    current_thread = threading.current_thread()
    current_thread.name = f"ActivityReportThread-{current_thread.ident}"
    logger.info("Activity report thread started.")
    timestamp = get_utc_timestamp_iso()
    active_window = "Error"
    idle_time = -1
    try:
        active_window = get_active_window_title()
        idle_time = get_idle_time()
        logger.info(f"Collected activity: window='{active_window}', idle={idle_time}s")
    except Exception as e:
        logger.error(f"Error getting system info: {e}", exc_info=True)

    payload = {
        "employee_id": employee_id, # Use configured ID
        "timestamp_utc": timestamp,
        "active_window": active_window,
        "system_idle_time": int(idle_time)
    }
    headers = {'X-Client-Secret': CLIENT_SECRET_KEY, 'Content-Type': 'application/json'}
    logger.info(f"Sending /api/report payload: {payload}")
    try:
        url = f"{SERVER_URL}/api/report"
        logger.info(f"Posting activity report to {url}")
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        response.raise_for_status()
        logger.info(f"Activity report sent successfully. Status: {response.status_code}, Response: {response.text}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send activity report: {e}")
        if e.response is not None:
             logger.error(f"Server response: Status={e.response.status_code}, Text={e.response.text}")
    except Exception as e:
        logger.error(f"An unexpected error occurred sending activity report: {e}", exc_info=True)
    logger.info("Activity report thread finished.")


def take_and_send_screenshot():
    """Takes a screenshot and uploads it to the server."""
    # Uses CONFIGURED_EMPLOYEE_ID directly now
    employee_id = CONFIGURED_EMPLOYEE_ID
    # ... rest of the function is the same, just uses employee_id variable ...
    current_thread = threading.current_thread()
    current_thread.name = f"ScreenshotThread-{current_thread.ident}"
    logger.info("Screenshot thread started.")
    timestamp_dt = datetime.now(timezone.utc)
    timestamp_iso = timestamp_dt.isoformat(timespec='seconds')
    logger.debug(f"Generated screenshot timestamp: {timestamp_iso}")
    try:
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            logger.info(f"Capturing screenshot from monitor: {monitor}")
            sct_img = sct.grab(monitor)
            img_bytes = mss.tools.to_png(sct_img.rgb, sct_img.size)
            img_file = io.BytesIO(img_bytes)
            logger.info(f"Screenshot taken, size: {len(img_bytes)} bytes")

        screenshot_filename = f"{timestamp_dt.strftime('%Y%m%d_%H%M%S')}.png"
        files = {'screenshot': (screenshot_filename, img_file, 'image/png')}
        payload = {
            'employee_id': employee_id, # Use configured ID
            'timestamp_utc': timestamp_iso
        }
        headers = {'X-Client-Secret': CLIENT_SECRET_KEY}
        logger.info(f"Sending /api/upload_screenshot payload: {payload}, filename: {screenshot_filename}")
        url = f"{SERVER_URL}/api/upload_screenshot"
        logger.info(f"Uploading screenshot to {url}")
        response = requests.post(url, files=files, data=payload, headers=headers, timeout=30)
        response.raise_for_status()
        logger.info(f"Screenshot uploaded successfully. Status: {response.status_code}, Response: {response.text}")
        return True
    except (mss.ScreenShotError, IndexError) as e:
        logger.error(f"Failed to take screenshot: {e}", exc_info=True)
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to upload screenshot: {e}")
        if e.response is not None:
             logger.error(f"Server response: Status={e.response.status_code}, Text={e.response.text}")
        return False
    except Exception as e:
        logger.error(f"An unexpected error occurred during screenshot process: {e}", exc_info=True)
        return False
    logger.info("Screenshot thread finished.")


# --- Main Loop ---
def main_loop():
    global last_screenshot_time, identity_reported

    # --- LOAD CONFIGURATION FIRST ---
    if not load_configuration():
        logger.critical("Failed to load essential configuration. Agent might not function correctly. Exiting?")
        # Decide if you want to exit or try to run with defaults
        # For now, we'll continue with potentially wrong defaults, but log critical error
        # return # Uncomment to exit if config fails

    main_thread = threading.current_thread()
    main_thread.name = "MainThread"

    logger.info(f"Client agent starting...")
    # Log configured values
    logger.info(f"Employee ID (from config): {CONFIGURED_EMPLOYEE_ID}")
    logger.info(f"Employee Name (from config): {CONFIGURED_EMPLOYEE_NAME}")
    logger.info(f"Server URL: {SERVER_URL}")
    logger.info(f"Report Interval: {REPORT_INTERVAL_SECONDS}s, Screenshot Interval: {SCREENSHOT_INTERVAL_SECONDS}s")

    last_screenshot_time = time.time() - SCREENSHOT_INTERVAL_SECONDS

    # --- Attempt to report identity ONCE on startup ---
    if not identity_reported:
        # Run in a separate thread so it doesn't block the main loop start
        identity_thread = threading.Thread(target=send_identity_report, daemon=True)
        identity_thread.start()
        # Note: We don't strictly wait for it. If it fails, it won't retry until agent restarts.

    while True:
        current_time = time.time()
        logger.debug(f"Main loop iteration. Current time: {current_time}")

        try:
            logger.debug("Starting activity report thread.")
            activity_thread = threading.Thread(target=send_activity_report, daemon=True)
            activity_thread.start()

            time_since_last_screenshot = current_time - last_screenshot_time
            logger.debug(f"Time since last screenshot: {time_since_last_screenshot:.2f}s")
            if time_since_last_screenshot >= SCREENSHOT_INTERVAL_SECONDS:
                logger.info("Screenshot interval reached. Starting screenshot thread.")
                screenshot_thread = threading.Thread(target=take_and_send_screenshot, daemon=True)
                screenshot_thread.start()
                last_screenshot_time = current_time
            else:
                logger.debug("Screenshot interval not reached.")

            sleep_duration = REPORT_INTERVAL_SECONDS
            logger.debug(f"Sleeping for {sleep_duration} seconds.")
            time.sleep(sleep_duration)

        except KeyboardInterrupt:
            logger.info("Client agent stopping due to KeyboardInterrupt.")
            break
        except Exception as e:
            logger.error(f"CRITICAL ERROR in main loop: {e}", exc_info=True)
            logger.info("Waiting 60 seconds after critical error before retrying loop.")
            time.sleep(60)

if __name__ == "__main__":
    main_loop()