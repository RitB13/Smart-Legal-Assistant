"""
Phase 4: Database Models
Models for storing queries, simulations, sessions, and analytics in MongoDB
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class UserSessionModel(BaseModel):
    """User session for tracking conversation context"""
    session_id: str = Field(..., description="Unique session identifier")
    user_id: Optional[str] = Field(None, description="Optional user identifier")
    language: str = Field("en", description="User's language preference")
    start_time: datetime = Field(default_factory=datetime.utcnow, description="Session start time")
    last_activity: datetime = Field(default_factory=datetime.utcnow, description="Last activity timestamp")
    total_queries: int = Field(default=0, description="Total queries in session")
    modes_used: List[str] = Field(default_factory=list, description="Modes used in session")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional session metadata")
    is_active: bool = Field(default=True, description="Whether session is active")
    
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class QueryRecordModel(BaseModel):
    """Record of a query and its response"""
    query_id: str = Field(..., description="Unique query identifier")
    session_id: Optional[str] = Field(None, description="Associated session ID")
    query_text: str = Field(..., description="User's query text")
    language: str = Field("en", description="Query language")
    
    # Response data
    response_summary: str = Field(..., description="LLM response summary")
    applicable_laws: List[str] = Field(default_factory=list, description="Applicable laws")
    suggestions: List[str] = Field(default_factory=list, description="Suggestions from LLM")
    impact_score: Optional[int] = Field(None, description="Legal impact score (0-100)")
    
    # Mode information
    detected_mode: str = Field(..., description="Detected mode: chat/predict/simulate")
    mode_confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in mode detection")
    mode_reasoning: Optional[str] = Field(None, description="Reasoning for mode selection")
    extracted_action: Optional[str] = Field(None, description="Extracted action from query")
    
    # Metadata
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When query was processed")
    processing_time_ms: float = Field(..., description="Time to process query")
    llm_model: Optional[str] = Field(None, description="LLM model used")
    ip_address: Optional[str] = Field(None, description="User's IP address")
    user_agent: Optional[str] = Field(None, description="Browser user agent")
    
    # Optional feedback
    user_feedback: Optional[int] = Field(None, ge=1, le=5, description="User rating (1-5)")
    user_comment: Optional[str] = Field(None, description="User comment/feedback")
    
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class SimulationRecordModel(BaseModel):
    """Record of a consequence simulation"""
    model_config = ConfigDict(protected_namespaces=())
    
    simulation_id: str = Field(..., description="Unique simulation identifier")
    session_id: Optional[str] = Field(None, description="Associated session ID")
    
    # Input
    planned_action: str = Field(..., description="Description of planned action")
    language: str = Field("en", description="Query language")
    jurisdiction: Optional[str] = Field(None, description="Jurisdiction context")
    
    # Analysis results
    risk_level: str = Field(..., description="Risk level: Low/Medium/High/Critical")
    risk_score: int = Field(..., ge=0, le=100, description="Risk score (0-100)")
    applicable_laws: List[str] = Field(default_factory=list, description="Applicable laws")
    penalties: List[str] = Field(default_factory=list, description="Potential penalties")
    safer_alternatives: List[str] = Field(default_factory=list, description="Safer alternative actions")
    precaution_steps: List[str] = Field(default_factory=list, description="Checklist steps to avoid risk")
    
    # Metadata
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When simulation was run")
    processing_time_ms: float = Field(..., description="Time to process simulation")
    model_version: Optional[str] = Field(None, description="Version of simulator model")
    
    # Feedback
    user_feedback: Optional[int] = Field(None, ge=1, le=5, description="User rating (1-5)")
    user_comment: Optional[str] = Field(None, description="User comment")
    user_found_helpful: Optional[bool] = Field(None, description="Did user find simulation helpful?")


class ModeDecisionModel(BaseModel):
    """Record of mode detection decision"""
    decision_id: str = Field(..., description="Unique decision identifier")
    session_id: Optional[str] = Field(None, description="Associated session ID")
    query_text: str = Field(..., description="User query that triggered mode detection")
    
    # Decision details
    detected_mode: str = Field(..., description="Detected mode: chat/predict/simulate")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0-1)")
    confidence_tier: str = Field(..., description="Confidence tier: very_high/high/medium/low/very_low")
    alternative_modes: List[str] = Field(default_factory=list, description="Alternative modes considered")
    reasoning: str = Field(..., description="Reasoning for mode selection")
    extracted_action: Optional[str] = Field(None, description="Extracted action from query")
    
    # User action
    user_accepted_mode: Optional[bool] = Field(None, description="Did user accept recommended mode?")
    user_selected_mode: Optional[str] = Field(None, description="Mode user actually selected")
    
    # Metadata
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When decision was made")
    language: str = Field("en", description="Query language")
    
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class UserFeedbackModel(BaseModel):
    """User feedback on system quality"""
    feedback_id: str = Field(..., description="Unique feedback identifier")
    session_id: Optional[str] = Field(None, description="Associated session ID")
    
    # What feedback is about
    feedback_type: str = Field(..., description="Type: mode_accuracy/content_quality/helpfulness/other")
    related_query_id: Optional[str] = Field(None, description="Related query ID if applicable")
    related_simulation_id: Optional[str] = Field(None, description="Related simulation ID if applicable")
    
    # Feedback
    rating: int = Field(..., ge=1, le=5, description="Rating 1-5 stars")
    comment: Optional[str] = Field(None, description="User's detailed comment")
    
    # Metadata
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When feedback was submitted")
    language: str = Field("en", description="Feedback language")
    
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class UserAnalyticsModel(BaseModel):
    """Analytics summary for a user/session"""
    analytics_id: str = Field(..., description="Unique analytics identifier")
    session_id: str = Field(..., description="Associated session ID")
    user_id: Optional[str] = Field(None, description="Associated user ID")
    
    # Query statistics
    total_queries: int = Field(default=0, description="Total queries in session")
    avg_mode_confidence: float = Field(default=0.0, description="Average mode detection confidence")
    mode_distribution: Dict[str, int] = Field(default_factory=dict, description="Count by mode")
    
    # Simulation statistics
    total_simulations: int = Field(default=0, description="Total simulations run")
    avg_risk_score: float = Field(default=0.0, description="Average risk score across simulations")
    risk_distribution: Dict[str, int] = Field(default_factory=dict, description="Count by risk level")
    
    # User satisfaction
    avg_user_rating: Optional[float] = Field(None, description="Average user rating (1-5)")
    total_feedback_items: int = Field(default=0, description="Total feedback items submitted")
    
    # Session data
    session_start: datetime = Field(..., description="Session start time")
    session_end: Optional[datetime] = Field(None, description="Session end time")
    session_duration_seconds: float = Field(default=0, description="Total session duration")
    
    # Language usage
    languages_used: List[str] = Field(default_factory=list, description="Languages used in session")
    
    # Mode accuracy
    mode_acceptance_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="% of modes user accepted")
    
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class ChecklisItemRecordModel(BaseModel):
    """Record of a checklist item shown to user"""
    checklist_item_id: str = Field(..., description="Unique checklist item identifier")
    simulation_id: Optional[str] = Field(None, description="Associated simulation")
    query_id: Optional[str] = Field(None, description="Associated query")
    
    # Checklist content
    step_number: int = Field(..., description="Step number")
    action: str = Field(..., description="Action to take")
    details: List[str] = Field(default_factory=list, description="Details")
    priority: str = Field(..., description="Priority level")
    timeline: str = Field(..., description="Timeline")
    reference_law: Optional[str] = Field(None, description="Reference law")
    
    # User interaction
    user_marked_complete: Optional[bool] = Field(None, description="Did user mark as complete?")
    completion_timestamp: Optional[datetime] = Field(None, description="When user marked complete")
    
    # Metadata
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When shown to user")
    
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
