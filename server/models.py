from pymongo import MongoClient, errors
from pymongo.server_api import ServerApi
from werkzeug.security import generate_password_hash, check_password_hash
import config # Assuming config.py is in the same directory
import os
import logging
from datetime import datetime, timezone # Make sure timezone is imported

# --- Configure Logger ---
# Use a shared logger name if desired, or just get the default logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
logger = logging.getLogger(__name__) # Get logger for this module

# --- Global Variables ---
db = None
client = None

# --- Database Connection ---
def connect_db():
    """Connects to MongoDB and returns the database object."""
    global client, db
    if db is None:
        if not config.MONGO_URI:
            logger.critical("CRITICAL: MONGO_URI is not set in config. Cannot connect to MongoDB.")
            raise ConnectionError("MongoDB URI not configured.")

        try:
            logger.info(f"Attempting to connect to MongoDB at {config.MONGO_HOST}:{config.MONGO_PORT}")
            client = MongoClient(
                config.MONGO_URI,
                server_api=ServerApi('1'), # Use modern Server API
                serverSelectionTimeoutMS=5000 # Timeout after 5 seconds
            )
            # The ismaster command is cheap and does not require auth. Check server availability.
            client.admin.command('ismaster')
            logger.info("MongoDB connection successful.")
            db = client[config.MONGO_DB_NAME]
            ensure_collections_and_indexes() # Ensure collections/indexes exist after connection
            # Ensure storage directories exist
            os.makedirs(config.SCREENSHOT_STORAGE_PATH, exist_ok=True)
            logger.info(f"Screenshot storage path ensured: {config.SCREENSHOT_STORAGE_PATH}")

        except errors.ConnectionFailure as e:
            logger.error(f"Could not connect to MongoDB: {e}")
            db = None # Ensure db is None if connection fails
            client = None
            raise ConnectionError(f"Failed to connect to MongoDB: {e}") from e
        except errors.ConfigurationError as e:
             logger.error(f"MongoDB configuration error (check username/password/authSource): {e}")
             db = None
             client = None
             raise ConnectionError(f"MongoDB configuration error: {e}") from e
        except Exception as e:
            logger.error(f"An unexpected error occurred during DB connection: {e}", exc_info=True)
            db = None
            client = None
            raise ConnectionError(f"Unexpected error connecting to DB: {e}") from e
    return db

def get_db():
    """Returns the database object, attempting to connect if necessary."""
    global db, client
    if db is None:
        try:
            connect_db()
        except ConnectionError:
            # Connection failed during connect_db(), db is already None
             logger.error("DB connection is not available (failed on connect).")
             return None # Explicitly return None

    # Optional: Ping the server before returning to ensure connection is live
    if client:
        try:
             # The ping command is cheap and does not require auth.
             client.admin.command('ping')
        except errors.ConnectionFailure:
             logger.warning("Reconnecting to MongoDB due to lost connection.")
             db = None # Reset db state
             client = None
             try:
                connect_db() # Attempt to reconnect
             except ConnectionError:
                  logger.error("DB reconnection failed.")
                  return None # Return None if reconnect fails
    elif db is None:
        # If client is None and db is None, connection likely failed initially
        logger.warning("Attempting to get DB, but connection was not established.")
        return None

    return db


def ensure_collections_and_indexes():
    """Checks if required collections exist and creates them if not. Also ensures indexes."""
    database = get_db() # Use get_db to ensure connection attempt
    if database is None:
        logger.error("Cannot ensure collections, DB connection not available.")
        return

    required_collections = ["users", "employees", "activity_logs", "screenshots"]
    try:
        existing_collections = database.list_collection_names()

        for col_name in required_collections:
            if col_name not in existing_collections:
                try:
                    database.create_collection(col_name)
                    logger.info(f"Created collection: '{col_name}'")
                except errors.CollectionInvalid:
                    logger.info(f"Collection '{col_name}' already exists.") # Should not happen with check above, but safe
                except Exception as e:
                    logger.error(f"Failed to create collection '{col_name}': {e}")

        # --- Ensure Indexes ---
        # Users (for Admin Login)
        database.users.create_index("username", unique=True)
        logger.info("Ensured index on users.username")

        # Employees
        database.employees.create_index("employee_id", unique=True)
        database.employees.create_index("name") # Index name for potential sorting/filtering
        logger.info("Ensured indexes on employees.employee_id and employees.name")

        # Activity Logs
        database.activity_logs.create_index([("employee_id", 1), ("timestamp", -1)]) # Compound index
        logger.info("Ensured index on activity_logs.{employee_id, timestamp}")

        # Screenshots
        database.screenshots.create_index([("employee_id", 1), ("timestamp", -1)]) # Compound index
        database.screenshots.create_index("screenshot_path") # Index path, but uniqueness might be enforced by filename logic
        logger.info("Ensured indexes on screenshots.{employee_id, timestamp} and screenshots.screenshot_path")

    except errors.OperationFailure as e:
         logger.error(f"Database operation failure during collection/index check: {e}. Check permissions.")
    except Exception as e:
         logger.error(f"Unexpected error during collection/index check: {e}", exc_info=True)


