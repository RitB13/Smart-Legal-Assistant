from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid


class JurisdictionInfo(BaseModel):
    """Information about the legal jurisdiction."""
    country: str = Field(..., description="Country jurisdiction (e.g., 'India', 'USA')")
    state_or_region: str = Field(..., description="State or region jurisdiction")
    detected_method: str = Field(
        ..., 
        description="How jurisdiction was detected (user_input, browser_language, ip_geolocation, default)"
    )
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence level of detection (0.0-1.0)")


class LegalReference(BaseModel):
    """Reference to a specific law or statute."""
    law_id: str = Field(..., description="Unique identifier for the law (e.g., 'IPC_498A')")
    name: str = Field(..., description="Name of the law or statute")
    section: Optional[str] = Field(None, description="Specific section or clause (e.g., 'Section 420')")
    jurisdiction: str = Field(..., description="Applicable jurisdiction for this law")
    statute_text: Optional[str] = Field(None, description="Text excerpt from the statute")
    url: Optional[str] = Field(None, description="URL to the full statute")
    relevance: str = Field(..., description="Relevance level (high, medium, low)")
    relevance_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Relevance score (0.0-1.0)")


class ScoreComponent(BaseModel):
    """Breakdown of a single score component."""
    component_name: str = Field(..., description="Name of the score component")
    score: int = Field(..., ge=0, le=100, description="Score for this component (0-100)")
    formula: Optional[str] = Field(None, description="Formula used to calculate this component")
    factors: List[str] = Field(default_factory=list, description="Factors contributing to this score")
    referenced_laws: List[LegalReference] = Field(default_factory=list, description="Laws supporting this score")


class ChecklistItem(BaseModel):
    """Single item in an action checklist."""
    step_number: int = Field(..., description="Step number in checklist (1, 2, 3, ...)")
    action: str = Field(..., description="Main action to take")
    details: List[str] = Field(default_factory=list, description="Detailed sub-steps for this action")
    priority: str = Field(
        ..., 
        description="Priority level (critical, high, medium, low)"
    )
    timeline: str = Field(..., description="Recommended timeline (e.g., 'within 1 week', 'immediately')")
    reference_law: Optional[str] = Field(None, description="Applicable law or statute for this action")


class Checklist(BaseModel):
    """Complete action checklist for the legal issue."""
    issue_type: str = Field(..., description="Type of legal issue (e.g., 'dowry_harassment', 'criminal_complaint')")
    items: List[ChecklistItem] = Field(..., description="Ordered list of checklist items")
    total_items: int = Field(..., description="Total number of items in checklist")
    jurisdiction: str = Field(..., description="Jurisdiction these checklists are for")
    note: Optional[str] = Field(None, description="Additional important note about the checklist")


class DocumentTemplate(BaseModel):
    """Document template available for download."""
    template_id: str = Field(..., description="Unique identifier for template")
    name: str = Field(..., description="User-friendly name of template")
    description: str = Field(..., description="What this template is used for")
    file_format: str = Field(..., description="File format (docx, xlsx, pdf, etc.)")
    jurisdiction: str = Field(..., description="Jurisdiction this template applies to")
    applicable_issues: List[str] = Field(default_factory=list, description="Issues this template is relevant for")
    category: str = Field(..., description="Category (correspondence, documentation, legal_petition, etc.)")
    download_url: Optional[str] = Field(None, description="URL to download the template")


class ScoreComponentExplanation(BaseModel):
    """Phase 3: Explanation for a single score component"""
    name: str = Field(..., description="Name of score component")
    score: float = Field(..., ge=0, le=100, description="Component score value")
    weight: str = Field(..., description="Weight percentage (e.g., '40%')")
    weighted_contribution: float = Field(..., description="Contribution to overall score")
    explanation: str = Field(..., description="Human-readable explanation of how this score was calculated")
    factors_considered: List[str] = Field(default_factory=list, description="Factors that contributed to this score")
    score_interpretation: str = Field(..., description="What this score level means (Critical/High/Moderate/Low)")


