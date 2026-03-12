from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import uuid

class QueryRequest(BaseModel):
    """Request model for legal queries with multilingual support."""
    query: str = Field(
        ..., 
        min_length=1, 
        max_length=2000, 
        description="Legal query or question",
        example="What are my rights as a tenant in case of wrongful eviction?"
    )
    language: Optional[str] = Field(
        None,
        description="ISO language code (e.g., 'en', 'hi', 'bn', 'ta', 'te', 'mr', 'gu', 'kn', 'ml', 'pa'). If not provided, language will be auto-detected.",
        example="en"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "What is the statute of limitations for filing a personal injury claim?",
                "language": "en"
            }
        }


class QueryResponse(BaseModel):
    """Response model for legal queries with multilingual support."""
    summary: str = Field(..., description="Summary of the legal response")
    laws: List[str] = Field(
        default_factory=list, 
        description="List of relevant laws, statutes, or legal references"
    )
    suggestions: List[str] = Field(
        default_factory=list, 
        description="Legal suggestions and recommendations"
    )
    language: str = Field(
        ...,
        description="ISO language code indicating the language of the response",
        example="en"
    )
    request_id: str = Field(..., description="Unique request identifier for tracking")
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when the response was created"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "summary": "Tenants have significant protections under landlord-tenant law...",
                "laws": [
                    "Fair Housing Act",
                    "State Residential Tenancies Act"
                ],
                "suggestions": [
                    "Document any violations in writing",
                    "Send notice to landlord via certified mail"
                ],
                "language": "en",
                "request_id": "a1b2c3d4-e5f6-7g8h-9i0j",
                "created_at": "2026-03-12T10:30:00"
            }
        }