def setup_initial_admin_user():
    """Creates the initial admin user if one doesn't exist."""
    database = get_db()
    if database is None:
        logger.error("Cannot set up admin user, DB connection not available.")
        return

    try:
        if database.users.count_documents({"username": config.ADMIN_USERNAME}) == 0:
            hashed_password = generate_password_hash(config.ADMIN_PASSWORD, method='pbkdf2:sha256')
            database.users.insert_one({
                "username": config.ADMIN_USERNAME,
                "password_hash": hashed_password,
                "is_admin": True,
                "created_at": datetime.utcnow()
            })
            logger.info(f"Initial admin user '{config.ADMIN_USERNAME}' created.")
        else:
            logger.info(f"Admin user '{config.ADMIN_USERNAME}' already exists.")
    except errors.OperationFailure as e:
         logger.error(f"Database operation failure creating admin user: {e}. Check permissions.")
    except Exception as e:
        logger.error(f"Error setting up initial admin user: {e}", exc_info=True)

# --- Data Operations ---

# Employee Management
def add_or_update_employee(employee_id, name=None, last_seen=None):
    """Adds or updates employee info, including name and last seen time."""
    database = get_db()
    if database is None:
        logger.error(f"Cannot update employee {employee_id}, DB unavailable.")
        return None
    now = datetime.utcnow()
    # Use timestamp provided, or fallback to now if only updating name/first seen
    effective_last_seen = last_seen or now

    # Data to set on update or insert
    set_data = {"last_seen": effective_last_seen}
    if name: # Only include name if it's provided
        set_data["name"] = name

    # Data to set only on insert (first time seen)
    set_on_insert_data = {
        "employee_id": employee_id,
        "first_seen": effective_last_seen # Use the timestamp from the first contact
    }
    if name: # Also set name on first insert if provided
        set_on_insert_data["name"] = name

    logger.info(f"Upserting employee: ID={employee_id}, Name={name if name else '(no change)'}, LastSeen={effective_last_seen}")
    try:
        result = database.employees.update_one(
            {"employee_id": employee_id},
            {
                "$set": set_data,
                "$setOnInsert": set_on_insert_data
            },
            upsert=True
        )
        logger.debug(f"Upsert result for {employee_id}: Matched={result.matched_count}, Modified={result.modified_count}, UpsertedId={result.upserted_id}")
        return result
    except errors.OperationFailure as e:
         logger.error(f"Database operation failure updating employee {employee_id}: {e}. Check permissions.")
         return None
    except Exception as e:
         logger.error(f"Unexpected error updating employee {employee_id}: {e}", exc_info=True)
         return None


def get_employees():
    """Retrieves all employees, sorted by last seen."""
    database = get_db()
    if database is None:
        logger.error("Cannot get employees, DB unavailable.")
        return []
    try:
        return list(database.employees.find().sort("last_seen", -1))
    except Exception as e:
        logger.error(f"Error retrieving employees: {e}", exc_info=True)
        return []


def get_employee_by_id(employee_id):
    """Retrieves a single employee by their ID."""
    database = get_db()
    if database is None:
        logger.error(f"Cannot get employee {employee_id}, DB unavailable.")
        return None
    try:
        return database.employees.find_one({"employee_id": employee_id})
    except Exception as e:
        logger.error(f"Error retrieving employee {employee_id}: {e}", exc_info=True)
        return None

