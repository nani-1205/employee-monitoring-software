from flask import (
    Blueprint, render_template, request, jsonify, redirect, url_for,
    flash, session, send_from_directory, abort
)
from werkzeug.utils import secure_filename
import os
import models  # Use models.logger
import config
from datetime import datetime, timezone
import functools # For login_required decorator
import logging # Good practice to have it explicitly, though using models.logger

# Use the logger configured in models.py
logger = models.logger

# --- Helper for Authentication ---
def login_required(view):
    """View decorator that redirects anonymous users to the login page."""
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if 'user_id' not in session:
            return redirect(url_for('main.login'))
        # You might want to fetch the user from DB here to ensure they still exist/are active
        return view(**kwargs)
    return wrapped_view

def client_auth_required(view):
    """Decorator to check for a valid client secret key in headers."""
    @functools.wraps(view)
    def wrapped_view(*args, **kwargs):
        client_key = request.headers.get('X-Client-Secret')
        if not client_key or client_key != config.CLIENT_SECRET_KEY:
            logger.warning(f"Unauthorized client access attempt from {request.remote_addr} - Invalid/Missing Secret Key") # Added reason
            return jsonify({"status": "error", "message": "Unauthorized client"}), 401
        return view(*args, **kwargs)
    return wrapped_view

bp = Blueprint('main', __name__)

# --- API Endpoints (for Clients) ---

@bp.route('/api/report', methods=['POST'])
@client_auth_required
def api_report_activity():
    """Receives activity data from the client agent."""
    # Check if content type is application/json
    if not request.is_json:
        logger.warning(f"/api/report error from {request.remote_addr}: Content-Type is not application/json.")
        return jsonify({"status": "error", "message": "Invalid Content-Type, expected application/json"}), 415 # Unsupported Media Type

    data = request.get_json() # Use get_json() for better error handling if not JSON
    if data is None:
        logger.warning(f"/api/report error from {request.remote_addr}: Failed to decode JSON.")
        return jsonify({"status": "error", "message": "Invalid JSON data"}), 400

    logger.info(f"Received /api/report data from {request.remote_addr}: {data}")

    if 'employee_id' not in data or 'timestamp_utc' not in data:
        logger.warning(f"/api/report missing required data. Received: {data}")
        return jsonify({"status": "error", "message": "Missing required data (employee_id, timestamp_utc)"}), 400

    employee_id = data.get('employee_id')
    timestamp_str = data.get('timestamp_utc') # Expecting ISO 8601 format string like YYYY-MM-DDTHH:MM:SS+00:00
    active_window = data.get('active_window', 'N/A') # Optional
    idle_time = data.get('system_idle_time', 0) # Get idle time if sent

    try:
        # Parse timestamp string to datetime object (UTC)
        logger.info(f"Attempting to parse timestamp for /api/report: {timestamp_str}")
        # --- REMOVED .replace("Z", "+00:00") ---
        timestamp = datetime.fromisoformat(timestamp_str)
        # --- Ensure timezone aware if parsing somehow resulted in naive (shouldn't with offset) ---
        if timestamp.tzinfo is None:
             logger.warning(f"Parsed timestamp '{timestamp_str}' resulted in naive datetime. Assuming UTC.")
             timestamp = timestamp.replace(tzinfo=timezone.utc)
        elif timestamp.tzinfo != timezone.utc:
             logger.warning(f"Parsed timestamp '{timestamp_str}' has non-UTC timezone ({timestamp.tzinfo}). Converting to UTC.")
             timestamp = timestamp.astimezone(timezone.utc)

        logger.info(f"Successfully parsed timestamp for /api/report: {timestamp}")
    except (ValueError, TypeError) as e: # Catch TypeError if timestamp_str is not a string
        logger.error(f"/api/report invalid timestamp format or type '{timestamp_str}': {e}")
        return jsonify({"status": "error", "message": f"Invalid timestamp format: {timestamp_str}"}), 400

    try:
        # Add activity log to the database
        models.add_activity_log(employee_id, timestamp, active_window_title=active_window, system_idle_time=idle_time)
        logger.info(f"Received activity report successfully processed for {employee_id}") # Changed log message
        return jsonify({"status": "success", "message": "Activity logged"}), 200
    except ConnectionError as e:
         logger.error(f"API DB connection error during /api/report: {e}")
         return jsonify({"status": "error", "message": "Database connection error"}), 500
    except Exception as e:
        logger.error(f"Error processing activity report for {employee_id}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Internal server error"}), 500


