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
    Connection is established lazily on first access to avoid startup failures.
    """
    
    _instance = None
    _client = None
    _db = None
    _connection_attempted = False
    _connection_failed = False
    
    def __new__(cls):
        """Create singleton instance"""
        if cls._instance is None:
            cls._instance = super(DatabaseConnection, cls).__new__(cls)
        return cls._instance
    
    def _ensure_connected(self):
        """Ensure connection is established (lazy connection)"""
        if self._connection_attempted:
            if self._connection_failed:
                raise RuntimeError("MongoDB connection failed. Database is unavailable.")
            return
        
        self._connection_attempted = True
        self._connect()
    
    def _connect(self):
        """Establish connection to MongoDB"""
        try:
            logger.info(f"[DB] Connecting to MongoDB: {DB_CONFIG['url']}")
            
            # Create MongoDB client 
            # For MongoDB Atlas, TLS is required. If you get SSL errors:
            # 1. Ensure your IP is whitelisted in Atlas Network Access
            # 2. Try updating your system's SSL certificates
            # 3. Use a public IP or configure network access to 0.0.0.0/0 (not recommended)
            self._client = MongoClient(
                DB_CONFIG["url"],
                serverSelectionTimeoutMS=DB_CONFIG["timeout"],
                connectTimeoutMS=10000,
                retryWrites=True,
                authSource="admin"
            )
            
            # Test the connection by pinging the server
            logger.debug("[DB] Sending ping command to test connection...")
            self._client.admin.command('ping')
            logger.info("✅ [DB] Connected to MongoDB successfully")
            
            # Get the database
            self._db = self._client[DB_CONFIG["db_name"]]
            logger.info(f"✅ [DB] Using database: {DB_CONFIG['db_name']}")
            self._connection_failed = False
            
        except ServerSelectionTimeoutError as e:
            self._connection_failed = True
            logger.warning("⚠️  [DB] Could not connect to MongoDB server!")
            logger.warning("   The database is currently unavailable.")
            logger.warning("   Connection URL: " + DB_CONFIG['url'])
            logger.warning("   Error details: " + str(e))
            logger.warning("\n   TROUBLESHOOTING STEPS:")
            logger.warning("   1. Check your internet connection")
            logger.warning("   2. Verify MongoDB Atlas credentials are correct")
            logger.warning("   3. Ensure your IP is in MongoDB Atlas Network Access whitelist")
            logger.warning("      - Go to: https://cloud.mongodb.com/v2 > Network Access")
            logger.warning("      - Add your current IP address")
            logger.warning("   4. If using VPN/proxy, you may need to configure it in MongoDB settings")
            logger.warning("   Connection URL: " + DB_CONFIG['url'])
            logger.warning("   Database operations will fail. Please check your connection.")
            
        except ConnectionFailure as e:
            self._connection_failed = True
            logger.warning(f"⚠️  [DB] Connection failure: {e}")
            
        except Exception as e:
            self._connection_failed = True
            logger.warning(f"⚠️  [DB] Error connecting to database: {e}")
    
    @property
    def client(self):
        """Get MongoDB client instance"""
        self._ensure_connected()
        if self._client is None:
            raise RuntimeError("Database connection failed")
        return self._client
    
    @property
    def db(self):
        """Get database instance"""
        self._ensure_connected()
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
        return self.db[collection_name]
    
    def is_connected(self) -> bool:
        """Check if database is connected"""
        return self._client is not None and not self._connection_failed
    
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


# Lazy getter for singleton instance
_db_connection = None

def get_db_connection() -> DatabaseConnection:
    """Get or create the singleton database connection"""
    global _db_connection
    if _db_connection is None:
        _db_connection = DatabaseConnection()
    return _db_connection

def get_db():
    """
    Get database instance for dependency injection.
    
    Returns:
        MongoDB database object
    """
    return get_db_connection().db

def get_collection(collection_name: str):
    """
    Get a collection by name.
    
    Args:
        collection_name: Name of the collection
        
    Returns:
        MongoDB collection object
    """
    return get_db_connection().get_collection(collection_name)
