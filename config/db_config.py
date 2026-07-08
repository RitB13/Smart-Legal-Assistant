import os
from dotenv import load_dotenv

load_dotenv()

# MongoDB Configuration
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://127.0.0.1:27017/")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "smart_legal_db")

# Database connection settings
DB_CONFIG = {
    "url": MONGODB_URL,
    "db_name": MONGODB_DB_NAME,
    "timeout": 5000,
}

logger = __import__('logging').getLogger(__name__)
logger.debug(f"[DB CONFIG] MongoDB URL loaded (host only logged in DEBUG mode)")
logger.debug(f"[DB CONFIG] Database: {MONGODB_DB_NAME}")
