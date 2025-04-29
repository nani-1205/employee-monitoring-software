import os
from dotenv import load_dotenv

load_dotenv() # Load environment variables from a .env file if present

# --- Core Settings ---
# Generate a strong secret key: python -c 'import secrets; print(secrets.token_hex(16))'
SECRET_KEY = os.getenv("SECRET_KEY", "a_very_insecure_default_secret_key")
# Set to False in production!
DEBUG = os.getenv("FLASK_DEBUG", "True").lower() in ("true", "1", "t")

# --- Database Settings (MongoDB) ---
MONGO_HOST = os.getenv("MONGO_HOST", "localhost")
MONGO_PORT = int(os.getenv("MONGO_PORT", "27017"))
MONGO_USERNAME = os.getenv("MONGO_USERNAME", "admin") # Change to your MongoDB admin username
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD", "password") # Change to your MongoDB admin password
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "employee_monitor")
MONGO_AUTH_DB = os.getenv("MONGO_AUTH_DB", "admin") # DB where the user is defined

# Construct MongoDB URI
MONGO_URI = f"mongodb://{MONGO_USERNAME}:{MONGO_PASSWORD}@{MONGO_HOST}:{MONGO_PORT}/{MONGO_DB_NAME}?authSource={MONGO_AUTH_DB}"

# --- Storage Settings ---
SCREENSHOT_STORAGE_PATH = os.path.join(os.path.dirname(__file__), "storage", "screenshots")

# --- Admin Credentials (Replace with a proper user management system) ---
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "password") # Hash this in production!

# --- Client Settings ---
# Optional: A secret key clients must send to validate requests
CLIENT_SECRET_KEY = os.getenv("CLIENT_SECRET_KEY", "default_client_secret") # Change this!