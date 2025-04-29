from pymongo import MongoClient, errors
from pymongo.server_api import ServerApi
from werkzeug.security import generate_password_hash, check_password_hash
import config
import os
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Global Variables ---
db = None
client = None

# --- Database Connection ---
def connect_db():
    """Connects to MongoDB and returns the database object."""
    global client, db
    if db is None:
        try:
            logger.info(f"Attempting to connect to MongoDB at {config.MONGO_HOST}:{config.MONGO_PORT}")
            client = MongoClient(
                config.MONGO_URI,
                server_api=ServerApi('1'), # Use modern Server API
                serverSelectionTimeoutMS=5000 # Timeout after 5 seconds
            )
            # The ismaster command is cheap and does not require auth.
            client.admin.command('ismaster')
            logger.info("MongoDB connection successful.")
            db = client[config.MONGO_DB_NAME]
            ensure_collections_and_indexes() # Ensure collections exist after connection
            # Create storage directories if they don't exist
            os.makedirs(config.SCREENSHOT_STORAGE_PATH, exist_ok=True)
            logger.info(f"Screenshot storage path ensured: {config.SCREENSHOT_STORAGE_PATH}")

        except errors.ConnectionFailure as e:
            logger.error(f"Could not connect to MongoDB: {e}")
            db = None # Ensure db is None if connection fails
            raise ConnectionError(f"Failed to connect to MongoDB: {e}") from e
        except errors.ConfigurationError as e:
             logger.error(f"MongoDB configuration error (check username/password/authSource): {e}")
             db = None
             raise ConnectionError(f"MongoDB configuration error: {e}") from e
        except Exception as e:
            logger.error(f"An unexpected error occurred during DB connection: {e}")
            db = None
            raise ConnectionError(f"Unexpected error connecting to DB: {e}") from e
    return db

def get_db():
    """Returns the database object, connecting if necessary."""
    if db is None:
        connect_db()
    # Optional: Ping the server before returning to ensure connection is live
    try:
         # The ping command is cheap and does not require auth.
         client.admin.command('ping')
    except errors.ConnectionFailure:
         logger.warning("Reconnecting to MongoDB due to lost connection.")
         connect_db() # Attempt to reconnect
    return db


def ensure_collections_and_indexes():
    """Checks if required collections exist and creates them if not. Also ensures indexes."""
    database = get_db()
    if database is None:
        logger.error("Cannot ensure collections, DB connection not available.")
        return

    required_collections = ["users", "employees", "activity_logs", "screenshots"]
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

    # Employees
    database.employees.create_index("employee_id", unique=True)
    database.employees.create_index("name")

    # Activity Logs
    database.activity_logs.create_index([("employee_id", 1), ("timestamp", -1)]) # Compound index

    # Screenshots
    database.screenshots.create_index([("employee_id", 1), ("timestamp", -1)]) # Compound index
    database.screenshots.create_index("screenshot_path", unique=True)
    logger.info("Ensured necessary indexes exist.")


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
    except Exception as e:
        logger.error(f"Error setting up initial admin user: {e}")

# --- Data Operations ---

# Employee Management
def add_or_update_employee(employee_id, name=None, last_seen=None):
    database = get_db()
    if database is None: return None
    now = datetime.utcnow()
    update_data = {"last_seen": last_seen or now}
    if name:
        update_data["name"] = name

    result = database.employees.update_one(
        {"employee_id": employee_id},
        {"$set": update_data, "$setOnInsert": {"employee_id": employee_id, "first_seen": now}},
        upsert=True
    )
    return result

def get_employees():
    database = get_db()
    if database is None: return []
    return list(database.employees.find().sort("last_seen", -1))

def get_employee_by_id(employee_id):
    database = get_db()
    if database is None: return None
    return database.employees.find_one({"employee_id": employee_id})

# Activity Log
def add_activity_log(employee_id, timestamp, active_window_title="N/A", system_idle_time=0):
    database = get_db()
    if database is None: return None
    log_entry = {
        "employee_id": employee_id,
        "timestamp": timestamp, # Expecting datetime object
        "active_window_title": active_window_title,
        "system_idle_time_seconds": system_idle_time, # Placeholder
        "received_at": datetime.utcnow()
    }
    result = database.activity_logs.insert_one(log_entry)
    # Also update employee's last seen status
    add_or_update_employee(employee_id, last_seen=timestamp)
    return result.inserted_id

def get_activity_logs(employee_id, limit=100):
    database = get_db()
    if database is None: return []
    return list(database.activity_logs.find({"employee_id": employee_id})
                .sort("timestamp", -1)
                .limit(limit))

# Screenshots
def add_screenshot_record(employee_id, timestamp, screenshot_filename):
    database = get_db()
    if database is None: return None

    # Construct the relative path for storage in DB
    relative_path = os.path.join(employee_id, screenshot_filename)

    screenshot_entry = {
        "employee_id": employee_id,
        "timestamp": timestamp, # Expecting datetime object
        "screenshot_path": relative_path, # Store relative path
        "received_at": datetime.utcnow()
    }
    result = database.screenshots.insert_one(screenshot_entry)
     # Also update employee's last seen status
    add_or_update_employee(employee_id, last_seen=timestamp)
    return result.inserted_id

def get_screenshots(employee_id, limit=50):
    database = get_db()
    if database is None: return []
    screenshots_data = list(database.screenshots.find({"employee_id": employee_id})
                           .sort("timestamp", -1)
                           .limit(limit))
    # Add full URL or relative path for template rendering
    for item in screenshots_data:
        # Creating a URL path relative to the 'static' or a dedicated 'media' route
        item['url_path'] = f"/screenshots/{item['screenshot_path']}"
    return screenshots_data

# User Authentication
def get_user(username):
    database = get_db()
    if database is None: return None
    return database.users.find_one({"username": username})

def verify_password(stored_hash, provided_password):
    return check_password_hash(stored_hash, provided_password)