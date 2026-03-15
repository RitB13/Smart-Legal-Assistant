"""
Conversation Service - Handles conversation and message operations.

This service provides methods to:
- Create conversations
- Retrieve conversations
- Add messages to conversations
- Search and filter conversations
- Delete conversations
"""

from pymongo import DESCENDING
from bson import ObjectId
from datetime import datetime
import logging
from typing import Optional, List
from src.models.db_models import (
    Conversation, ConversationCreate, ConversationInDB,
    MessageInConversation
)
from src.services.db_connection import get_collection

logger = logging.getLogger(__name__)


class ConversationService:
    """Service for managing conversations in MongoDB"""
    
    @staticmethod
    def create_conversation(conv_data: ConversationCreate) -> Optional[ConversationInDB]:
        """
        Create a new conversation for a user.
        
        Args:
            conv_data: Conversation information (title, language, user_id)
            
        Returns:
            ConversationInDB if successful, None if failed
            
        Example:
            >>> conv = ConversationService.create_conversation(
            ...     ConversationCreate(
            ...         user_id="507f1f77bcf86cd799439011",
            ...         title="Initial Consultation",
            ...         language="en"
            ...     )
            ... )
        """
        collection = get_collection("conversations")
        
        conv_dict = {
            "user_id": conv_data.user_id,
            "title": conv_data.title,
            "language": conv_data.language,
            "messages": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        
        try:
            result = collection.insert_one(conv_dict)
            conv_dict["_id"] = result.inserted_id
            logger.info(f"✅ [CONV] Created conversation: {result.inserted_id}")
            return ConversationInDB(**conv_dict)
        except Exception as e:
            logger.error(f"❌ [CONV] Error creating conversation: {e}")
            return None
    
    @staticmethod
    def get_conversation(conv_id: str) -> Optional[ConversationInDB]:
        """
        Get a conversation by ID.
        
        Args:
            conv_id: Conversation's MongoDB ObjectId as string
            
        Returns:
            ConversationInDB if found, None if not found
            
        Example:
            >>> conv = ConversationService.get_conversation("507f1f77bcf86cd799439011")
        """
        collection = get_collection("conversations")
        
        try:
            conv_dict = collection.find_one({"_id": ObjectId(conv_id)})
            if conv_dict:
                logger.info(f"✅ [CONV] Found conversation: {conv_id}")
                return ConversationInDB(**conv_dict)
            else:
                logger.warning(f"⚠️  [CONV] Conversation not found: {conv_id}")
                return None
        except Exception as e:
            logger.error(f"❌ [CONV] Error getting conversation: {e}")
            return None
    
    @staticmethod
    def get_user_conversations(user_id: str, limit: int = 50) -> List[ConversationInDB]:
        """
        Get all conversations for a user, sorted by most recent first.
        
        Args:
            user_id: User's MongoDB ObjectId as string
            limit: Maximum number of conversations to return (default 50)
            
        Returns:
            List of ConversationInDB objects (newest first)
            
        Example:
            >>> conversations = ConversationService.get_user_conversations(
            ...     "507f1f77bcf86cd799439011",
            ...     limit=20
            ... )
        """
        collection = get_collection("conversations")
        
        try:
            conversations = list(collection.find(
                {"user_id": user_id}
            ).sort("created_at", DESCENDING).limit(limit))
            
            logger.info(f"✅ [CONV] Found {len(conversations)} conversation(s) for user")
            return [ConversationInDB(**conv) for conv in conversations]
        except Exception as e:
            logger.error(f"❌ [CONV] Error getting conversations: {e}")
            return []
    
    @staticmethod
    def add_message(conv_id: str, role: str, content: str, language: Optional[str] = None) -> Optional[ConversationInDB]:
        """
        Add a message to a conversation.
        
        Args:
            conv_id: Conversation's MongoDB ObjectId as string
            role: Message role ("user" or "assistant")
            content: Message text content
            language: Language of the message (optional)
            
        Returns:
            Updated ConversationInDB if successful, None if failed
            
        Example:
            >>> conv = ConversationService.add_message(
            ...     "507f1f77bcf86cd799439011",
            ...     role="user",
            ...     content="What are my case prospects?",
            ...     language="en"
            ... )
        """
        collection = get_collection("conversations")
        
        try:
            message = {
                "role": role,
                "content": content,
                "timestamp": datetime.utcnow(),
                "language": language,
            }
            
            result = collection.update_one(
                {"_id": ObjectId(conv_id)},
                {
                    "$push": {"messages": message},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            
            if result.matched_count > 0:
                logger.info(f"✅ [CONV] Added message to conversation: {conv_id}")
                # Return updated conversation
                return ConversationService.get_conversation(conv_id)
            else:
                logger.warning(f"⚠️  [CONV] Conversation not found: {conv_id}")
                return None
        except Exception as e:
            logger.error(f"❌ [CONV] Error adding message: {e}")
            return None
    
    @staticmethod
    def delete_conversation(conv_id: str) -> bool:
        """
        Delete a conversation.
        
        Args:
            conv_id: Conversation's MongoDB ObjectId as string
            
        Returns:
            True if successful, False if failed
            
        Example:
            >>> success = ConversationService.delete_conversation("507f1f77bcf86cd799439011")
        """
        collection = get_collection("conversations")
        
        try:
            result = collection.delete_one({"_id": ObjectId(conv_id)})
            
            if result.deleted_count > 0:
                logger.info(f"✅ [CONV] Deleted conversation: {conv_id}")
                return True
            else:
                logger.warning(f"⚠️  [CONV] Conversation not found to delete: {conv_id}")
                return False
        except Exception as e:
            logger.error(f"❌ [CONV] Error deleting conversation: {e}")
            return False
    
    @staticmethod
    def search_conversations(user_id: str, query: str) -> List[ConversationInDB]:
        """
        Search conversations by title (case-insensitive).
        
        Args:
            user_id: User's MongoDB ObjectId as string
            query: Search query string
            
        Returns:
            List of matching ConversationInDB objects
            
        Example:
            >>> results = ConversationService.search_conversations(
            ...     "507f1f77bcf86cd799439011",
            ...     "divorce"
            ... )
        """
        collection = get_collection("conversations")
        
        try:
            conversations = list(collection.find({
                "user_id": user_id,
                "title": {"$regex": query, "$options": "i"}  # Case-insensitive regex search
            }).sort("created_at", DESCENDING))
            
            logger.info(f"✅ [CONV] Found {len(conversations)} matching conversation(s)")
            return [ConversationInDB(**conv) for conv in conversations]
        except Exception as e:
            logger.error(f"❌ [CONV] Error searching conversations: {e}")
            return []
    
    @staticmethod
    def update_conversation_title(conv_id: str, new_title: str) -> Optional[ConversationInDB]:
        """
        Update a conversation's title.
        
        Args:
            conv_id: Conversation's MongoDB ObjectId as string
            new_title: New title for the conversation
            
        Returns:
            Updated ConversationInDB if successful, None if failed
            
        Example:
            >>> conv = ConversationService.update_conversation_title(
            ...     "507f1f77bcf86cd799439011",
            ...     "Family Law Case"
            ... )
        """
        collection = get_collection("conversations")
        
        try:
            result = collection.update_one(
                {"_id": ObjectId(conv_id)},
                {"$set": {
                    "title": new_title,
                    "updated_at": datetime.utcnow()
                }}
            )
            
            if result.matched_count > 0:
                logger.info(f"✅ [CONV] Updated conversation title: {conv_id}")
                return ConversationService.get_conversation(conv_id)
            else:
                logger.warning(f"⚠️  [CONV] Conversation not found: {conv_id}")
                return None
        except Exception as e:
            logger.error(f"❌ [CONV] Error updating conversation title: {e}")
            return None
    
    @staticmethod
    def get_conversation_stats(user_id: str) -> dict:
        """
        Get conversation statistics for a user.
        
        Args:
            user_id: User's MongoDB ObjectId as string
            
        Returns:
            Dictionary with conversation stats
            
        Example:
            >>> stats = ConversationService.get_conversation_stats("507f1f77bcf86cd799439011")
        """
        collection = get_collection("conversations")
        
        try:
            total = collection.count_documents({"user_id": user_id})
            
            # Get total messages across all conversations
            conversations = list(collection.find({"user_id": user_id}))
            total_messages = sum(len(conv.get("messages", [])) for conv in conversations)
            
            return {
                "total_conversations": total,
                "total_messages": total_messages,
            }
        except Exception as e:
            logger.error(f"❌ [CONV] Error getting conversation stats: {e}")
            return {"total_conversations": 0, "total_messages": 0}
