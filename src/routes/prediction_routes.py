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
from src.models.db_models import CasePrediction

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
        
        prediction = PredictionHistoryService.save_prediction(
            user_id=current_user.user_id,
            case_type=request.case_type,
            description=request.description,
            jurisdiction=request.jurisdiction,
            predicted_verdict=request.predicted_verdict,
            confidence_score=request.confidence_score,
            legal_references=request.legal_references or [],
            impact_score=request.impact_score,
            analysis_details=request.analysis_details or {}
        )
        
        if not prediction:
            logger.error(f"[PRED] Failed to save prediction for {current_user.user_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save prediction"
            )
        
        logger.info(f"[PRED] Prediction saved: {prediction.id}")
        
        return PredictionResponse(
            _id=str(prediction.id),
            user_id=str(prediction.user_id),
            case_type=prediction.case_type,
            description=prediction.description,
            jurisdiction=prediction.jurisdiction,
            predicted_verdict=prediction.predicted_verdict,
            confidence_score=prediction.confidence_score,
            legal_references=prediction.legal_references,
            impact_score=prediction.impact_score,
            analysis_details=prediction.analysis_details,
            created_at=prediction.created_at,
            updated_at=prediction.updated_at
        )
        
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
            limit=limit
        )
        
        result = []
        for pred in predictions:
            result.append(PredictionResponse(
                _id=str(pred.id),
                user_id=str(pred.user_id),
                case_type=pred.case_type,
                description=pred.description,
                jurisdiction=pred.jurisdiction,
                predicted_verdict=pred.predicted_verdict,
                confidence_score=pred.confidence_score,
                legal_references=pred.legal_references,
                impact_score=pred.impact_score,
                analysis_details=pred.analysis_details,
                created_at=pred.created_at,
                updated_at=pred.updated_at
            ))
        
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
        
        return PredictionResponse(
            _id=str(prediction.id),
            user_id=str(prediction.user_id),
            case_type=prediction.case_type,
            description=prediction.description,
            jurisdiction=prediction.jurisdiction,
            predicted_verdict=prediction.predicted_verdict,
            confidence_score=prediction.confidence_score,
            legal_references=prediction.legal_references,
            impact_score=prediction.impact_score,
            analysis_details=prediction.analysis_details,
            created_at=prediction.created_at,
            updated_at=prediction.updated_at
        )
        
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
        
        # Build search query
        search_query = {"user_id": current_user.user_id}
        
        if case_type:
            search_query["case_type"] = case_type
        if verdict:
            search_query["predicted_verdict"] = verdict
        if jurisdiction:
            search_query["jurisdiction"] = jurisdiction
        if min_confidence is not None:
            search_query["confidence_score"] = {"$gte": min_confidence}
        
        # Perform search using service method or direct query
        predictions = PredictionHistoryService.search_predictions(search_query)
        
        result = []
        for pred in predictions:
            result.append(PredictionResponse(
                _id=str(pred.id),
                user_id=str(pred.user_id),
                case_type=pred.case_type,
                description=pred.description,
                jurisdiction=pred.jurisdiction,
                predicted_verdict=pred.predicted_verdict,
                confidence_score=pred.confidence_score,
                legal_references=pred.legal_references,
                impact_score=pred.impact_score,
                analysis_details=pred.analysis_details,
                created_at=pred.created_at,
                updated_at=pred.updated_at
            ))
        
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
