"""
Legal Consequence Simulator Models
Pydantic models for consequence simulation feature
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class RiskLevelEnum(str, Enum):
    """Risk level enumeration"""
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class PenaltyType(str, Enum):
    """Type of penalty"""
    CIVIL = "civil"
    CRIMINAL = "criminal"
    FINANCIAL = "financial"
    IMPRISONMENT = "imprisonment"
    ADMINISTRATIVE = "administrative"


class Penalty(BaseModel):
    """Detailed penalty information"""
    penalty_type: PenaltyType = Field(..., description="Type of penalty")
    description: str = Field(..., description="Description of the penalty")
    severity: str = Field(..., description="Severity level (minor, moderate, severe, critical)")
    minimum: Optional[str] = Field(None, description="Minimum penalty (e.g., 'no fine')")
    maximum: Optional[str] = Field(None, description="Maximum penalty (e.g., '7 years imprisonment')")
    typical_range: Optional[str] = Field(None, description="Typical range based on precedents")
    applicable_law: Optional[str] = Field(None, description="Applicable law section")
    
    class Config:
        json_schema_extra = {
            "example": {
                "penalty_type": "criminal",
                "description": "Imprisonment and/or fine",
                "severity": "severe",
                "maximum": "3 years imprisonment + ₹50,000 fine",
                "applicable_law": "IT Act 2000, Section 66"
            }
        }


class SaferAlternative(BaseModel):
    """A safer alternative to the planned action"""
    alternative: str = Field(..., description="The safer alternative action")
    explanation: str = Field(..., description="Why this is safer")
    requirement: Optional[str] = Field(None, description="Any requirement or precaution")
    legal_basis: Optional[str] = Field(None, description="Legal basis for this recommendation")
    
    class Config:
        json_schema_extra = {
            "example": {
                "alternative": "Obtain written consent before recording",
                "explanation": "This eliminates all privacy law violations",
                "requirement": "Get signed consent from all call parties",
                "legal_basis": "Privacy law, consent requirement"
            }
        }


class RiskFactor(BaseModel):
    """A specific risk factor in the planned action"""
    factor: str = Field(..., description="The risk factor")
    severity: str = Field(..., description="How severe is this risk (minor, moderate, severe, critical)")
    mitigation: Optional[str] = Field(None, description="How to mitigate this risk")
    applicable_law: Optional[str] = Field(None, description="Applicable law")


class ApplicableLaw(BaseModel):
    """Applicable law for the consequence simulation"""
    law_id: str = Field(..., description="Unique law identifier (e.g., IPC_420)")
    name: str = Field(..., description="Name of the law")
    section: Optional[str] = Field(None, description="Specific section (e.g., Section 420)")
    jurisdiction: str = Field(..., description="Jurisdiction (India, USA, etc.)")
    description: str = Field(..., description="What this law covers")
    relevance: str = Field(..., description="Relevance to the action (high, medium, low)")
    url: Optional[str] = Field(None, description="Link to statute")
    statute_text: Optional[str] = Field(None, description="Excerpt from statute")
    
    class Config:
        json_schema_extra = {
            "example": {
                "law_id": "IPC_66C",
                "name": "Violation of Privacy",
                "section": "IT Act 2000 Section 66C",
                "jurisdiction": "India",
                "description": "Punishment for identity theft",
                "relevance": "high"
            }
        }


class PrecautionStep(BaseModel):
    """Precaution step to minimize legal risk"""
    step_number: int = Field(..., description="Step number (1, 2, 3...)")
    action: str = Field(..., description="Main action to take")
    details: List[str] = Field(default_factory=list, description="Sub-steps")
    priority: str = Field(..., description="Priority (critical, high, medium, low)")
    timeline: str = Field(..., description="When to do this (immediately, within 1 week, etc.)")
    reason: Optional[str] = Field(None, description="Why this precaution is needed")
    reference_law: Optional[str] = Field(None, description="Applicable law")
    
    class Config:
        json_schema_extra = {
            "example": {
                "step_number": 1,
                "action": "Obtain written consent",
                "details": ["Email all parties", "Get signed acknowledgment"],
                "priority": "critical",
                "timeline": "before recording",
                "reason": "Required by privacy law"
            }
        }


class PlannedActionInput(BaseModel):
    """User input for consequence simulation"""
    action_description: str = Field(
        ..., 
        min_length=10, 
        description="Description of the planned action (min 10 chars)"
    )
    jurisdiction: Optional[str] = Field("India", description="Jurisdiction")
    state: Optional[str] = Field(None, description="State/region within jurisdiction")
    context: Optional[str] = Field(None, description="Additional context")
    language: Optional[str] = Field("en", description="Language of input")
    
    class Config:
        json_schema_extra = {
            "example": {
                "action_description": "I want to record a phone call with my business partner to document an agreement we discussed",
                "jurisdiction": "India",
                "state": "Delhi",
                "context": "This is for a business dispute resolution",
                "language": "en"
            }
        }


class ConsequenceSimulationResult(BaseModel):
    """Complete consequence simulation result"""
    
    # Identification
    simulation_id: str = Field(..., description="Unique simulation ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When simulation was run")
    
    # Risk Assessment
    risk_level: RiskLevelEnum = Field(..., description="Overall risk level")
    confidence_score: float = Field(
        ..., 
        ge=0.0, 
        le=1.0, 
        description="Confidence in analysis (0.0-1.0)"
    )
    
    # Action Summary
    action_analyzed: str = Field(..., description="The action that was analyzed")
    jurisdiction: str = Field(..., description="Jurisdiction analyzed")
    
    # Legal Analysis
    applicable_laws: List[ApplicableLaw] = Field(
        default_factory=list, 
        description="Laws applicable to this action"
    )
    penalties: List[Penalty] = Field(
        default_factory=list, 
        description="Potential penalties"
    )
    civil_exposure: Optional[str] = Field(None, description="Civil law exposure")
    criminal_exposure: Optional[str] = Field(None, description="Criminal law exposure")
    
    # Risk Breakdown
    key_risks: List[RiskFactor] = Field(
        default_factory=list, 
        description="Top 3-5 risk factors"
    )
    
    # Alternatives & Precautions
    safer_alternatives: List[SaferAlternative] = Field(
        default_factory=list, 
        description="Safer alternatives to the action"
    )
    precautions_checklist: List[PrecautionStep] = Field(
        default_factory=list, 
        description="Steps to minimize legal risk if proceeding"
    )
    
    # Explanations
    explanation: str = Field(..., description="Why this action is risky")
    jurisdiction_specific_notes: Optional[str] = Field(
        None, 
        description="Jurisdiction-specific considerations"
    )
    
    # Metadata
    language: str = Field(default="en", description="Language of response")
    
    class Config:
        json_schema_extra = {
            "example": {
                "simulation_id": "sim_abc123def456",
                "risk_level": "Medium",
                "confidence_score": 0.85,
                "action_analyzed": "Record a phone call",
                "jurisdiction": "India",
                "applicable_laws": [
                    {
                        "law_id": "IT_ACT_2000_66C",
                        "name": "Privacy Violation",
                        "section": "Section 66C",
                        "jurisdiction": "India",
                        "description": "Unauthorized access to privacy",
                        "relevance": "high"
                    }
                ],
                "penalties": [
                    {
                        "penalty_type": "criminal",
                        "description": "Imprisonment and/or fine",
                        "severity": "moderate",
                        "maximum": "3 years imprisonment + ₹50,000"
                    }
                ],
                "key_risks": [
                    {
                        "factor": "Recording without consent",
                        "severity": "critical",
                        "mitigation": "Get written consent from all parties"
                    }
                ],
                "safer_alternatives": [
                    {
                        "alternative": "Obtain written consent",
                        "explanation": "Eliminates privacy law violations",
                        "requirement": "Get signed acknowledgment"
                    }
                ],
                "explanation": "Recording without consent violates India's privacy laws..."
            }
        }


class SimulationFeedback(BaseModel):
    """User feedback on a simulation"""
    simulation_id: str = Field(..., description="ID of the simulation")
    helpful: bool = Field(..., description="Was this simulation helpful?")
    rating: Optional[int] = Field(None, ge=1, le=5, description="Rating (1-5)")
    comments: Optional[str] = Field(None, description="Additional comments")
    user_took_action: Optional[bool] = Field(None, description="Did user take the action?")
    actual_outcome: Optional[str] = Field(None, description="What actually happened?")
    
    class Config:
        json_schema_extra = {
            "example": {
                "simulation_id": "sim_abc123",
                "helpful": True,
                "rating": 5,
                "comments": "Very helpful! Made me realize the risks"
            }
        }


class SimulatorDetectionResult(BaseModel):
    """Result of detecting if query is for simulator"""
    is_simulator_query: bool = Field(..., description="Whether this is a simulator query")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence (0.0-1.0)")
    extracted_action: Optional[str] = Field(None, description="Extracted planned action")
    reasoning: Optional[str] = Field(None, description="Why we think this is/isn't a simulator query")
    suggested_mode: str = Field(..., description="Suggested mode: 'chat', 'predict', or 'simulate'")