# Activity Log
def add_activity_log(employee_id, timestamp, active_window_title="N/A", system_idle_time=0):
    """Adds an activity log entry and updates the employee's last seen time."""
    database = get_db()
    if database is None:
        logger.error(f"Cannot add activity log for {employee_id}, DB unavailable.")
        return None

    log_entry = {
        "employee_id": employee_id,
        "timestamp": timestamp, # Expecting UTC datetime object
        "active_window_title": active_window_title,
        "system_idle_time_seconds": system_idle_time, # Store with clear name
        "received_at": datetime.utcnow()
    }
    try:
        result = database.activity_logs.insert_one(log_entry)
        # Also update employee's last seen status (without changing name here)
        add_or_update_employee(employee_id, last_seen=timestamp)
        logger.debug(f"Activity log added for {employee_id}, ID: {result.inserted_id}")
        return result.inserted_id
    except errors.OperationFailure as e:
         logger.error(f"Database operation failure adding activity log for {employee_id}: {e}. Check permissions.")
         return None
    except Exception as e:
         logger.error(f"Unexpected error adding activity log for {employee_id}: {e}", exc_info=True)
         return None


def get_activity_logs(employee_id, limit=100):
    """Retrieves recent activity logs for an employee."""
    database = get_db()
    if database is None:
        logger.error(f"Cannot get activity logs for {employee_id}, DB unavailable.")
        return []
    try:
        return list(database.activity_logs.find({"employee_id": employee_id})
                    .sort("timestamp", -1)
                    .limit(limit))
    except Exception as e:
        logger.error(f"Error retrieving activity logs for {employee_id}: {e}", exc_info=True)
        return []


# Screenshots
def add_screenshot_record(employee_id, timestamp, screenshot_filename):
    """Adds a screenshot metadata record and updates the employee's last seen time."""
    database = get_db()
    if database is None:
        logger.error(f"Cannot add screenshot record for {employee_id}, DB unavailable.")
        return None

    # Construct the relative path for storage in DB
    relative_path = os.path.join(employee_id, screenshot_filename) # Store employee_id/filename.png

    screenshot_entry = {
        "employee_id": employee_id,
        "timestamp": timestamp, # Expecting UTC datetime object
        "screenshot_path": relative_path, # Store relative path
        "received_at": datetime.utcnow()
    }
    try:
        result = database.screenshots.insert_one(screenshot_entry)
        # Also update employee's last seen status (without changing name here)
        add_or_update_employee(employee_id, last_seen=timestamp)
        logger.debug(f"Screenshot record added for {employee_id}, ID: {result.inserted_id}, Path: {relative_path}")
        return result.inserted_id
    except errors.OperationFailure as e:
        # Consider if you should delete the file if the DB record fails
         logger.error(f"Database operation failure adding screenshot record for {employee_id}: {e}. Check permissions.")
         return None
    except Exception as e:
         # Consider if you should delete the file if the DB record fails
         logger.error(f"Unexpected error adding screenshot record for {employee_id}: {e}", exc_info=True)
         return None


def get_screenshots(employee_id, limit=50):
    """Retrieves recent screenshot metadata for an employee."""
    database = get_db()
    if database is None:
        logger.error(f"Cannot get screenshots for {employee_id}, DB unavailable.")
        return []
    try:
        screenshots_data = list(database.screenshots.find({"employee_id": employee_id})
                            .sort("timestamp", -1)
                            .limit(limit))
        # Add URL path for template rendering
        for item in screenshots_data:
            # Creating a URL path relative to the '/screenshots/' route
            # Ensure screenshot_path is correctly formatted (no leading slashes needed if using os.path.join previously)
            item['url_path'] = url_for('main.serve_screenshot', employee_id=item['employee_id'], filename=os.path.basename(item['screenshot_path']))
            # Alternatively, build manually if url_for context isn't available here (less ideal):
            # item['url_path'] = f"/screenshots/{item['screenshot_path']}"
        return screenshots_data
    except Exception as e:
        logger.error(f"Error retrieving screenshots for {employee_id}: {e}", exc_info=True)
        return []


# User Authentication
def get_user(username):
    """Retrieves an admin user by username."""
    database = get_db()
    if database is None:
        logger.error(f"Cannot get user {username}, DB unavailable.")
        return None
    try:
        return database.users.find_one({"username": username})
    except Exception as e:
        logger.error(f"Error retrieving user {username}: {e}", exc_info=True)
        return None

def verify_password(stored_hash, provided_password):
    """Verifies a provided password against a stored hash."""
    return check_password_hash(stored_hash, provided_password)

# Helper function to generate URL for screenshots (needed in get_screenshots)
# Requires access to Flask's url_for, typically called within request context
from flask import url_for # Add this import at the top if not already there