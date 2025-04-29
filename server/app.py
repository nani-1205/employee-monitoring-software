from flask import Flask
import config
import models
import routes
import logging

def create_app():
    app = Flask(__name__)
    app.config.from_object(config)

    # Set up logging
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(name)s: %(message)s')
    app.logger.setLevel(logging.INFO) # Use Flask's logger instance

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
            # Depending on requirements, you might want to exit here or allow Flask to start
            # but log critical errors for routes needing the DB.
        except Exception as e:
             app.logger.critical(f"CRITICAL: An unexpected error occurred during DB setup: {e}", exc_info=True)


    # --- Register Blueprints ---
    app.register_blueprint(routes.bp)

    # Add a simple health check endpoint
    @app.route('/health')
    def health_check():
        # Optional: Add a quick DB ping check here too
        try:
            models.client.admin.command('ping')
            db_status = "connected"
        except Exception:
            db_status = "disconnected"
        return {"status": "ok", "db_status": db_status}

    app.logger.info("Flask application created and configured.")
    return app

if __name__ == '__main__':
    app = create_app()
    # Use host='0.0.0.0' to make it accessible externally (within network)
    # Use debug=True only for development (enables auto-reloader and debugger)
    # In production, use a proper WSGI server like Gunicorn or uWSGI
    app.run(host='0.0.0.0', port=5000, debug=app.config['DEBUG'])