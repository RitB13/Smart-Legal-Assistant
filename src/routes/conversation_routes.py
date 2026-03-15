"""
Conversation Routes - FastAPI endpoints for managing conversations.

Endpoints:
- POST   /conversations              - Create new conversation
- GET    /conversations              - Get all conversations for user
- GET    /conversations/{id}         - Get specific conversation
- PUT    /conversations/{id}         - Update conversation
- DELETE /conversations/{id}         - Delete conversation
- POST   /conversations/{id}/message - Add message to conversation
"""

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import logging

from src.routes.auth_routes import get_current_user
from src.services.auth_service import TokenData
from src.services.conversation_service import ConversationService
from src.models.db_models import Conversation, MessageInConversation

logger = logging.getLogger(__name__)

# Router for conversation endpoints
router = APIRouter(prefix="/conversations", tags=["Conversations"])


# ==================== REQUEST/RESPONSE MODELS ====================

class MessageCreate(BaseModel):
    """Create message request"""
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    case_type: Optional[str] = None
    analyzed_entities: Optional[dict] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "role": "user",
                "content": "What are my rights in a property dispute?",
                "case_type": "property_dispute"
            }
        }


class MessageResponse(BaseModel):
    """Message response"""
    role: str
    content: str
    timestamp: datetime
    case_type: Optional[str] = None
    analyzed_entities: Optional[dict] = None


class ConversationCreate(BaseModel):
    """Create conversation request"""
    title: Optional[str] = None
    case_type: str = "general"
    jurisdiction: str = "india"
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "Property Dispute Discussion",
                "case_type": "property_dispute",
                "jurisdiction": "india"
            }
        }


class ConversationResponse(BaseModel):
    """Conversation response"""
    id: str = Field(alias="_id")
    user_id: str
    title: str
    case_type: str
    jurisdiction: str
    messages: Optional[List[MessageResponse]] = []
    created_at: datetime
    updated_at: datetime
    message_count: int = 0
    
    class Config:
        populate_by_name = True


class ConversationUpdateRequest(BaseModel):
    """Update conversation request"""
    title: Optional[str] = None
    case_type: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "Updated Property Dispute Discussion"
            }
        }


# ==================== ENDPOINTS ====================