@bp.route('/api/upload_screenshot', methods=['POST'])
@client_auth_required
def api_upload_screenshot():
    """Receives screenshot file and metadata from the client agent."""
    logger.info(f"Received POST request on /api/upload_screenshot from {request.remote_addr}") # Log entry point

    if 'screenshot' not in request.files:
        logger.warning(f"/api/upload_screenshot error: 'screenshot' file part missing in request.files")
        return jsonify({"status": "error", "message": "No screenshot file part"}), 400

    file = request.files['screenshot']
    # Use request.form.get for safety, in case keys are missing
    employee_id = request.form.get('employee_id')
    timestamp_str = request.form.get('timestamp_utc')

    logger.info(f"Received /api/upload_screenshot form data: employee_id={employee_id}, timestamp_utc={timestamp_str}")
    if file:
        logger.info(f"Received /api/upload_screenshot file: filename='{file.filename}', content_type='{file.content_type}'")
    else:
         logger.warning(f"/api/upload_screenshot file object is empty/invalid")

    if not employee_id or not timestamp_str:
         logger.warning(f"/api/upload_screenshot missing required form data. Received: employee_id={employee_id}, timestamp_utc={timestamp_str}")
         return jsonify({"status": "error", "message": "Missing required form data (employee_id, timestamp_utc)"}), 400

    if not file or file.filename == '':
        logger.warning(f"/api/upload_screenshot received empty filename or invalid file object.")
        return jsonify({"status": "error", "message": "No valid file selected/sent"}), 400

    # Proceed only if file seems valid
    try:
        # Parse timestamp string to datetime object (UTC)
        logger.info(f"Attempting to parse timestamp for /api/upload_screenshot: {timestamp_str}")
        # --- REMOVED .replace("Z", "+00:00") ---
        timestamp = datetime.fromisoformat(timestamp_str)
        # --- Ensure timezone aware if parsing somehow resulted in naive ---
        if timestamp.tzinfo is None:
             logger.warning(f"Parsed timestamp '{timestamp_str}' resulted in naive datetime. Assuming UTC.")
             timestamp = timestamp.replace(tzinfo=timezone.utc)
        elif timestamp.tzinfo != timezone.utc:
             logger.warning(f"Parsed timestamp '{timestamp_str}' has non-UTC timezone ({timestamp.tzinfo}). Converting to UTC.")
             timestamp = timestamp.astimezone(timezone.utc)

        logger.info(f"Successfully parsed timestamp for /api/upload_screenshot: {timestamp}")
    except (ValueError, TypeError) as e: # Catch TypeError if timestamp_str is not a string
        logger.error(f"/api/upload_screenshot invalid timestamp format or type '{timestamp_str}': {e}")
        return jsonify({"status": "error", "message": f"Invalid timestamp format: {timestamp_str}"}), 400

    # Create a secure filename (timestamp + original extension)
    file_ext = os.path.splitext(file.filename)[1] if file.filename else '.png' # Default extension
    # Use timestamp for filename to ensure uniqueness and order
    filename = secure_filename(f"{timestamp.strftime('%Y%m%d_%H%M%S_%f')}{file_ext}")

    # Create employee-specific directory if it doesn't exist
    employee_dir = os.path.join(config.SCREENSHOT_STORAGE_PATH, employee_id)
    try:
        os.makedirs(employee_dir, exist_ok=True)
    except OSError as e:
            logger.error(f"Error creating directory {employee_dir}: {e}")
            return jsonify({"status": "error", "message": "Could not create storage directory"}), 500

    save_path = os.path.join(employee_dir, filename)

    try:
        file.save(save_path)
        logger.info(f"Screenshot saved for {employee_id} at {save_path}")

        # Add screenshot metadata record to the database
        models.add_screenshot_record(employee_id, timestamp, filename) # Store just filename

        return jsonify({"status": "success", "message": "Screenshot uploaded"}), 200
    except ConnectionError as e:
            logger.error(f"API DB connection error during /api/upload_screenshot: {e}")
            # Consider deleting the saved file if DB operation fails
            if os.path.exists(save_path):
                try:
                    os.remove(save_path)
                    logger.info(f"Removed partially saved file due to DB error: {save_path}")
                except OSError as remove_err:
                        logger.error(f"Error removing file {save_path} after DB error: {remove_err}")
            return jsonify({"status": "error", "message": "Database connection error"}), 500
    except Exception as e:
        logger.error(f"Error processing screenshot upload for {employee_id}: {e}", exc_info=True)
        # Clean up saved file if error occurs
        if os.path.exists(save_path):
            try:
                os.remove(save_path)
                logger.info(f"Removed partially saved file due to processing error: {save_path}")
            except OSError as remove_err:
                logger.error(f"Error removing file {save_path} after processing error: {remove_err}")
        return jsonify({"status": "error", "message": "Internal server error during upload"}), 500

