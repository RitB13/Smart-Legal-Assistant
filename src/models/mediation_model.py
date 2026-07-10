"""
Mediation Models - Pydantic schemas for the AI-Mediated Dispute Resolution feature.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Literal, Dict, Any
from datetime import datetime
from enum import Enum


class MediationStatus(str, Enum):
    pending_party_b = "pending_party_b"                    # Party B hasn't joined yet
    pending_statements = "pending_statements"              # Both joined, neither submitted
    pending_party_b_statement = "pending_party_b_statement"  # A submitted, waiting B
    pending_party_a_statement = "pending_party_a_statement"  # B submitted, waiting A
    analysis_running = "analysis_running"
    completed = "completed"
    failed = "failed"


# ─── Request Models ────────────────────────────────────────────────────────────

class CreateDisputeRequest(BaseModel):
    case_description: str = Field(..., min_length=50, description="Brief description of the dispute (min 50 chars)")
    case_type: str = Field(..., description="Type: property, money, family, employment, consumer, contract, other")
    jurisdiction: str = Field(default="India", description="Legal jurisdiction")
    state: Optional[str] = Field(None, description="State/region within jurisdiction")
    language: str = Field(default="en", description="ISO language code")
    prior_chat_session_id: Optional[str] = Field(None, description="Chat session ID if user went through guided pipeline")
    prior_prediction_id: Optional[str] = Field(None, description="Prediction ID if user used case predictor first")

    class Config:
        json_schema_extra = {
            "example": {
                "case_description": "My landlord refused to return my security deposit of Rs. 50,000 after I vacated the property in good condition.",
                "case_type": "property",
                "jurisdiction": "India",
                "state": "Delhi",
                "language": "en"
            }
        }


class JoinDisputeRequest(BaseModel):
    invite_code: str = Field(..., min_length=6, description="Invite code shared by Party A")

    class Config:
        json_schema_extra = {"example": {"invite_code": "A3F9B2C1"}}


class SubmitStatementRequest(BaseModel):
    statement: str = Field(..., min_length=50, description="Your account of the dispute (min 50 chars)")
    supporting_points: Optional[List[str]] = Field(
        default_factory=list,
        description="Key facts or evidence you want highlighted"
    )
    language: str = Field(default="en", description="Language of your statement")

    class Config:
        json_schema_extra = {
            "example": {
                "statement": "I rented the flat at X for 11 months and paid Rs. 50,000 as security. I vacated on time and left the flat clean. The landlord refused to return the deposit claiming damages that did not exist.",
                "supporting_points": ["Paid deposit via bank transfer with receipt", "Vacated on agreed date", "No damages existed at time of vacating"],
                "language": "en"
            }
        }


class MediationFeedbackRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5, description="Rating 1-5")
    accepted_settlement: Optional[bool] = Field(None, description="Whether the party accepted the proposed settlement")
    comment: Optional[str] = Field(None, description="Optional comment")


# ─── Sub-models for the Mediation Report ──────────────────────────────────────

class SettlementRange(BaseModel):
    low: Optional[float] = Field(None, description="Low estimate (INR or relevant currency)")
    median: Optional[float] = Field(None, description="Median/most likely estimate")
    high: Optional[float] = Field(None, description="High estimate")
    currency: str = Field(default="INR")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    basis: str = Field(default="llm_estimate", description="'llm_estimate' or 'ml_model'")


class AgreementPoint(BaseModel):
    point: str = Field(..., description="Something both parties appear to agree on")
    confidence: float = Field(..., ge=0.0, le=1.0, description="AI confidence that both parties agree")


class ConflictPoint(BaseModel):
    point: str = Field(..., description="The point of disagreement")
    party_a_position: str = Field(..., description="Party A's stated position")
    party_b_position: str = Field(..., description="Party B's stated position")
    severity: Literal["critical", "major", "minor"] = Field(..., description="How central this conflict is")


class FairnessAudit(BaseModel):
    party_a_privilege_score: float = Field(..., ge=0.0, le=1.0, description="Linguistic privilege score (higher = more advantaged)")
    party_b_privilege_score: float = Field(..., ge=0.0, le=1.0)
    bias_detected: bool = Field(..., description="Whether a significant imbalance was detected")
    bias_direction: Optional[Literal["party_a", "party_b", "neutral"]] = None
    normalization_applied: bool = Field(default=False, description="Whether the LLM was instructed to compensate")
    note: str = Field(..., description="Human-readable explanation of the fairness analysis")


class PartyExtraction(BaseModel):
    key_claims: List[str] = Field(default_factory=list)
    amounts_mentioned: List[str] = Field(default_factory=list)
    dates_mentioned: List[str] = Field(default_factory=list)
    evidence_mentioned: List[str] = Field(default_factory=list)
    tone: str = Field(default="neutral")
    evidence_strength_score: float = Field(default=0.5, ge=0.0, le=1.0)
    primary_legal_issue: str = Field(default="")


class MediationReport(BaseModel):
    dispute_id: str
    points_of_agreement: List[AgreementPoint] = Field(default_factory=list)
    points_of_conflict: List[ConflictPoint] = Field(default_factory=list)
    settlement_range: SettlementRange
    proposed_settlement: str = Field(..., description="The AI mediator's proposed resolution")
    proposed_settlement_rationale: str = Field(..., description="Why this settlement is fair")
    applicable_laws: List[str] = Field(default_factory=list)
    fairness_audit: FairnessAudit
    similar_precedents: List[Dict[str, Any]] = Field(default_factory=list)  # each: {case_name, case_type, summary, outcome, similarity, llm_title, llm_description, llm_laws_cited, llm_decision}
    next_steps: List[str] = Field(default_factory=list)
    generated_at: datetime
    model_version: str = Field(default="llm_only_v1")


# ─── Response Models ───────────────────────────────────────────────────────────

class CreateDisputeResponse(BaseModel):
    dispute_id: str
    status: MediationStatus
    invite_code: str = Field(..., description="Share this code with the other party so they can join")
    message: str
    created_at: datetime


class DisputeStatusResponse(BaseModel):
    dispute_id: str
    status: MediationStatus
    case_type: str
    jurisdiction: str
    party_a_submitted: bool
    party_b_submitted: bool
    party_b_joined: bool
    is_party_a: bool = True
    created_at: datetime
    completed_at: Optional[datetime] = None


class MediationResultResponse(BaseModel):
    dispute_id: str
    status: MediationStatus
    report: Optional[MediationReport] = None
    message: str


class UserDisputeListItem(BaseModel):
    dispute_id: str
    invite_code: str
    status: MediationStatus
    case_type: str
    role: Literal["party_a", "party_b"]
    created_at: datetime
    completed_at: Optional[datetime] = None