class ScoreExplanation(BaseModel):
    """Phase 3: Complete explanation of score calculation"""
    overview: str = Field(..., description="Overview of overall score meaning")
    components: List[ScoreComponentExplanation] = Field(..., description="Breakdown of each component")
    total_calculation: Dict[str, Any] = Field(..., description="Complete formula and calculation")
    feature_impact: Dict[str, Any] = Field(..., description="Which features most impacted the score")
    key_factors: List[str] = Field(..., description="Key factors driving the overall score")


class LawMatchingExplanation(BaseModel):
    """Phase 3: Explanation for why a law was matched"""
    law_id: str = Field(..., description="Law identifier")
    law_name: str = Field(..., description="Law name")
    relevance_percentage: str = Field(..., description="Relevance percentage")
    why_matched: str = Field(..., description="Explanation of why this law applies")
    keywords_found: List[str] = Field(default_factory=list, description="Keywords from query that matched law")
    applicable_section: str = Field(..., description="Applicable section")
    statute_url: Optional[str] = Field(None, description="URL to law statute")
    severity: str = Field(..., description="Severity level of offense")
    key_penalties: str = Field(..., description="Potential penalties")


class JurisdictionExplanation(BaseModel):
    """Phase 3: Explanation of jurisdiction detection"""
    detected_location: str = Field(..., description="Detected location")
    confidence_level: str = Field(..., description="Confidence percentage")
    detection_method: str = Field(..., description="Method used for detection")
    confidence_interpretation: str = Field(..., description="What confidence level means")
    reasoning: str = Field(..., description="Detailed reasoning for detection")
    signals_evaluated: Dict[str, Any] = Field(..., description="Signals considered")
    legal_significance: str = Field(..., description="Why jurisdiction matters legally")


class ChecklistPriorityExplanation(BaseModel):
    """Phase 3: Explanation for checklist item priority"""
    step: int = Field(..., description="Step number")
    action: str = Field(..., description="Action to take")
    priority: str = Field(..., description="Priority level")
    priority_reasoning: str = Field(..., description="Why this priority was assigned")
    urgency_level: str = Field(..., description="Urgency interpretation with emoji")
    timeline: str = Field(..., description="Recommended timeline")
    legal_basis: Optional[str] = Field(None, description="Legal reference")
    consequence_if_delayed: str = Field(..., description="What happens if delayed")


class AuditEvent(BaseModel):
    """Phase 3: Single event in audit trail"""
    timestamp: str = Field(..., description="ISO timestamp of event")
    type: str = Field(..., description="Type of event")
    description: str = Field(..., description="Human-readable description")
    duration_ms: float = Field(..., description="Duration in milliseconds")
    status: str = Field(..., description="Event status (success/error/partial)")


class AuditTrailSummary(BaseModel):
    """Phase 3: Summary audit trail of processing"""
    request_id: str = Field(..., description="Request identifier")
    total_events: int = Field(..., description="Total number of events logged")
    total_duration_ms: float = Field(..., description="Total processing time")
    event_types: Dict[str, Any] = Field(..., description="Summary of event types")
    events: List[AuditEvent] = Field(..., description="List of events in order")
    

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


