"""
Pydantic models for MongoDB documents.

These models define the structure of data stored in MongoDB collections.
They handle data validation, serialization, and deserialization.
"""

from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime
from typing import Optional, List, Dict, Any
from bson import ObjectId


# ==================== HELPER: ObjectId STRING CONVERSION ====================
# MongoDB returns ObjectId objects, but Pydantic needs strings
# We'll handle this with field_validator


# ==================== USER MODELS ====================

class UserBase(BaseModel):
    """Base user data (shared fields)"""
    email: EmailStr
    name: str
    preferred_language: str = "en"
    jurisdiction: str = "india"


class UserCreate(UserBase):
    """Data needed to create a user"""
    password: str  # Will be hashed before storing


class UserInDB(UserBase):
    """User as stored in database"""
    id: str = Field(alias="_id")
    password_hash: str
    is_active: bool = True
    created_at: datetime
    updated_at: datetime
    
    @field_validator('id', mode='before')
    @classmethod
    def convert_objectid_to_str(cls, v):
        return str(v) if v is not None else None
    
    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            ObjectId: lambda v: str(v),
        }


class User(UserBase):
    """User returned to frontend (no password)"""
    id: str = Field(alias="_id")
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    @field_validator('id', mode='before')
    @classmethod
    def convert_objectid_to_str(cls, v):
        return str(v) if v is not None else None
    
    class Config:
        populate_by_name = True


# ==================== CONVERSATION MODELS ====================

class MessageInConversation(BaseModel):
    """Single message in a conversation"""
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime
    language: Optional[str] = None


class ConversationBase(BaseModel):
    """Base conversation data"""
    title: str
    language: str = "en"


class ConversationCreate(ConversationBase):
    """Data needed to create a conversation"""
    user_id: str


class ConversationInDB(ConversationBase):
    """Conversation as stored in database"""
    id: str = Field(alias="_id")
    user_id: str
    messages: List[MessageInConversation] = []
    created_at: datetime
    updated_at: datetime
    
    @field_validator('id', mode='before')
    @classmethod
    def convert_objectid_to_str(cls, v):
        return str(v) if v is not None else None
    
    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            ObjectId: lambda v: str(v),
        }


class Conversation(ConversationBase):
    """Conversation returned to frontend"""
    id: str = Field(alias="_id")
    messages: List[MessageInConversation] = []
    created_at: datetime
    updated_at: datetime
    
    @field_validator('id', mode='before')
    @classmethod
    def convert_objectid_to_str(cls, v):
        return str(v) if v is not None else None
    
    class Config:
        populate_by_name = True


# ==================== CASE PREDICTION MODELS ====================

class CasePredictionMetadata(BaseModel):
    """Metadata about a case being predicted"""
    case_name: str
    case_type: str  # "Criminal", "Civil", "Family", etc.
    year: int
    jurisdiction_state: str
    damages: Optional[float] = None
    parties_count: int = 2
    is_appeal: bool = False


class PredictionResult(BaseModel):
    """The ML prediction result for a case"""
    verdict: str  # Accepted, Acquitted, Convicted, Rejected, Settlement, Other, Unknown
    confidence: float  # 0-100
    probabilities: Dict[str, float]  # {"Accepted": 0.45, "Convicted": 0.3, ...}
    shap_explanation: Dict[str, float]  # Feature importance from SHAP model
    similar_cases: List[Dict[str, Any]] = []
    risk_assessment: Dict[str, Any] = {}


class CasePredictionCreate(BaseModel):
    """Data needed to save a prediction"""
    user_id: str
    metadata: CasePredictionMetadata
    result: PredictionResult


class CasePredictionInDB(BaseModel):
    """Prediction as stored in database"""
    id: str = Field(alias="_id")
    user_id: str
    metadata: CasePredictionMetadata
    result: PredictionResult
    created_at: datetime
    
    @field_validator('id', mode='before')
    @classmethod
    def convert_objectid_to_str(cls, v):
        return str(v) if v is not None else None
    
    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            ObjectId: lambda v: str(v),
        }


class CasePrediction(BaseModel):
    """Prediction returned to frontend"""
    id: str = Field(alias="_id")
    metadata: CasePredictionMetadata
    result: PredictionResult
    created_at: datetime
    
    @field_validator('id', mode='before')
    @classmethod
    def convert_objectid_to_str(cls, v):
        return str(v) if v is not None else None
    
    class Config:
        populate_by_name = True


# ==================== FEEDBACK MODELS ====================

class FeedbackCreate(BaseModel):
    """User feedback on a prediction"""
    prediction_id: str
    user_id: str
    rating: int  # 1-5 stars
    comment: Optional[str] = None
    was_verdict_correct: Optional[bool] = None


class FeedbackInDB(FeedbackCreate):
    """Feedback as stored in database"""
    id: str = Field(alias="_id")
    created_at: datetime
    
    @field_validator('id', mode='before')
    @classmethod
    def convert_objectid_to_str(cls, v):
        return str(v) if v is not None else None
    
    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            ObjectId: lambda v: str(v),
        }


# ==================== AUDIT LOG MODELS ====================

class AuditLogCreate(BaseModel):
    """Log entry for auditing and compliance"""
    user_id: Optional[str] = None
    action: str  # "predict", "feedback", "login", etc.
    resource: str  # "case_prediction", "conversation", etc.
    resource_id: Optional[str] = None
    details: Dict[str, Any] = {}


class AuditLogInDB(AuditLogCreate):
    """Audit log as stored in database"""
    id: str = Field(alias="_id")
    created_at: datetime
    
    @field_validator('id', mode='before')
    @classmethod
    def convert_objectid_to_str(cls, v):
        return str(v) if v is not None else None
    
    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            ObjectId: lambda v: str(v),
        }
