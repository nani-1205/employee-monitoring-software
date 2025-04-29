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
    data = request.json
    # --- ADDED LOGGING ---
    logger.info(f"Received /api/report data from {request.remote_addr}: {data}")
    # --- END ADDED LOGGING ---

    if not data or 'employee_id' not in data or 'timestamp_utc' not in data:
        # --- ADDED LOGGING ---
        logger.warning(f"/api/report missing required data. Received: {data}")
        # --- END ADDED LOGGING ---
        return jsonify({"status": "error", "message": "Missing required data (employee_id, timestamp_utc)"}), 400 # More specific message

    employee_id = data.get('employee_id')
    timestamp_str = data.get('timestamp_utc') # Expecting ISO 8601 format string
    active_window = data.get('active_window', 'N/A') # Optional
    idle_time = data.get('system_idle_time', 0) # Get idle time if sent

    try:
        # Parse timestamp string to datetime object (UTC)
        # --- ADDED LOGGING ---
        logger.info(f"Attempting to parse timestamp for /api/report: {timestamp_str}")
        # --- END ADDED LOGGING ---
        timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        # Ensure it's timezone-aware (UTC)
        timestamp = timestamp.replace(tzinfo=timezone.utc)
        # --- ADDED LOGGING ---
        logger.info(f"Successfully parsed timestamp for /api/report: {timestamp}")
        # --- END ADDED LOGGING ---
    except ValueError as e:
        # --- ADDED LOGGING ---
        logger.error(f"/api/report invalid timestamp format '{timestamp_str}': {e}")
        # --- END ADDED LOGGING ---
        return jsonify({"status": "error", "message": f"Invalid timestamp format: {timestamp_str}"}), 400 # Return invalid string

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
    employee_id = request.form.get('employee_id') # Use .get() for safety
    timestamp_str = request.form.get('timestamp_utc') # Use .get() for safety

    # --- ADDED LOGGING ---
    logger.info(f"Received /api/upload_screenshot form data: employee_id={employee_id}, timestamp_utc={timestamp_str}")
    if file:
        logger.info(f"Received /api/upload_screenshot file: filename='{file.filename}', content_type='{file.content_type}'")
    else:
         logger.warning(f"/api/upload_screenshot file object is empty/invalid") # Should not happen if 'screenshot' key exists
    # --- END ADDED LOGGING ---

    if not employee_id or not timestamp_str: # Check if .get() returned None
         logger.warning(f"/api/upload_screenshot missing required form data. Received: employee_id={employee_id}, timestamp_utc={timestamp_str}")
         return jsonify({"status": "error", "message": "Missing required form data (employee_id, timestamp_utc)"}), 400

    if file.filename == '':
        logger.warning(f"/api/upload_screenshot received empty filename.")
        return jsonify({"status": "error", "message": "No selected file"}), 400

    # Proceed only if file seems valid initially
    if file:
        try:
            # Parse timestamp string to datetime object (UTC)
            # --- ADDED LOGGING ---
            logger.info(f"Attempting to parse timestamp for /api/upload_screenshot: {timestamp_str}")
            # --- END ADDED LOGGING ---
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            # Ensure it's timezone-aware (UTC)
            timestamp = timestamp.replace(tzinfo=timezone.utc)
            # --- ADDED LOGGING ---
            logger.info(f"Successfully parsed timestamp for /api/upload_screenshot: {timestamp}")
            # --- END ADDED LOGGING ---
        except ValueError as e:
            # --- ADDED LOGGING ---
            logger.error(f"/api/upload_screenshot invalid timestamp format '{timestamp_str}': {e}")
            # --- END ADDED LOGGING ---
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

    # Fallback if file object was problematic initially (should be rare)
    logger.error(f"/api/upload_screenshot file processing failed unexpectedly for employee {employee_id}.")
    return jsonify({"status": "error", "message": "File processing failed"}), 500


# --- Web UI Routes (for Admin) ---
# (No changes needed in the Web UI routes below this line)
# ... (keep the login, logout, dashboard, employee_detail, serve_screenshot routes as they were) ...

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        error = None
        try:
            user = models.get_user(username)

            if user is None or not models.verify_password(user['password_hash'], password):
                error = 'Invalid username or password.'
            else:
                # Basic session management - Flask-Login is recommended for production
                session.clear()
                session['user_id'] = str(user['_id']) # Store MongoDB ObjectId as string
                session['username'] = user['username']
                logger.info(f"Admin user '{username}' logged in.")
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
def logout():
    username = session.get('username', 'Unknown user')
    session.clear()
    logger.info(f"User '{username}' logged out.")
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
@bp.route('/screenshots/<employee_id>/<filename>')
@login_required # Ensure only logged-in admins can access screenshot files directly
def serve_screenshot(employee_id, filename):
    """Serves a specific screenshot file."""
    # Basic path traversal prevention (Flask's send_from_directory helps)
    if '..' in employee_id or '/' in employee_id or '..' in filename or '/' in filename:
         logger.warning(f"Potential path traversal attempt: {employee_id}/{filename}")
         abort(404)

    screenshot_dir = os.path.join(config.SCREENSHOT_STORAGE_PATH, employee_id)
    # Check if file exists within the designated directory
    if not os.path.isfile(os.path.join(screenshot_dir, filename)): # Use isfile for better check
        logger.warning(f"Screenshot file not found or is not a file: {employee_id}/{filename}")
        abort(404)
    try:
        # send_from_directory is safer against path traversal
        return send_from_directory(screenshot_dir, filename)
    except FileNotFoundError:
         logger.error(f"File not found error during send_from_directory: {employee_id}/{filename}")
         abort(404)
    except Exception as e:
        logger.error(f"Error serving screenshot {employee_id}/{filename}: {e}", exc_info=True)
        abort(500)