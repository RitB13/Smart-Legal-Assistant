"""
User Service - Handles user-related database operations.

This service provides methods to:
- Create users
- Retrieve users by ID or email
- Update user information
- Check user existence
"""

from pymongo.errors import DuplicateKeyError
from bson import ObjectId
from datetime import datetime
import logging
from typing import Optional
from src.models.db_models import User, UserCreate, UserInDB
from src.services.db_connection import get_collection

logger = logging.getLogger(__name__)


class UserService:
    """Service for managing users in MongoDB"""
    
    @staticmethod
    def create_user(user_data: UserCreate, password_hash: str) -> Optional[UserInDB]:
        """
        Create a new user in the database.
        
        Args:
            user_data: User information (email, name, language, jurisdiction)
            password_hash: Hashed password (should be hashed before calling this)
            
        Returns:
            UserInDB if successful, None if failed
            
        Example:
            >>> user = UserService.create_user(
            ...     UserCreate(email="john@example.com", name="John Doe", ...),
            ...     password_hash="hashed_password_123"
            ... )
        """
        collection = get_collection("users")
        
        user_dict = {
            "email": user_data.email,
            "name": user_data.name,
            "preferred_language": user_data.preferred_language,
            "jurisdiction": user_data.jurisdiction,
            "password_hash": password_hash,
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        
        try:
            result = collection.insert_one(user_dict)
            user_dict["_id"] = result.inserted_id
            logger.info(f"✅ [USER] Created user: {user_data.email}")
            return UserInDB(**user_dict)
        except DuplicateKeyError:
            logger.error(f"❌ [USER] User already exists: {user_data.email}")
            return None
        except Exception as e:
            logger.error(f"❌ [USER] Error creating user: {e}")
            return None
    
    @staticmethod
    def get_user_by_email(email: str) -> Optional[UserInDB]:
        """
        Get a user by their email address.
        
        Args:
            email: User's email address
            
        Returns:
            UserInDB if found, None if not found
            
        Example:
            >>> user = UserService.get_user_by_email("john@example.com")
        """
        collection = get_collection("users")
        
        try:
            user_dict = collection.find_one({"email": email})
            if user_dict:
                logger.info(f"✅ [USER] Found user: {email}")
                return UserInDB(**user_dict)
            else:
                logger.warning(f"⚠️  [USER] User not found: {email}")
                return None
        except Exception as e:
            logger.error(f"❌ [USER] Error getting user by email: {e}")
            return None
    
    @staticmethod
    def get_user_by_id(user_id: str) -> Optional[UserInDB]:
        """
        Get a user by their ID (ObjectId).
        
        Args:
            user_id: User's MongoDB ObjectId as string
            
        Returns:
            UserInDB if found, None if not found or invalid ID
            
        Example:
            >>> user = UserService.get_user_by_id("507f1f77bcf86cd799439011")
        """
        collection = get_collection("users")
        
        try:
            # Convert string ID to ObjectId
            object_id = ObjectId(user_id)
            user_dict = collection.find_one({"_id": object_id})
            if user_dict:
                logger.info(f"✅ [USER] Found user: {user_id}")
                return UserInDB(**user_dict)
            else:
                logger.warning(f"⚠️  [USER] User not found: {user_id}")
                return None
        except Exception as e:
            logger.error(f"❌ [USER] Error getting user by ID: {e}")
            return None
    
    @staticmethod
    def update_user(user_id: str, **kwargs) -> Optional[UserInDB]:
        """
        Update user information.
        
        Args:
            user_id: User's MongoDB ObjectId as string
            **kwargs: Fields to update (name, preferred_language, jurisdiction, etc.)
            
        Returns:
            Updated UserInDB if successful, None if failed
            
        Example:
            >>> user = UserService.update_user("507f1f77bcf86cd799439011",
            ...                                 name="Jane Doe",
            ...                                 preferred_language="hi")
        """
        collection = get_collection("users")
        
        try:
            # Always update the updated_at timestamp
            update_dict = {**kwargs, "updated_at": datetime.utcnow()}
            
            result = collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": update_dict}
            )
            
            if result.matched_count > 0:
                logger.info(f"✅ [USER] Updated user: {user_id}")
                # Return the updated user
                return UserService.get_user_by_id(user_id)
            else:
                logger.warning(f"⚠️  [USER] User not found to update: {user_id}")
                return None
        except Exception as e:
            logger.error(f"❌ [USER] Error updating user: {e}")
            return None
    
    @staticmethod
    def user_exists(email: str) -> bool:
        """
        Check if a user with given email exists.
        
        Args:
            email: Email address to check
            
        Returns:
            True if user exists, False otherwise
            
        Example:
            >>> if UserService.user_exists("john@example.com"):
            ...     print("User already registered")
        """
        collection = get_collection("users")
        
        try:
            exists = collection.find_one({"email": email}) is not None
            if exists:
                logger.debug(f"[USER] Email exists: {email}")
            return exists
        except Exception as e:
            logger.error(f"❌ [USER] Error checking user existence: {e}")
            return False
    
    @staticmethod
    def delete_user(user_id: str) -> bool:
        """
        Delete a user (set is_active to False instead of hard delete).
        
        Args:
            user_id: User's MongoDB ObjectId as string
            
        Returns:
            True if successful, False if failed
            
        Example:
            >>> success = UserService.delete_user("507f1f77bcf86cd799439011")
        """
        collection = get_collection("users")
        
        try:
            result = collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"is_active": False, "updated_at": datetime.utcnow()}}
            )
            
            if result.matched_count > 0:
                logger.info(f"✅ [USER] Deactivated user: {user_id}")
                return True
            else:
                logger.warning(f"⚠️  [USER] User not found to delete: {user_id}")
                return False
        except Exception as e:
            logger.error(f"❌ [USER] Error deleting user: {e}")
            return False
    
    @staticmethod
    def get_user_stats(user_id: str) -> dict:
        """
        Get statistics about a user's activity.
        
        Args:
            user_id: User's MongoDB ObjectId as string
            
        Returns:
            Dictionary with user stats (will expand as we build more services)
            
        Example:
            >>> stats = UserService.get_user_stats("507f1f77bcf86cd799439011")
        """
        try:
            user = UserService.get_user_by_id(user_id)
            if not user:
                return {}
            
            return {
                "user_id": user_id,
                "email": user.email,
                "name": user.name,
                "created_at": user.created_at.isoformat(),
                "last_updated": user.updated_at.isoformat(),
            }
        except Exception as e:
            logger.error(f"❌ [USER] Error getting user stats: {e}")
            return {}
