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

print(f"[DB CONFIG] MongoDB URL: {MONGODB_URL}")
print(f"[DB CONFIG] Database Name: {MONGODB_DB_NAME}")