# --- Web UI Routes (for Admin) ---
# (No changes needed in the Web UI routes below this line)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username') # Use .get for safety
        password = request.form.get('password')
        error = None

        if not username or not password:
             error = 'Username and password are required.'
             flash(error)
             return render_template('login.html')

        try:
            user = models.get_user(username)

            if user is None or not models.verify_password(user['password_hash'], password):
                error = 'Invalid username or password.'
            else:
                # Basic session management - Flask-Login is recommended for production
                session.clear()
                session['user_id'] = str(user['_id']) # Store MongoDB ObjectId as string
                session['username'] = user['username']
                logger.info(f"Admin user '{username}' logged in from {request.remote_addr}.")
                return redirect(url_for('main.dashboard'))

        except ConnectionError as e:
            error = "Database connection error during login."
            logger.error(f"Login DB connection error: {e}")
        except Exception as e:
             error = "An unexpected error occurred during login."
             logger.error(f"Login error: {e}", exc_info=True)

        flash(error)

    # If already logged in, redirect to dashboard
    if 'user_id' in session:
         return redirect(url_for('main.dashboard'))

    return render_template('login.html')

@bp.route('/logout')
@login_required # Make sure user is logged in to log out
def logout():
    username = session.get('username', 'Unknown user')
    session.clear()
    logger.info(f"User '{username}' logged out from {request.remote_addr}.")
    flash('You were successfully logged out.')
    return redirect(url_for('main.login'))

@bp.route('/')
@bp.route('/dashboard')
@login_required
def dashboard():
    """Shows the main dashboard with a list of employees."""
    try:
        employees = models.get_employees()
        return render_template('dashboard.html', employees=employees)
    except ConnectionError as e:
        logger.error(f"Dashboard DB connection error: {e}")
        flash("Error connecting to the database to retrieve employee list.", "error")
        return render_template('dashboard.html', employees=[]) # Render with empty list on error
    except Exception as e:
        logger.error(f"Error loading dashboard: {e}", exc_info=True)
        flash("An unexpected error occurred while loading the dashboard.", "error")
        return render_template('dashboard.html', employees=[])

@bp.route('/employee/<employee_id>')
@login_required
def employee_detail(employee_id):
    """Shows details, activity logs, and screenshots for a specific employee."""
    try:
        # Sanitize employee_id? Basic check:
        if not employee_id or not employee_id.isalnum(): # Allow only alphanumeric IDs? Adjust as needed.
             logger.warning(f"Invalid employee_id format requested: {employee_id}")
             flash('Invalid employee ID format.', 'error')
             return redirect(url_for('main.dashboard'))

        employee = models.get_employee_by_id(employee_id)
        if not employee:
            flash(f'Employee with ID {employee_id} not found.', 'warning')
            return redirect(url_for('main.dashboard'))

        activity_logs = models.get_activity_logs(employee_id, limit=200) # Get recent logs
        screenshots = models.get_screenshots(employee_id, limit=100) # Get recent screenshots

        return render_template('employee_detail.html',
                               employee=employee,
                               activity_logs=activity_logs,
                               screenshots=screenshots)
    except ConnectionError as e:
        logger.error(f"Employee Detail DB connection error: {e}")
        flash(f"Error connecting to the database for employee {employee_id}.", "error")
        return redirect(url_for('main.dashboard'))
    except Exception as e:
        logger.error(f"Error loading employee detail for {employee_id}: {e}", exc_info=True)
        flash(f"An unexpected error occurred loading details for {employee_id}.", "error")
        return redirect(url_for('main.dashboard'))


# --- Route for serving stored screenshots ---
@bp.route('/screenshots/<path:employee_id>/<path:filename>') # Use path converter for more flexibility if needed
@login_required # Ensure only logged-in admins can access screenshot files directly
def serve_screenshot(employee_id, filename):
    """Serves a specific screenshot file."""
    # Path traversal check (already partially handled by werkzeug/flask)
    # secure_filename can help sanitize filename, but employee_id needs care
    if '..' in employee_id or employee_id.startswith('/'):
         logger.warning(f"Potential path traversal attempt in employee_id: {employee_id}")
         abort(404)
    if '..' in filename or filename.startswith('/'):
        logger.warning(f"Potential path traversal attempt in filename: {filename}")
        abort(404)


    # Construct the absolute path robustly
    screenshot_dir = os.path.abspath(os.path.join(config.SCREENSHOT_STORAGE_PATH, employee_id))

    # Security check: Ensure the requested path is *within* the allowed base storage path
    if not screenshot_dir.startswith(os.path.abspath(config.SCREENSHOT_STORAGE_PATH)):
        logger.error(f"Security Alert: Attempt to access path outside designated storage: {screenshot_dir}")
        abort(403) # Forbidden


    file_path = os.path.join(screenshot_dir, filename)

    # Check if file exists and is actually a file
    if not os.path.isfile(file_path):
        logger.warning(f"Screenshot file not found or is not a file: {file_path}")
        abort(404)
    try:
        logger.debug(f"Serving screenshot: {file_path}")
        return send_from_directory(screenshot_dir, filename)
    except FileNotFoundError:
         # This shouldn't happen if os.path.isfile passed, but handle defensively
         logger.error(f"File not found error during send_from_directory (unexpected): {file_path}")
         abort(404)
    except Exception as e:
        logger.error(f"Error serving screenshot {file_path}: {e}", exc_info=True)
        abort(500)