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
# Removed: import configparser

# --- Configuration (Hardcoded Values) ---
# IMPORTANT: You MUST edit EMPLOYEE_ID before building for each user!
SERVER_URL = "http://10.0.1.142:5000" # <-- USE PRIVATE IP IF IN SAME VPC, OR PUBLIC IP
EMPLOYEE_ID = "EMP001" # <-- REPLACE with the unique ID for this specific installation
# Employee Name is no longer handled by the client in this version
CLIENT_SECRET_KEY = "YOUR_STRONG_SHARED_SECRET_BETWEEN_SERVER_AND_CLIENTS" # <-- REPLACE this secret key
REPORT_INTERVAL_SECONDS = 60
SCREENSHOT_INTERVAL_SECONDS = 300

# --- Logging Setup ---
# Logs will still go to C:\ProgramData\MonitorAgent\Logs
PROGRAMDATA_PATH = os.environ.get('PROGRAMDATA', 'C:\\ProgramData')
LOG_DIR_BASE = os.path.join(PROGRAMDATA_PATH, 'MonitorAgent', 'Logs')

# Ensure log directory exists (installer creates it, but be defensive)
try:
    os.makedirs(LOG_DIR_BASE, exist_ok=True)
except OSError as e:
    sys.stderr.write(f"ERROR: Cannot create log directory {LOG_DIR_BASE}: {e}\n")
    # Fallback log location (might fail if in Program Files)
    if getattr(sys, 'frozen', False):
        log_dir = os.path.dirname(sys.executable)
    else:
        log_dir = os.path.dirname(__file__)
    log_filepath = os.path.join(log_dir, f"monitor_agent_{EMPLOYEE_ID}_fallback.log")
else:
     # Use the correct log directory and the hardcoded Employee ID
     log_filepath = os.path.join(LOG_DIR_BASE, f"monitor_agent_{EMPLOYEE_ID}.log")

# --- Configure Logging ---
log_handlers = [logging.StreamHandler(sys.stdout)]
try:
    log_handlers.append(logging.FileHandler(log_filepath))
except Exception as e:
    sys.stderr.write(f"ERROR: Cannot create file handler for {log_filepath}: {e}\n")

logging.basicConfig(
    level=logging.INFO, # Change to logging.DEBUG for more detailed logs
    format='%(asctime)s - %(levelname)s - [%(threadName)s] - %(message)s',
    handlers=log_handlers,
    force=True # Allow reconfiguration if needed (though not done here anymore)
)
logger = logging.getLogger(__name__)
logger.info(f"Logging initialized. Log file path: {log_filepath}")


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
# Removed: identity_reported flag

# --- Core Functions ---
def get_utc_timestamp_iso():
    # (Keep this function exactly as it was)
    now_utc = datetime.now(timezone.utc)
    iso_string = now_utc.isoformat(timespec='seconds')
    logger.debug(f"Generated timestamp: {iso_string}")
    return iso_string

# Removed: send_identity_report() function

def send_activity_report():
    """Collects and sends activity data to the server."""
    # Uses the hardcoded EMPLOYEE_ID constant
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
        "employee_id": EMPLOYEE_ID, # Use hardcoded constant
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
    # Uses the hardcoded EMPLOYEE_ID constant
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
            'employee_id': EMPLOYEE_ID, # Use hardcoded constant
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
    global last_screenshot_time
    # Removed: load_configuration() call

    main_thread = threading.current_thread()
    main_thread.name = "MainThread"

    logger.info(f"Client agent starting...")
    # Log hardcoded values
    logger.info(f"Employee ID (Hardcoded): {EMPLOYEE_ID}")
    logger.info(f"Server URL: {SERVER_URL}")
    logger.info(f"Report Interval: {REPORT_INTERVAL_SECONDS}s, Screenshot Interval: {SCREENSHOT_INTERVAL_SECONDS}s")

    last_screenshot_time = time.time() - SCREENSHOT_INTERVAL_SECONDS

    # Removed: Identity reporting logic

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