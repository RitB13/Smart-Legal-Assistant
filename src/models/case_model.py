from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime


class CaseInputModel(BaseModel):
    """Input model for case outcome prediction."""
    case_name: str = Field(..., description="Name of the legal case")
    case_type: str = Field(
        ..., 
        description="Type of case (appeal, writ_petition, property_dispute, criminal_complaint, etc.)"
    )
    year: int = Field(..., ge=1950, le=2100, description="Year the case was filed")
    jurisdiction_state: str = Field(..., description="State jurisdiction (e.g., 'Delhi', 'Maharashtra')")
    damages_awarded: Optional[float] = Field(None, ge=0, description="Damages awarded (in rupees)")
    parties_count: Optional[int] = Field(None, ge=1, description="Number of parties involved")
    is_appeal: Optional[bool] = Field(False, description="Whether this case is an appeal")
    legal_representation: Optional[str] = Field(
        "unknown",
        description="Legal representation status (both_sides, claimant_only, defendant_only, none, unknown)"
    )
    number_of_parties: Optional[int] = Field(
        2,
        ge=1,
        le=10,
        description="Number of parties involved in the case (1-10)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "case_name": "State v. John Doe - Criminal Appeal",
                "case_type": "appeal",
                "year": 2023,
                "jurisdiction_state": "Delhi",
                "damages_awarded": 500000,
                "parties_count": 2,
                "is_appeal": True,
                "legal_representation": "both_sides",
                "number_of_parties": 2
            }
        }


class PredictionConfidence(BaseModel):
    """Confidence level categorization."""
    level: str = Field(..., description="Confidence level (very_high, high, medium, low)")
    score: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0.0-1.0)")
    interpretation: str = Field(..., description="Human-readable interpretation")


class SHAPExplanation(BaseModel):
    """SHAP-based model explanation."""
    model_config = ConfigDict(protected_namespaces=())
    
    top_positive_features: List[Dict[str, Any]] = Field(
        ..., 
        description="Top features that increased prediction confidence"
    )
    top_negative_features: List[Dict[str, Any]] = Field(
        ..., 
        description="Top features that decreased prediction confidence"
    )
    feature_impact_summary: str = Field(
        ..., 
        description="Summary of how features influenced the prediction"
    )
    model_certainty: float = Field(
        ..., 
        ge=0.0, 
        le=1.0, 
        description="Model's certainty about the prediction (0.0-1.0)"
    )


class SimilarCase(BaseModel):
    """Similar case reference from historical data."""
    case_id: str = Field(..., description="Unique identifier for similar case")
    case_name: str = Field(..., description="Name of the similar case")
    case_type: str = Field(..., description="Type of similar case")
    year: int = Field(..., description="Year of similar case")
    verdict: str = Field(..., description="Verdict in similar case")
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Similarity to input case (0.0-1.0)")
    jurisdiction: str = Field(..., description="Jurisdiction of similar case")


class VerdictProbabilities(BaseModel):
    """Probability distribution across all possible verdicts."""
    accepted: float = Field(..., ge=0.0, le=1.0, description="Probability of Accepted verdict")
    acquitted: float = Field(..., ge=0.0, le=1.0, description="Probability of Acquitted verdict")
    convicted: float = Field(..., ge=0.0, le=1.0, description="Probability of Convicted verdict")
    other: float = Field(..., ge=0.0, le=1.0, description="Probability of Other verdict")
    rejected: float = Field(..., ge=0.0, le=1.0, description="Probability of Rejected verdict")
    settlement: float = Field(..., ge=0.0, le=1.0, description="Probability of Settlement verdict")
    unknown: float = Field(..., ge=0.0, le=1.0, description="Probability of Unknown verdict")