@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    request: ConversationCreate,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Create new conversation for user.
    
    Args:
        request: Conversation creation details
        current_user: Current authenticated user
        
    Returns:
        ConversationResponse with new conversation
        
    Example:
        POST /conversations
        {
            "title": "Property Dispute Discussion",
            "case_type": "property_dispute",
            "jurisdiction": "india"
        }
    """
    try:
        logger.info(f"[CONV] Creating conversation for user {current_user.user_id}")
        
        conversation = ConversationService.create_conversation(
            user_id=current_user.user_id,
            title=request.title or f"Conversation {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            case_type=request.case_type,
            jurisdiction=request.jurisdiction
        )
        
        if not conversation:
            logger.error(f"[CONV] Failed to create conversation for {current_user.user_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create conversation"
            )
        
        logger.info(f"[CONV] Conversation created: {conversation.id}")
        
        return ConversationResponse(
            _id=str(conversation.id),
            user_id=str(conversation.user_id),
            title=conversation.title,
            case_type=conversation.case_type,
            jurisdiction=conversation.jurisdiction,
            messages=[],
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            message_count=0
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[CONV] Error creating conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create conversation"
        )


@router.get("", response_model=List[ConversationResponse])
async def get_conversations(
    current_user: TokenData = Depends(get_current_user),
    skip: int = 0,
    limit: int = 20
):
    """
    Get all conversations for authenticated user.
    
    Args:
        current_user: Current authenticated user
        skip: Number of conversations to skip (pagination)
        limit: Maximum number of conversations to return
        
    Returns:
        List of ConversationResponse
        
    Example:
        GET /conversations?skip=0&limit=20
    """
    try:
        logger.info(f"[CONV] Fetching conversations for user {current_user.user_id}")
        
        conversations = ConversationService.get_user_conversations(
            user_id=current_user.user_id,
            skip=skip,
            limit=limit
        )
        
        result = []
        for conv in conversations:
            result.append(ConversationResponse(
                _id=str(conv.id),
                user_id=str(conv.user_id),
                title=conv.title,
                case_type=conv.case_type,
                jurisdiction=conv.jurisdiction,
                messages=[],
                created_at=conv.created_at,
                updated_at=conv.updated_at,
                message_count=len(conv.messages) if conv.messages else 0
            ))
        
        logger.debug(f"[CONV] Retrieved {len(result)} conversations for {current_user.user_id}")
        return result
        
    except Exception as e:
        logger.error(f"[CONV] Error fetching conversations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch conversations"
        )


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Get specific conversation by ID.
    
    Args:
        conversation_id: Conversation ID
        current_user: Current authenticated user
        
    Returns:
        ConversationResponse with full conversation details
        
    Example:
        GET /conversations/507f1f77bcf86cd799439011
    """
    try:
        logger.info(f"[CONV] Fetching conversation {conversation_id}")
        
        conversation = ConversationService.get_conversation(conversation_id)
        
        if not conversation:
            logger.warning(f"[CONV] Conversation not found: {conversation_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        # Verify user owns this conversation
        if str(conversation.user_id) != current_user.user_id:
            logger.warning(f"[CONV] Unauthorized access to {conversation_id} by {current_user.user_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        messages = [
            MessageResponse(
                role=msg.role,
                content=msg.content,
                timestamp=msg.timestamp,
                case_type=msg.case_type,
                analyzed_entities=msg.analyzed_entities
            )
            for msg in conversation.messages
        ] if conversation.messages else []
        
        return ConversationResponse(
            _id=str(conversation.id),
            user_id=str(conversation.user_id),
            title=conversation.title,
            case_type=conversation.case_type,
            jurisdiction=conversation.jurisdiction,
            messages=messages,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            message_count=len(conversation.messages) if conversation.messages else 0
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[CONV] Error fetching conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch conversation"
        )


@router.put("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: str,
    request: ConversationUpdateRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Update conversation details (title, case_type).
    
    Args:
        conversation_id: Conversation ID
        request: Update details
        current_user: Current authenticated user
        
    Returns:
        Updated ConversationResponse
        
    Example:
        PUT /conversations/507f1f77bcf86cd799439011
        {
            "title": "Updated Title"
        }
    """
    try:
        logger.info(f"[CONV] Updating conversation {conversation_id}")
        
        conversation = ConversationService.get_conversation(conversation_id)
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        # Verify user owns this conversation
        if str(conversation.user_id) != current_user.user_id:
            logger.warning(f"[CONV] Unauthorized update to {conversation_id} by {current_user.user_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Update title if provided
        if request.title:
            conversation = ConversationService.update_conversation_title(
                conversation_id,
                request.title
            )
        
        # Update case_type if provided (implement in service if needed)
        
        messages = [
            MessageResponse(
                role=msg.role,
                content=msg.content,
                timestamp=msg.timestamp,
                case_type=msg.case_type,
                analyzed_entities=msg.analyzed_entities
            )
            for msg in conversation.messages
        ] if conversation.messages else []
        
        return ConversationResponse(
            _id=str(conversation.id),
            user_id=str(conversation.user_id),
            title=conversation.title,
            case_type=conversation.case_type,
            jurisdiction=conversation.jurisdiction,
            messages=messages,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            message_count=len(conversation.messages) if conversation.messages else 0
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[CONV] Error updating conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update conversation"
        )


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Delete conversation.
    
    Args:
        conversation_id: Conversation ID
        current_user: Current authenticated user
        
    Example:
        DELETE /conversations/507f1f77bcf86cd799439011
    """
    try:
        logger.info(f"[CONV] Deleting conversation {conversation_id}")
        
        conversation = ConversationService.get_conversation(conversation_id)
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        # Verify user owns this conversation
        if str(conversation.user_id) != current_user.user_id:
            logger.warning(f"[CONV] Unauthorized delete of {conversation_id} by {current_user.user_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        ConversationService.delete_conversation(conversation_id)
        
        logger.info(f"[CONV] Conversation deleted: {conversation_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[CONV] Error deleting conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete conversation"
        )


@router.post("/{conversation_id}/messages", response_model=ConversationResponse)
async def add_message_to_conversation(
    conversation_id: str,
    request: MessageCreate,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Add message to conversation.
    
    Args:
        conversation_id: Conversation ID
        request: Message details (role, content, etc.)
        current_user: Current authenticated user
        
    Returns:
        Updated ConversationResponse with new message
        
    Example:
        POST /conversations/507f1f77bcf86cd799439011/messages
        {
            "role": "user",
            "content": "What are my rights?",
            "case_type": "property_dispute"
        }
    """
    try:
        logger.info(f"[CONV] Adding message to conversation {conversation_id}")
        
        conversation = ConversationService.get_conversation(conversation_id)
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        # Verify user owns this conversation
        if str(conversation.user_id) != current_user.user_id:
            logger.warning(f"[CONV] Unauthorized message add to {conversation_id} by {current_user.user_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Add message to conversation
        conversation = ConversationService.add_message(
            conversation_id=conversation_id,
            role=request.role,
            content=request.content,
            case_type=request.case_type,
            analyzed_entities=request.analyzed_entities
        )
        
        if not conversation:
            logger.error(f"[CONV] Failed to add message to {conversation_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to add message"
            )
        
        logger.debug(f"[CONV] Message added to {conversation_id}")
        
        messages = [
            MessageResponse(
                role=msg.role,
                content=msg.content,
                timestamp=msg.timestamp,
                case_type=msg.case_type,
                analyzed_entities=msg.analyzed_entities
            )
            for msg in conversation.messages
        ] if conversation.messages else []
        
        return ConversationResponse(
            _id=str(conversation.id),
            user_id=str(conversation.user_id),
            title=conversation.title,
            case_type=conversation.case_type,
            jurisdiction=conversation.jurisdiction,
            messages=messages,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            message_count=len(conversation.messages) if conversation.messages else 0
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[CONV] Error adding message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add message"
        )
