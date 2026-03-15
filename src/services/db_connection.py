"""
MongoDB Database Connection Module

This module provides a singleton connection to MongoDB that's used
throughout the application.
"""

from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure
from config.db_config import DB_CONFIG
import logging

logger = logging.getLogger(__name__)

class DatabaseConnection:
    """
    Singleton class for MongoDB connection.
    
    Ensures only one connection to MongoDB exists throughout the app.
    Usage:
        db_connection = DatabaseConnection()
        db = db_connection.db
        collection = db_connection.get_collection("users")
    """
    
    _instance = None
    _client = None
    _db = None
    
    def __new__(cls):
        """Create singleton instance"""
        if cls._instance is None:
            cls._instance = super(DatabaseConnection, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize database connection on first instantiation"""
        if self._client is None:
            self._connect()
    
    def _connect(self):
        """Establish connection to MongoDB"""
        try:
            logger.info(f"[DB] Connecting to MongoDB: {DB_CONFIG['url']}")
            
            # Create MongoDB client
            self._client = MongoClient(
                DB_CONFIG["url"],
                serverSelectionTimeoutMS=DB_CONFIG["timeout"]
            )
            
            # Test the connection by pinging the server
            self._client.admin.command('ping')
            logger.info("✅ [DB] Connected to MongoDB successfully")
            
            # Get the database
            self._db = self._client[DB_CONFIG["db_name"]]
            logger.info(f"✅ [DB] Using database: {DB_CONFIG['db_name']}")
            
        except ServerSelectionTimeoutError as e:
            logger.error("❌ [DB] Could not connect to MongoDB server!")
            logger.error("   Make sure:")
            logger.error("   1. MongoDB server is running (mongod)")
            logger.error("   2. Connection URL is correct: " + DB_CONFIG['url'])
            raise
        except ConnectionFailure as e:
            logger.error(f"❌ [DB] Connection failure: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ [DB] Unexpected error: {e}")
            raise
    
    @property
    def client(self):
        """Get MongoDB client instance"""
        return self._client
    
    @property
    def db(self):
        """Get database instance"""
        if self._db is None:
            raise RuntimeError("Database not connected")
        return self._db
    
    def get_collection(self, collection_name: str):
        """
        Get a specific collection from the database.
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            MongoDB collection object
        """
        return self._db[collection_name]
    
    def close(self):
        """Close the database connection"""
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
            logger.info("✅ [DB] Connection closed")
    
    def __del__(self):
        """Cleanup on deletion"""
        self.close()


# Create the singleton instance
db_connection = DatabaseConnection()

def get_db():
    """
    Get database instance for dependency injection.
    
    Returns:
        MongoDB database object
    """
    return db_connection.db

def get_collection(collection_name: str):
    """
    Get a collection by name.
    
    Args:
        collection_name: Name of the collection
        
    Returns:
        MongoDB collection object
    """
    return db_connection.get_collection(collection_name)
