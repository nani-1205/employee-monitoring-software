import requests
import time
import mss # For screenshots
import platform
import threading
import sys
import io
from datetime import datetime, timezone
import logging # Basic logging for the client

# --- Configuration ---
# IMPORTANT: These should ideally be configured during deployment/build, not hardcoded directly.
#            Maybe read from a config file or environment variables.
SERVER_URL = "http://YOUR_CENTOS_SERVER_IP:5000" # REPLACE WITH ACTUAL SERVER IP/DOMAIN
EMPLOYEE_ID = "EMP001" # REPLACE with a unique ID for each employee/installation
REPORT_INTERVAL_SECONDS = 60  # Send activity report every 60 seconds
SCREENSHOT_INTERVAL_SECONDS = 300 # Take screenshot every 5 minutes (300 seconds)
CLIENT_SECRET_KEY = "default_client_secret" # REPLACE with the actual secret key from server config

# --- Logging Setup ---
# In a real scenario, log to a file, especially for background processes
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Platform Specific Imports ---
try:
    if platform.system() == "Windows":
        from windows_specific import get_active_window_title, get_idle_time
    elif platform.system() == "Darwin": # macOS
        from macos_specific import get_active_window_title, get_idle_time
    else:
        # Basic fallback for other OS (Linux desktop, etc.)
        def get_active_window_title(): return "N/A (Unsupported OS)"
        def get_idle_time(): return 0
except ImportError as e:
    logger.error(f"Could not import platform specific module: {e}. Activity/Idle tracking may fail.")
    def get_active_window_title(): return "N/A (Import Error)"
    def get_idle_time(): return 0

# --- Global State ---
last_screenshot_time = 0

# --- Core Functions ---
def get_utc_timestamp_iso():
    """Returns the current UTC time as an ISO 8601 formatted string."""
    return datetime.now(timezone.utc).isoformat(timespec='seconds') + "Z"

def send_activity_report():
    """Collects and sends activity data to the server."""
    global EMPLOYEE_ID, SERVER_URL, CLIENT_SECRET_KEY
    timestamp = get_utc_timestamp_iso()
    active_window = "Error"
    idle_time = -1
    try:
        active_window = get_active_window_title()
        idle_time = get_idle_time()
    except Exception as e:
        logger.error(f"Error getting system info: {e}")


    payload = {
        "employee_id": EMPLOYEE_ID,
        "timestamp_utc": timestamp,
        "active_window": active_window,
        "system_idle_time": int(idle_time) # Send as integer seconds
    }
    headers = {'X-Client-Secret': CLIENT_SECRET_KEY}

    try:
        url = f"{SERVER_URL}/api/report"
        response = requests.post(url, json=payload, headers=headers, timeout=15) # 15 sec timeout
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        logger.info(f"Activity report sent successfully. Status: {response.status_code}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send activity report: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred sending activity report: {e}")

def take_and_send_screenshot():
    """Takes a screenshot and uploads it to the server."""
    global EMPLOYEE_ID, SERVER_URL, CLIENT_SECRET_KEY
    timestamp_dt = datetime.now(timezone.utc) # Get datetime object for filename logic
    timestamp_iso = timestamp_dt.isoformat(timespec='seconds') + "Z" # ISO string for payload

    try:
        with mss.mss() as sct:
            # Capture the primary monitor
            monitor = sct.monitors[1] # Index 1 is usually the primary monitor
            sct_img = sct.grab(monitor)

            # Convert to PNG bytes in memory
            img_bytes = mss.tools.to_png(sct_img.rgb, sct_img.size)
            img_file = io.BytesIO(img_bytes)

        # Prepare data for POST request (multipart/form-data)
        files = {'screenshot': ('screenshot.png', img_file, 'image/png')}
        payload = {
            'employee_id': EMPLOYEE_ID,
            'timestamp_utc': timestamp_iso
        }
        headers = {'X-Client-Secret': CLIENT_SECRET_KEY}

        url = f"{SERVER_URL}/api/upload_screenshot"
        response = requests.post(url, files=files, data=payload, headers=headers, timeout=30) # 30 sec timeout for upload
        response.raise_for_status()
        logger.info(f"Screenshot uploaded successfully. Status: {response.status_code}")
        return True # Indicate success

    except (mss.ScreenShotError, IndexError) as e:
        logger.error(f"Failed to take screenshot: {e}")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to upload screenshot: {e}")
        return False
    except Exception as e:
        logger.error(f"An unexpected error occurred during screenshot process: {e}")
        return False


# --- Main Loop ---
def main_loop():
    global last_screenshot_time
    logger.info(f"Client agent started for Employee ID: {EMPLOYEE_ID}")
    logger.info(f"Server URL: {SERVER_URL}")
    logger.info(f"Report Interval: {REPORT_INTERVAL_SECONDS}s, Screenshot Interval: {SCREENSHOT_INTERVAL_SECONDS}s")

    while True:
        try:
            current_time = time.time()

            # Send Activity Report
            # Run in a separate thread to avoid blocking screenshot timing
            threading.Thread(target=send_activity_report, daemon=True).start()

            # Check if it's time for a screenshot
            if current_time - last_screenshot_time >= SCREENSHOT_INTERVAL_SECONDS:
                 # Run in a separate thread
                threading.Thread(target=take_and_send_screenshot, daemon=True).start()
                last_screenshot_time = current_time # Update time even if upload fails, retry next interval


            # Wait before next cycle, adjusting for processing time if needed (simplified here)
            time.sleep(REPORT_INTERVAL_SECONDS)

        except KeyboardInterrupt:
            logger.info("Client agent stopping due to KeyboardInterrupt.")
            break
        except Exception as e:
            logger.error(f"Error in main loop: {e}", exc_info=True)
            # Avoid crashing the agent, wait before retrying
            time.sleep(30) # Wait 30 seconds after a major error

if __name__ == "__main__":
    # Initialize last screenshot time to allow immediate first screenshot if interval is short
    last_screenshot_time = time.time() - SCREENSHOT_INTERVAL_SECONDS
    main_loop()