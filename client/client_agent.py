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
SERVER_URL = "http://18.60.111.172:5000" # REPLACE WITH ACTUAL SERVER IP/DOMAIN
EMPLOYEE_ID = "EMP001" # REPLACE with a unique ID for each employee/installation
REPORT_INTERVAL_SECONDS = 60  # Send activity report every 60 seconds
SCREENSHOT_INTERVAL_SECONDS = 300 # Take screenshot every 5 minutes (300 seconds)
CLIENT_SECRET_KEY = "YOUR_STRONG_SHARED_SECRET_BETWEEN_SERVER_AND_CLIENTS" # REPLACE with the actual secret key from server config

# --- Logging Setup ---
# In a real scenario, log to a file, especially for background processes
# For testing within the EXE, we might not see console output easily.
# Logging to a file might be better for debugging deployed EXEs.
log_filename = f"monitor_agent_{EMPLOYEE_ID}.log" # Log file specific to employee
log_filepath = os.path.join(os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(__file__), log_filename)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filepath), # Log to a file
        logging.StreamHandler(sys.stdout) # Also log to stdout (visible if not --noconsole)
    ]
)
logger = logging.getLogger(__name__)
logger.info(f"Logging initialized. Log file: {log_filepath}")

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
    # Ensure microseconds are included for potential granularity needs, then format
    now_utc = datetime.now(timezone.utc)
    # Format explicitly including 'T' separator and 'Z' for UTC
    iso_string = now_utc.strftime('%Y-%m-%dT%H:%M:%SZ')
    logger.debug(f"Generated timestamp: {iso_string}") # Debug log level
    return iso_string

def send_activity_report():
    """Collects and sends activity data to the server."""
    global EMPLOYEE_ID, SERVER_URL, CLIENT_SECRET_KEY
    timestamp = get_utc_timestamp_iso()
    active_window = "Error"
    idle_time = -1
    try:
        active_window = get_active_window_title()
        idle_time = get_idle_time()
        logger.info(f"Collected activity: window='{active_window}', idle={idle_time}s")
    except Exception as e:
        logger.error(f"Error getting system info: {e}")

    payload = {
        "employee_id": EMPLOYEE_ID,
        "timestamp_utc": timestamp,
        "active_window": active_window,
        "system_idle_time": int(idle_time) # Send as integer seconds
    }
    headers = {'X-Client-Secret': CLIENT_SECRET_KEY}

    # --- ADDED LOGGING ---
    logger.info(f"Sending /api/report payload: {payload}")
    # --- END ADDED LOGGING ---

    try:
        url = f"{SERVER_URL}/api/report"
        logger.info(f"Posting activity report to {url}")
        response = requests.post(url, json=payload, headers=headers, timeout=15) # 15 sec timeout
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        logger.info(f"Activity report sent successfully. Status: {response.status_code}, Response: {response.text}") # Log response text
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send activity report: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred sending activity report: {e}")

def take_and_send_screenshot():
    """Takes a screenshot and uploads it to the server."""
    global EMPLOYEE_ID, SERVER_URL, CLIENT_SECRET_KEY
    timestamp_dt = datetime.now(timezone.utc) # Get datetime object
    # Format explicitly including 'T' separator and 'Z' for UTC
    timestamp_iso = timestamp_dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    logger.debug(f"Generated screenshot timestamp: {timestamp_iso}") # Debug log level

    try:
        with mss.mss() as sct:
            # Capture the primary monitor
            monitor = sct.monitors[1] # Index 1 is usually the primary monitor
            logger.info(f"Capturing screenshot from monitor: {monitor}")
            sct_img = sct.grab(monitor)

            # Convert to PNG bytes in memory
            img_bytes = mss.tools.to_png(sct_img.rgb, sct_img.size)
            img_file = io.BytesIO(img_bytes)
            logger.info(f"Screenshot taken, size: {len(img_bytes)} bytes")

        # Prepare data for POST request (multipart/form-data)
        screenshot_filename = f"{timestamp_dt.strftime('%Y%m%d_%H%M%S')}.png" # Simple filename
        files = {'screenshot': (screenshot_filename, img_file, 'image/png')}
        payload = {
            'employee_id': EMPLOYEE_ID,
            'timestamp_utc': timestamp_iso
        }
        headers = {'X-Client-Secret': CLIENT_SECRET_KEY}

        # --- ADDED LOGGING ---
        logger.info(f"Sending /api/upload_screenshot payload: {payload}, filename: {screenshot_filename}")
        # --- END ADDED LOGGING ---

        url = f"{SERVER_URL}/api/upload_screenshot"
        logger.info(f"Uploading screenshot to {url}")
        response = requests.post(url, files=files, data=payload, headers=headers, timeout=30) # 30 sec timeout for upload
        response.raise_for_status()
        logger.info(f"Screenshot uploaded successfully. Status: {response.status_code}, Response: {response.text}") # Log response text
        return True # Indicate success

    except (mss.ScreenShotError, IndexError) as e:
        logger.error(f"Failed to take screenshot: {e}")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to upload screenshot: {e}")
        # Log server response if available
        if e.response is not None:
             logger.error(f"Server response: Status={e.response.status_code}, Text={e.response.text}")
        return False
    except Exception as e:
        logger.error(f"An unexpected error occurred during screenshot process: {e}")
        return False


# --- Main Loop ---
def main_loop():
    global last_screenshot_time
    logger.info(f"Client agent starting...")
    logger.info(f"Employee ID: {EMPLOYEE_ID}")
    logger.info(f"Server URL: {SERVER_URL}")
    logger.info(f"Report Interval: {REPORT_INTERVAL_SECONDS}s, Screenshot Interval: {SCREENSHOT_INTERVAL_SECONDS}s")

    # Initialize last screenshot time correctly relative to current time
    last_screenshot_time = time.time() - SCREENSHOT_INTERVAL_SECONDS # Ensure first screenshot runs soon if needed

    while True:
        current_time = time.time()
        logger.debug(f"Main loop iteration. Current time: {current_time}") # Debug log level

        try:
            # Send Activity Report Thread
            logger.debug("Starting activity report thread.")
            activity_thread = threading.Thread(target=send_activity_report, daemon=True)
            activity_thread.start()

            # Check if it's time for a screenshot
            time_since_last_screenshot = current_time - last_screenshot_time
            logger.debug(f"Time since last screenshot: {time_since_last_screenshot:.2f}s")
            if time_since_last_screenshot >= SCREENSHOT_INTERVAL_SECONDS:
                logger.info("Screenshot interval reached. Starting screenshot thread.")
                 # Run in a separate thread
                screenshot_thread = threading.Thread(target=take_and_send_screenshot, daemon=True)
                screenshot_thread.start()
                last_screenshot_time = current_time # Update time
            else:
                logger.debug("Screenshot interval not reached.")

            # Wait before next cycle
            # Calculate sleep time based on the *report* interval.
            # This ensures reports are sent roughly on schedule.
            # Screenshots happen independently when their timer is up.
            # (Could be more sophisticated with timers, but this is simple)
            sleep_duration = REPORT_INTERVAL_SECONDS
            logger.debug(f"Sleeping for {sleep_duration} seconds.")
            time.sleep(sleep_duration)

        except KeyboardInterrupt:
            logger.info("Client agent stopping due to KeyboardInterrupt.")
            break
        except Exception as e:
            logger.error(f"CRITICAL ERROR in main loop: {e}", exc_info=True)
            # Avoid rapid looping on error
            logger.info("Waiting 60 seconds after critical error before retrying loop.")
            time.sleep(60)

if __name__ == "__main__":
    main_loop()