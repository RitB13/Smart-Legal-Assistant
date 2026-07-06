"""
Prediction Routes - FastAPI endpoints for managing case predictions.

Endpoints:
- POST   /predictions           - Save new prediction
- GET    /predictions           - Get all predictions for user
- GET    /predictions/{id}      - Get specific prediction
- DELETE /predictions/{id}      - Delete prediction
- GET    /predictions/search    - Search predictions by criteria
- GET    /predictions/stats     - Get user's prediction statistics
"""

from fastapi import APIRouter, HTTPException, status, Depends, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from src.routes.auth_routes import get_current_user
from src.services.auth_service import TokenData
from src.services.prediction_history_service import PredictionHistoryService
from src.models.db_models import (
    CasePrediction, CasePredictionCreate, CasePredictionInDB,
    CasePredictionMetadata, PredictionResult as DbPredictionResult,
)

logger = logging.getLogger(__name__)

# Router for prediction endpoints
router = APIRouter(prefix="/predictions", tags=["Predictions"])


# ==================== REQUEST/RESPONSE MODELS ====================

class PredictionCreate(BaseModel):
    """Create prediction request"""
    case_type: str = Field(..., description="Type of legal case")
    description: str = Field(..., description="Case description")
    jurisdiction: str = Field(..., description="Legal jurisdiction")
    predicted_verdict: Optional[str] = None
    confidence_score: Optional[float] = Field(None, ge=0, le=1)
    legal_references: Optional[List[str]] = []
    impact_score: Optional[float] = Field(None, ge=0, le=100)
    analysis_details: Optional[Dict[str, Any]] = {}
    
    class Config:
        json_schema_extra = {
            "example": {
                "case_type": "property_dispute",
                "description": "Property boundary dispute with neighbor",
                "jurisdiction": "india",
                "predicted_verdict": "favorable",
                "confidence_score": 0.85,
                "impact_score": 75.5
            }
        }


class PredictionResponse(BaseModel):
    """Prediction response"""
    id: str = Field(alias="_id")
    user_id: str
    case_type: str
    description: str
    jurisdiction: str
    predicted_verdict: Optional[str] = None
    confidence_score: Optional[float] = None
    legal_references: Optional[List[str]] = []
    impact_score: Optional[float] = None
    analysis_details: Optional[Dict[str, Any]] = {}
    created_at: datetime
    updated_at: datetime
    
    class Config:
        populate_by_name = True


def _to_response(pred: CasePredictionInDB) -> PredictionResponse:
    """Map the service's nested CasePredictionInDB to the flat PredictionResponse."""
    ra = pred.result.risk_assessment or {}
    return PredictionResponse(
        _id=str(pred.id),
        user_id=str(pred.user_id),
        case_type=pred.metadata.case_type,
        description=ra.get("description", pred.metadata.case_name),
        jurisdiction=pred.metadata.jurisdiction_state,
        predicted_verdict=pred.result.verdict,
        confidence_score=round(pred.result.confidence / 100.0, 4) if pred.result.confidence else None,
        legal_references=ra.get("legal_references", []),
        impact_score=ra.get("impact_score"),
        analysis_details={k: v for k, v in ra.items() if k not in ("description", "legal_references", "impact_score")},
        created_at=pred.created_at,
        updated_at=pred.created_at,
    )


class PredictionStatsResponse(BaseModel):
    """Prediction statistics response"""
    total_predictions: int
    by_case_type: Dict[str, int]
    by_verdict: Dict[str, int]
    average_confidence: Optional[float] = None
    average_impact_score: Optional[float] = None


class PredictionSearchRequest(BaseModel):
    """Search predictions request"""
    case_type: Optional[str] = None
    verdict: Optional[str] = None
    jurisdiction: Optional[str] = None
    min_confidence: Optional[float] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "case_type": "property_dispute",
                "verdict": "favorable",
                "min_confidence": 0.7
            }
        }


# ==================== ENDPOINTS ====================

