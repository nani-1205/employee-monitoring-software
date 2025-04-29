from flask import Flask
import config
import models
import routes
import logging
from datetime import datetime, timezone # Import timezone
import pytz # Import pytz

# --- Define IST Timezone ---
IST = pytz.timezone('Asia/Kolkata')

# --- Custom Jinja Filter for IST Formatting ---
def format_datetime_ist(dt_utc):
    """Converts a UTC datetime object to a formatted IST string."""
    if dt_utc is None:
        return "N/A"
    if not isinstance(dt_utc, datetime):
        return str(dt_utc) # Return as string if not a datetime object

    try:
        # Ensure the input datetime is UTC aware
        if dt_utc.tzinfo is None:
            # If naive, assume it's UTC (as stored in DB)
            dt_utc = dt_utc.replace(tzinfo=timezone.utc)
        elif dt_utc.tzinfo != timezone.utc:
            # If aware but not UTC, convert to UTC first
             dt_utc = dt_utc.astimezone(timezone.utc)

        # Convert UTC datetime to IST
        dt_ist = dt_utc.astimezone(IST)
        # Format as desired (e.g., including AM/PM and timezone abbr)
        return dt_ist.strftime('%Y-%m-%d %I:%M:%S %p %Z') # Example: 2024-04-29 07:30:00 PM IST
    except Exception as e:
        # Log error and return original representation or an error string
        models.logger.error(f"Error formatting datetime to IST: {e}", exc_info=True)
        return str(dt_utc) # Fallback


def create_app():
    app = Flask(__name__)
    app.config.from_object(config)

    # Set up logging
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(name)s: %(message)s')
    # Use Flask's logger instance after configuration
    # Note: Consider using Flask's native logging configuration methods for more complex setups
    # https://flask.palletsprojects.com/en/2.3.x/logging/
    if not app.debug: # Don't log basic requests to file/stdout in production by default via basicConfig
        log_level = logging.INFO
        # Configure more robust logging here for production if needed
    else:
        log_level = logging.DEBUG # Show more detail in debug mode

    # Ensure our models logger uses Flask's config level
    models.logger.setLevel(log_level)
    app.logger.setLevel(log_level)


    # --- Database Initialization ---
    with app.app_context():
        try:
            # Connect to DB and ensure collections/indexes exist on startup
            models.connect_db()
            # Create initial admin user if needed (idempotent)
            models.setup_initial_admin_user()
            app.logger.info("Database connection established and initial setup checked.")
        except ConnectionError as e:
            app.logger.critical(f"CRITICAL: Failed to connect to MongoDB on startup: {e}. Application might not function correctly.")
        except Exception as e:
             app.logger.critical(f"CRITICAL: An unexpected error occurred during DB setup: {e}", exc_info=True)


    # --- Register Custom Jinja Filter ---
    app.jinja_env.filters['to_ist'] = format_datetime_ist
    app.logger.info("Registered 'to_ist' Jinja2 filter.")


    # --- Register Blueprints ---
    app.register_blueprint(routes.bp)

    # Add a simple health check endpoint
    @app.route('/health')
    def health_check():
        # Optional: Add a quick DB ping check here too
        db_status = "unknown"
        try:
            if models.client:
                 models.client.admin.command('ping')
                 db_status = "connected"
            else:
                 db_status = "disconnected (no client)"
        except Exception as e:
            db_status = f"error ({e})"
        return jsonify({"status": "ok", "db_status": db_status})

    app.logger.info("Flask application created and configured.")
    return app

if __name__ == '__main__':
    app = create_app()
    # Use host='0.0.0.0' to make it accessible externally (within network)
    # Use debug=True only for development (enables auto-reloader and debugger)
    # In production, use a proper WSGI server like Gunicorn or uWSGI
    # Debug mode is read from config.DEBUG now
    app.run(host='0.0.0.0', port=5000, debug=app.config['DEBUG'])