class CaseOutcomePredictionResponse(BaseModel):
    """Complete response for case outcome prediction."""
    prediction_id: str = Field(..., description="Unique ID for this prediction (tracking)")
    case_summary: Dict[str, Any] = Field(..., description="Echo of input case data")
    verdict: str = Field(..., description="Predicted verdict (Accepted, Acquitted, Convicted, Other, Rejected, Settlement, Unknown)")
    verdict_id: int = Field(..., ge=0, le=6, description="Verdict class ID (0-6)")
    probability: float = Field(..., ge=0.0, le=1.0, description="Probability of predicted verdict")
    confidence: PredictionConfidence = Field(..., description="Confidence assessment (how certain is the model about this prediction)")
    risk_level: str = Field(..., description="Semantic risk level for the client (very_high, high, medium, low) - based on verdict type AND confidence")
    verdict_probabilities: VerdictProbabilities = Field(..., description="Probability distribution across all verdicts")
    explanation: SHAPExplanation = Field(..., description="Model explainability using SHAP")
    similar_cases: List[SimilarCase] = Field(default_factory=list, description="Most similar historical cases")
    risk_assessment: Dict[str, Any] = Field(..., description="Risk assessment based on prediction")
    recommendations: List[str] = Field(default_factory=list, description="Recommendations based on prediction")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When prediction was made")
    
    class Config:
        json_schema_extra = {
            "example": {
                "prediction_id": "pred_123456",
                "case_summary": {
                    "case_name": "State v. John Doe",
                    "case_type": "appeal",
                    "year": 2023,
                    "jurisdiction_state": "Delhi"
                },
                "verdict": "Accepted",
                "verdict_id": 0,
                "probability": 0.87,
                "confidence": {
                    "level": "high",
                    "score": 0.87,
                    "interpretation": "Model is quite confident about this prediction"
                },
                "verdict_probabilities": {
                    "accepted": 0.87,
                    "acquitted": 0.02,
                    "convicted": 0.03,
                    "other": 0.05,
                    "rejected": 0.02,
                    "settlement": 0.01,
                    "unknown": 0.00
                },
                "explanation": {
                    "top_positive_features": [
                        {"feature": "case_name_length", "impact": 0.15},
                        {"feature": "year", "impact": 0.10}
                    ],
                    "top_negative_features": [],
                    "feature_impact_summary": "Case name length and filing year were the main drivers",
                    "model_certainty": 0.87
                },
                "similar_cases": [
                    {
                        "case_id": "case_001",
                        "case_name": "Similar Case 1",
                        "case_type": "appeal",
                        "year": 2022,
                        "verdict": "Accepted",
                        "similarity_score": 0.92,
                        "jurisdiction": "Delhi"
                    }
                ],
                "risk_assessment": {
                    "overall_risk": "medium",
                    "key_risks": ["Precedent exists for opposite verdict"],
                    "success_probability": 0.87
                },
                "recommendations": [
                    "File within statutory timeline",
                    "Gather supporting documents"
                ],
                "timestamp": "2026-03-15T10:30:45.123Z"
            }
        }


class BatchPredictionRequest(BaseModel):
    """Request for batch predictions on multiple cases."""
    cases: List[CaseInputModel] = Field(..., min_items=1, max_items=100, description="List of cases to predict")
    include_explanations: bool = Field(
        False, 
        description="Whether to include SHAP explanations (slower but more detailed)"
    )
    include_similar_cases: bool = Field(
        False, 
        description="Whether to fetch similar cases (slower but more useful)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "cases": [
                    {
                        "case_name": "Case 1",
                        "case_type": "appeal",
                        "year": 2023,
                        "jurisdiction_state": "Delhi"
                    },
                    {
                        "case_name": "Case 2",
                        "case_type": "criminal_complaint",
                        "year": 2024,
                        "jurisdiction_state": "Maharashtra"
                    }
                ],
                "include_explanations": False,
                "include_similar_cases": False
            }
        }


class BatchPredictionResponse(BaseModel):
    """Response for batch predictions."""
    batch_id: str = Field(..., description="Unique batch ID for tracking")
    total_cases: int = Field(..., description="Total number of cases processed")
    successful_predictions: int = Field(..., description="Number of successful predictions")
    failed_predictions: int = Field(..., description="Number of failed predictions")
    predictions: List[Dict[str, Any]] = Field(..., description="List of prediction results")
    errors: List[Dict[str, Any]] = Field(default_factory=list, description="List of errors if any")
    processing_time_seconds: float = Field(..., description="Total processing time in seconds")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When batch was processed")


class HealthCheckResponse(BaseModel):
    """Health check response for case outcome service."""
    model_config = ConfigDict(protected_namespaces=())
    
    status: str = Field(..., description="Service status (healthy, degraded, unhealthy)")
    model_loaded: bool = Field(..., description="Whether prediction model is loaded")
    model_version: str = Field(..., description="Version of the prediction model")
    features_available: int = Field(..., description="Number of features available")
    last_update: str = Field(..., description="Last time model was updated")
    message: str = Field(..., description="Status message")