@router.post("", response_model=PredictionResponse, status_code=status.HTTP_201_CREATED)
async def save_prediction(
    request: PredictionCreate,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Save new case prediction for user.
    
    Args:
        request: Prediction details
        current_user: Current authenticated user
        
    Returns:
        PredictionResponse with saved prediction
        
    Example:
        POST /predictions
        {
            "case_type": "property_dispute",
            "description": "Property boundary dispute",
            "jurisdiction": "india",
            "predicted_verdict": "favorable",
            "confidence_score": 0.85,
            "impact_score": 75.5
        }
    """
    try:
        logger.info(f"[PRED] Saving prediction for user {current_user.user_id}")

        pred_data = CasePredictionCreate(
            user_id=current_user.user_id,
            metadata=CasePredictionMetadata(
                case_name=(request.analysis_details or {}).get("relief_sought", request.case_type)[:120],
                case_type=request.case_type,
                year=datetime.utcnow().year,
                jurisdiction_state=request.jurisdiction,
            ),
            result=DbPredictionResult(
                verdict=request.predicted_verdict or "Unknown",
                confidence=round((request.confidence_score or 0.0) * 100, 1),
                probabilities={request.predicted_verdict: request.confidence_score or 0.0} if request.predicted_verdict else {},
                shap_explanation={},
                similar_cases=[],
                risk_assessment={
                    "description": request.description,
                    "legal_references": request.legal_references or [],
                    "impact_score": request.impact_score,
                    **(request.analysis_details or {}),
                },
            ),
        )
        prediction = PredictionHistoryService.save_prediction(pred_data)

        if not prediction:
            logger.error(f"[PRED] Failed to save prediction for {current_user.user_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save prediction"
            )

        logger.info(f"[PRED] Prediction saved: {prediction.id}")
        return _to_response(prediction)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[PRED] Error saving prediction: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save prediction"
        )


@router.get("", response_model=List[PredictionResponse])
async def get_predictions(
    current_user: TokenData = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100)
):
    """
    Get all predictions for authenticated user.
    
    Args:
        current_user: Current authenticated user
        skip: Number of predictions to skip (pagination)
        limit: Maximum number of predictions to return
        
    Returns:
        List of PredictionResponse
        
    Example:
        GET /predictions?skip=0&limit=20
    """
    try:
        logger.info(f"[PRED] Fetching predictions for user {current_user.user_id}")

        predictions = PredictionHistoryService.get_user_predictions(
            user_id=current_user.user_id,
            skip=skip,
            limit=limit,
        )

        result = [_to_response(p) for p in predictions]
        logger.debug(f"[PRED] Retrieved {len(result)} predictions for {current_user.user_id}")
        return result
        
    except Exception as e:
        logger.error(f"[PRED] Error fetching predictions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch predictions"
        )


@router.get("/{prediction_id}", response_model=PredictionResponse)
async def get_prediction(
    prediction_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Get specific prediction by ID.
    
    Args:
        prediction_id: Prediction ID
        current_user: Current authenticated user
        
    Returns:
        PredictionResponse with prediction details
        
    Example:
        GET /predictions/507f1f77bcf86cd799439011
    """
    try:
        logger.info(f"[PRED] Fetching prediction {prediction_id}")
        
        prediction = PredictionHistoryService.get_prediction(prediction_id)
        
        if not prediction:
            logger.warning(f"[PRED] Prediction not found: {prediction_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prediction not found"
            )
        
        # Verify user owns this prediction
        if str(prediction.user_id) != current_user.user_id:
            logger.warning(f"[PRED] Unauthorized access to {prediction_id} by {current_user.user_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        return _to_response(prediction)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[PRED] Error fetching prediction: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch prediction"
        )


@router.delete("/{prediction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_prediction(
    prediction_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Delete prediction.
    
    Args:
        prediction_id: Prediction ID
        current_user: Current authenticated user
        
    Example:
        DELETE /predictions/507f1f77bcf86cd799439011
    """
    try:
        logger.info(f"[PRED] Deleting prediction {prediction_id}")
        
        prediction = PredictionHistoryService.get_prediction(prediction_id)
        
        if not prediction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prediction not found"
            )
        
        # Verify user owns this prediction
        if str(prediction.user_id) != current_user.user_id:
            logger.warning(f"[PRED] Unauthorized delete of {prediction_id} by {current_user.user_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        PredictionHistoryService.delete_prediction(prediction_id)
        
        logger.info(f"[PRED] Prediction deleted: {prediction_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[PRED] Error deleting prediction: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete prediction"
        )


@router.get("/search/results", response_model=List[PredictionResponse])
async def search_predictions(
    current_user: TokenData = Depends(get_current_user),
    case_type: Optional[str] = None,
    verdict: Optional[str] = None,
    jurisdiction: Optional[str] = None,
    min_confidence: Optional[float] = None
):
    """
    Search predictions by criteria.
    
    Args:
        current_user: Current authenticated user
        case_type: Filter by case type
        verdict: Filter by predicted verdict
        jurisdiction: Filter by jurisdiction
        min_confidence: Filter by minimum confidence score
        
    Returns:
        List of matching PredictionResponse
        
    Example:
        GET /predictions/search/results?case_type=property_dispute&verdict=favorable
    """
    try:
        logger.info(f"[PRED] Searching predictions for user {current_user.user_id}")
        
        # Fetch all user predictions then filter in Python
        # (corpus is small per-user, so this is acceptable)
        all_preds = PredictionHistoryService.get_user_predictions(
            user_id=current_user.user_id, skip=0, limit=200
        )

        result = []
        for pred in all_preds:
            if verdict and pred.result.verdict != verdict:
                continue
            if case_type and pred.metadata.case_type != case_type:
                continue
            if jurisdiction and pred.metadata.jurisdiction_state != jurisdiction:
                continue
            if min_confidence is not None:
                conf = pred.result.confidence / 100.0 if pred.result.confidence else 0
                if conf < min_confidence:
                    continue
            result.append(_to_response(pred))

        logger.info(f"[PRED] Found {len(result)} matching predictions")
        return result
        
    except Exception as e:
        logger.error(f"[PRED] Error searching predictions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search predictions"
        )


@router.get("/stats/summary", response_model=PredictionStatsResponse)
async def get_prediction_stats(
    current_user: TokenData = Depends(get_current_user)
):
    """
    Get prediction statistics for user.
    
    Returns statistics about user's predictions including:
    - Total prediction count
    - Count by case type
    - Count by verdict
    - Average confidence score
    - Average impact score
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        PredictionStatsResponse with statistics
        
    Example:
        GET /predictions/stats/summary
    """
    try:
        logger.info(f"[PRED] Fetching stats for user {current_user.user_id}")
        
        stats = PredictionHistoryService.get_user_stats(current_user.user_id)
        
        if not stats:
            # Return empty stats if none found
            return PredictionStatsResponse(
                total_predictions=0,
                by_case_type={},
                by_verdict={},
                average_confidence=None,
                average_impact_score=None
            )
        
        logger.debug(f"[PRED] Retrieved stats for {current_user.user_id}")
        
        return PredictionStatsResponse(
            total_predictions=stats.get("total_predictions", 0),
            by_case_type=stats.get("by_case_type", {}),
            by_verdict=stats.get("by_verdict", {}),
            average_confidence=stats.get("average_confidence"),
            average_impact_score=stats.get("average_impact_score")
        )
        
    except Exception as e:
        logger.error(f"[PRED] Error fetching stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch statistics"
        )
