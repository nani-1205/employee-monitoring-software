import os
from dotenv import load_dotenv
from urllib.parse import quote_plus # Import quote_plus for URL encoding

# Load environment variables from a .env file if present
# Place the .env file in the same directory as this config.py
load_dotenv()

# --- Core Settings ---
# Generate a strong secret key: python -c 'import secrets; print(secrets.token_hex(16))'
# Store this in your .env file
SECRET_KEY = os.getenv("SECRET_KEY", "a_very_insecure_default_secret_key_CHANGE_ME")
# Set to False in production! Use .env file to set FLASK_DEBUG=False
DEBUG = os.getenv("FLASK_DEBUG", "True").lower() in ("true", "1", "t")

# --- Database Settings (MongoDB) ---
# Get raw values from environment/.env file
MONGO_HOST = os.getenv("MONGO_HOST", "localhost")
MONGO_PORT = int(os.getenv("MONGO_PORT", "27017"))
MONGO_USERNAME = os.getenv("MONGO_USERNAME") # Expecting username in .env
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD") # Expecting password in .env
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "employee_monitor")
MONGO_AUTH_DB = os.getenv("MONGO_AUTH_DB", "admin") # DB where the user is defined

# --- Construct MongoDB URI ---
MONGO_URI = None # Initialize MONGO_URI

# Check if required credentials are provided
if not MONGO_USERNAME:
    print("WARNING: MONGO_USERNAME environment variable not set.")
if not MONGO_PASSWORD:
    print("WARNING: MONGO_PASSWORD environment variable not set.")

# Construct the URI only if username and password are provided
# Apply URL encoding using quote_plus
if MONGO_USERNAME and MONGO_PASSWORD:
    try:
        MONGO_URI = (
            f"mongodb://{quote_plus(MONGO_USERNAME)}:{quote_plus(MONGO_PASSWORD)}"
            f"@{MONGO_HOST}:{MONGO_PORT}/{MONGO_DB_NAME}?authSource={MONGO_AUTH_DB}"
        )
        print(f"MongoDB URI constructed with authentication for user '{MONGO_USERNAME}'")
    except Exception as e:
         print(f"ERROR: Failed to construct MongoDB URI: {e}")
         # Optionally raise an error here if URI construction fails critically
         # raise ValueError(f"Failed to construct MongoDB URI: {e}") from e
else:
    # Handle case without authentication (or raise error if auth is mandatory)
    print("WARNING: Attempting to construct MongoDB URI without authentication (username or password missing).")
    # If your setup requires auth, you should probably raise an error here instead.
    # raise ValueError("MongoDB username and password are required but not set in environment.")
    MONGO_URI = f"mongodb://{MONGO_HOST}:{MONGO_PORT}/{MONGO_DB_NAME}"


# --- Storage Settings ---
# Define the base directory for the server application
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCREENSHOT_STORAGE_PATH = os.path.join(BASE_DIR, "storage", "screenshots")


# --- Admin Credentials (For initial setup or fallback) ---
# Store these in your .env file
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
# Ensure the password loaded from .env is treated as a string
ADMIN_PASSWORD = str(os.getenv("ADMIN_PASSWORD", "password")) # CHANGE THIS in .env! Hash this in production DB.


# --- Client Settings ---
# Store this in your .env file and ensure it matches the client agent
CLIENT_SECRET_KEY = os.getenv("CLIENT_SECRET_KEY", "default_client_secret_CHANGE_ME") # Change this!


# --- Validation (Optional but recommended) ---
if not SECRET_KEY or SECRET_KEY == "a_very_insecure_default_secret_key_CHANGE_ME":
    print("WARNING: SECRET_KEY is not set or is using the default insecure value. Please set a strong SECRET_KEY in your .env file.")

if not CLIENT_SECRET_KEY or CLIENT_SECRET_KEY == "default_client_secret_CHANGE_ME":
     print("WARNING: CLIENT_SECRET_KEY is not set or is using the default insecure value. Please set a strong CLIENT_SECRET_KEY in your .env file and the client.")

if ADMIN_PASSWORD == "password" or ADMIN_PASSWORD == "Asset@123": # Example weak passwords
    print(f"WARNING: Default or potentially weak ADMIN_PASSWORD ('{ADMIN_PASSWORD}') is being used. Please change it in your .env file.")

if MONGO_URI is None and (MONGO_USERNAME and MONGO_PASSWORD):
     print("CRITICAL WARNING: MongoDB URI could not be constructed despite username/password being present. Check for errors above.")
elif MONGO_URI is None:
     print("CRITICAL WARNING: MongoDB URI is None. Check environment variables and potential errors.")