class ImpactScoreModel(BaseModel):
    """Legal impact score model with detailed breakdown."""
    overall_score: int = Field(..., ge=0, le=100, description="Overall impact score (0-100)")
    financial_risk_score: int = Field(..., ge=0, le=100, description="Financial risk subscore")
    legal_exposure_score: int = Field(..., ge=0, le=100, description="Legal exposure subscore")
    long_term_impact_score: int = Field(..., ge=0, le=100, description="Long-term impact subscore")
    rights_lost_score: int = Field(..., ge=0, le=100, description="Rights lost subscore")
    
    risk_level: str = Field(..., description="Risk level classification (🔴 Critical, 🟠 High, 🟡 Medium, 🟢 Low)")
    breakdown: Dict[str, str] = Field(..., description="Detailed explanation of each subscore")
    key_factors: List[str] = Field(..., description="Main factors contributing to the score")
    mitigating_factors: List[str] = Field(..., description="Factors that reduce/mitigate risk")
    recommendation: str = Field(..., description="Actionable recommendation for the user")
    
    # NEW: Calculation details for transparency
    calculation_details: Optional[Dict] = Field(None, description="Detailed breakdown of score calculation showing formula and inputs")
    applicable_laws: List[LegalReference] = Field(default_factory=list, description="Laws applied in score calculation")
    
    # NEW (Phase 3): Detailed explanation of score calculation
    score_explanation: Optional[ScoreExplanation] = Field(None, description="Detailed explanation of how score was calculated")
    
    class Config:
        json_schema_extra = {
            "example": {
                "overall_score": 72,
                "financial_risk_score": 80,
                "legal_exposure_score": 70,
                "long_term_impact_score": 65,
                "rights_lost_score": 60,
                "risk_level": "🟠 High",
                "breakdown": {
                    "financial_risk": "Score: 80/100 - Significant financial exposure (50000 rupees at risk)",
                    "legal_exposure": "Score: 70/100 - Legal exposure: multiple laws applicable",
                    "long_term_impact": "Score: 65/100 - Multi-year consequences",
                    "rights_lost": "Score: 60/100 - 1 right(s) affected: Property rights"
                },
                "key_factors": [
                    "High financial exposure: 50000 rupees",
                    "Property rights affected",
                    "Multiple laws applicable"
                ],
                "mitigating_factors": [
                    "Right to appeal available - can challenge verdict"
                ],
                "recommendation": "⚠️ HIGH RISK: Consult lawyer promptly. Document all evidence.",
                "calculation_details": {
                    "formula": "Overall = (Financial × 0.40) + (Legal × 0.30) + (LongTerm × 0.20) + (Rights × 0.10)",
                    "weights": {
                        "financial_risk": "40%",
                        "legal_exposure": "30%",
                        "long_term_impact": "20%",
                        "rights_lost": "10%"
                    },
                    "subscores": {
                        "financial_risk": {"score": 80, "weighted_contribution": 32},
                        "legal_exposure": {"score": 70, "weighted_contribution": 21},
                        "long_term_impact": {"score": 65, "weighted_contribution": 13},
                        "rights_lost": {"score": 60, "weighted_contribution": 6}
                    },
                    "overall_calculation": "(80 × 0.40) + (70 × 0.30) + (65 × 0.20) + (60 × 0.10) = 72"
                },
                "applicable_laws": [
                    {
                        "law_id": "IPC_498A",
                        "name": "Cruelty by husband or his relatives",
                        "section": "Section 498A",
                        "jurisdiction": "India",
                        "relevance": "high",
                        "relevance_score": 0.95
                    }
                ]
            }
        }


class QueryResponse(BaseModel):
    """Response model for legal queries with multilingual support and impact score."""
    summary: str = Field(..., description="Summary of the legal response")
    laws: List[str] = Field(
        default_factory=list, 
        description="List of relevant laws, statutes, or legal references"
    )
    suggestions: List[str] = Field(
        default_factory=list, 
        description="Legal suggestions and recommendations"
    )
    impact_score: ImpactScoreModel = Field(..., description="Legal impact assessment score")
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
    
    # NEW: Jurisdiction information
    jurisdiction: Optional[JurisdictionInfo] = Field(None, description="Jurisdiction context for the response")
    applicable_laws: List[LegalReference] = Field(default_factory=list, description="Specific laws applicable in this jurisdiction")
    
    # NEW: Phase 2 - Actionable steps and templates
    checklist: Optional[Checklist] = Field(None, description="Step-by-step action checklist for this legal issue")
    document_templates: List[DocumentTemplate] = Field(
        default_factory=list, 
        description="Relevant document templates available for download"
    )
    
    # NEW (Phase 3): Explainability and transparency
    law_explanations: List[LawMatchingExplanation] = Field(
        default_factory=list,
        description="Detailed explanations for why each law was matched"
    )
    jurisdiction_explanation: Optional[JurisdictionExplanation] = Field(
        None,
        description="Explanation of how jurisdiction was detected and why it matters"
    )
    checklist_explanations: List[ChecklistPriorityExplanation] = Field(
        default_factory=list,
        description="Explanation for priority levels of checklist items"
    )
    
    # NEW (Phase 3): Audit trail for compliance
    audit_trail: Optional[AuditTrailSummary] = Field(
        None,
        description="Complete audit trail of all processing steps for compliance and transparency"
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
