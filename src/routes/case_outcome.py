from fastapi import APIRouter, HTTPException, status, Request, BackgroundTasks
from src.models.case_model import (
    CaseInputModel,
    CaseOutcomePredictionResponse,
    BatchPredictionRequest,
    BatchPredictionResponse,
    PredictionConfidence,
    SHAPExplanation,
    SimilarCase,
    VerdictProbabilities,
    HealthCheckResponse
)
from src.services.case_outcome_predictor_service import get_predictor_service
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, List

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/case-outcome", tags=["Case Outcome Prediction"])


# ============================================================================
# HEALTH CHECK ENDPOINT
# ============================================================================

@router.get(
    "/health",
    response_model=HealthCheckResponse,
    status_code=200,
    summary="Health Check",
    description="Check if the case outcome prediction service is healthy and ready"
)
def health_check():
    """
    Health check endpoint for case outcome prediction service.
    
    Verifies:
    - Service is running
    - Model is loaded
    - All components are available
    
    Returns:
        HealthCheckResponse with service status
    """
    try:
        service = get_predictor_service()
        model_info = service.get_model_info()
        
        return HealthCheckResponse(
            status="healthy",
            model_loaded=model_info['model_loaded'],
            model_version="1.0",
            features_available=model_info['feature_count'],
            last_update="2026-03-15",
            message="Case outcome prediction service is operational"
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Case outcome prediction service is not available"
        )


# ============================================================================
# SINGLE PREDICTION ENDPOINT
# ============================================================================

@router.post(
    "/predict",
    response_model=CaseOutcomePredictionResponse,
    status_code=200,
    summary="Predict Case Outcome",
    description="Predict the likely outcome of a legal case with detailed explanation"
)
async def predict_case_outcome(
    case_input: CaseInputModel,
    request: Request,
    include_explanation: bool = True,
    include_similar_cases: bool = False
) -> Dict[str, Any]:
    """
    Predict the outcome of a legal case.
    
    This endpoint:
    1. Validates case input
    2. Preprocesses case data into features
    3. Generates prediction using trained LightGBM model
    4. Computes confidence and probabilities
    5. Optionally generates SHAP explanation
    6. Returns comprehensive prediction result
    
    Args:
        case_input: CaseInputModel with case details
        request: HTTP request object
        include_explanation: Whether to include SHAP explanation (slower but more detailed)
        include_similar_cases: Whether to find similar historical cases (requires database)
    
    Returns:
        CaseOutcomePredictionResponse with prediction, confidence, and explanation
    
    Example Request:
        ```json
        {
            "case_name": "State v. John Doe - Criminal Appeal",
            "case_type": "appeal",
            "year": 2023,
            "jurisdiction_state": "Delhi",
            "damages_awarded": 500000,
            "parties_count": 2,
            "is_appeal": true
        }
        ```
    
    Example Response:
        ```json
        {
            "prediction_id": "pred_abc123",
            "case_summary": {"case_name": "State v. John Doe...", ...},
            "verdict": "Accepted",
            "verdict_id": 0,
            "probability": 0.87,
            "confidence": {
                "level": "high",
                "score": 0.87,
                "interpretation": "Model is quite confident..."
            },
            "verdict_probabilities": {
                "accepted": 0.87,
                "acquitted": 0.02,
                ...
            },
            "explanation": {...SHAP analysis...},
            "similar_cases": [...],
            "risk_assessment": {...},
            "recommendations": [...],
            "timestamp": "2026-03-15T..."
        }
        ```
    
    Raises:
        HTTPException 400: Invalid input data
        HTTPException 500: Prediction service error
    """
    prediction_id = f"pred_{str(uuid.uuid4())[:12]}"
    request_time = datetime.utcnow()
    
    try:
        logger.info(f"[{prediction_id}] Prediction request: {case_input.case_name}")
        
        # Get predictor service
        try:
            service = get_predictor_service()
        except Exception as e:
            logger.error(f"[{prediction_id}] Failed to initialize predictor service: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Prediction service temporarily unavailable"
            )
        
        # Convert to dictionary for service
        case_dict = {
            'case_name': case_input.case_name,
            'case_type': case_input.case_type,
            'year': case_input.year,
            'jurisdiction_state': case_input.jurisdiction_state,
            'damages_awarded': case_input.damages_awarded or 0,
            'parties_count': case_input.parties_count or 2,
            'is_appeal': case_input.is_appeal or False,
        }
        
        # Get prediction
        prediction_result = service.predict_outcome(case_dict)
        
        # Get explanation if requested
        explanation_data = None
        if include_explanation:
            explanation_result = service.explain_prediction(case_dict, num_top_features=5)
            explanation_data = SHAPExplanation(
                top_positive_features=explanation_result.get('top_positive_features', []),
                top_negative_features=explanation_result.get('top_negative_features', []),
                feature_impact_summary=explanation_result.get('summary', ''),
                model_certainty=prediction_result.get('probability', 0.5)
            )
        else:
            explanation_data = SHAPExplanation(
                top_positive_features=[],
                top_negative_features=[],
                feature_impact_summary="Explanation not requested",
                model_certainty=prediction_result.get('probability', 0.5)
            )
        
        # Build confidence assessment
        prob = prediction_result['probability']
        if prob > 0.85:
            confidence_level = "very_high"
            interpretation = "Model is very confident about this prediction"
        elif prob > 0.70:
            confidence_level = "high"
            interpretation = "Model is quite confident about this prediction"
        elif prob > 0.55:
            confidence_level = "medium"
            interpretation = "Prediction is somewhat uncertain - multiple outcomes possible"
        else:
            confidence_level = "low"
            interpretation = "Prediction is uncertain - this outcome is not favored"
        
        confidence = PredictionConfidence(
            level=confidence_level,
            score=prob,
            interpretation=interpretation
        )
        
        # Build verdict probabilities
        probs = prediction_result.get('probabilities', {
            'Accepted': 0.0,
            'Acquitted': 0.0,
            'Convicted': 0.0,
            'Other': 0.0,
            'Rejected': 1.0,
            'Settlement': 0.0,
            'Unknown': 0.0
        })
        
        verdict_probabilities = VerdictProbabilities(
            accepted=probs.get('Accepted', 0.0),
            acquitted=probs.get('Acquitted', 0.0),
            convicted=probs.get('Convicted', 0.0),
            other=probs.get('Other', 0.0),
            rejected=probs.get('Rejected', 0.0),
            settlement=probs.get('Settlement', 0.0),
            unknown=probs.get('Unknown', 0.0)
        )
        
        # Risk assessment
        verdict = prediction_result['verdict']
        risk_level = "low" if prob > 0.75 else "medium" if prob > 0.50 else "high"
        risk_assessment = {
            'overall_risk': risk_level,
            'key_risks': _get_risk_factors(verdict, case_dict),
            'success_probability': prob
        }
        
        # Recommendations
        recommendations = _get_recommendations(verdict, case_dict)
        
        # Build response
        response = CaseOutcomePredictionResponse(
            prediction_id=prediction_id,
            case_summary={
                'case_name': case_input.case_name,
                'case_type': case_input.case_type,
                'year': case_input.year,
                'jurisdiction_state': case_input.jurisdiction_state,
                'damages_awarded': case_input.damages_awarded,
                'parties_count': case_input.parties_count,
                'is_appeal': case_input.is_appeal
            },
            verdict=verdict,
            verdict_id=prediction_result['verdict_id'],
            probability=prob,
            confidence=confidence,
            verdict_probabilities=verdict_probabilities,
            explanation=explanation_data,
            similar_cases=_get_similar_cases(verdict, case_dict) if include_similar_cases else [],
            risk_assessment=risk_assessment,
            recommendations=recommendations,
            timestamp=request_time
        )
        
        logger.info(f"[{prediction_id}] ✓ Prediction successful: {verdict} (confidence: {prob:.2%})")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{prediction_id}] ✗ Prediction failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction failed: {str(e)}"
        )


# ============================================================================
# BATCH PREDICTION ENDPOINT
# ============================================================================

@router.post(
    "/predict-batch",
    response_model=BatchPredictionResponse,
    status_code=202,  # Accepted (async processing)
    summary="Batch Predict Case Outcomes",
    description="Predict outcomes for multiple cases at once"
)
async def batch_predict_outcomes(
    batch_request: BatchPredictionRequest,
    request: Request
) -> Dict[str, Any]:
    """
    Predict outcomes for multiple cases in a single batch.
    
    Advantages:
    - More efficient than calling single prediction endpoint multiple times
    - Can optionally skip explanations for speed
    - Returns results for successful cases + errors for failed cases
    
    Args:
        batch_request: BatchPredictionRequest with list of cases
        request: HTTP request object
    
    Returns:
        BatchPredictionResponse with results for all cases
    
    Example Request:
        ```json
        {
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
            "include_explanations": false,
            "include_similar_cases": false
        }
        ```
    
    Raises:
        HTTPException 400: Invalid input or too many cases
        HTTPException 500: Batch processing error
    """
    batch_id = f"batch_{str(uuid.uuid4())[:12]}"
    
    try:
        # Validate batch size
        if len(batch_request.cases) > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 100 cases per batch allowed"
            )
        
        logger.info(f"[{batch_id}] Batch prediction requested: {len(batch_request.cases)} cases")
        
        # Get predictor service
        try:
            service = get_predictor_service()
        except Exception as e:
            logger.error(f"[{batch_id}] Service initialization failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Prediction service temporarily unavailable"
            )
        
        # Convert cases to dictionaries
        cases_dicts = [
            {
                'case_name': case.case_name,
                'case_type': case.case_type,
                'year': case.year,
                'jurisdiction_state': case.jurisdiction_state,
                'damages_awarded': case.damages_awarded or 0,
                'parties_count': case.parties_count or 2,
                'is_appeal': case.is_appeal or False,
            }
            for case in batch_request.cases
        ]
        
        # Run batch prediction
        batch_result = service.batch_predict(
            cases_dicts,
            include_explanations=batch_request.include_explanations,            include_similar_cases=False  # Handle similar cases in routes for better control
        )
        
        # Add similar cases if requested
        if batch_request.include_similar_cases:
            for prediction in batch_result['predictions']:
                verdict = prediction.get('verdict', 'Unknown')
                similar = _get_similar_cases(verdict, {})
                prediction['similar_cases'] = [s.dict() for s in similar]
        
        # Build response
        response = BatchPredictionResponse(
            batch_id=batch_id,
            total_cases=batch_result['total_cases'],
            successful_predictions=batch_result['successful_predictions'],
            failed_predictions=batch_result['failed_predictions'],
            predictions=batch_result['predictions'],
            errors=batch_result['failures'],
            processing_time_seconds=batch_result['processing_time_seconds'],
            timestamp=datetime.utcnow()
        )
        
        logger.info(
            f"[{batch_id}] ✓ Batch complete: {batch_result['successful_predictions']}/"
            f"{batch_result['total_cases']} successful"
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{batch_id}] ✗ Batch prediction failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch prediction failed: {str(e)}"
        )


# ============================================================================
# EXPLANATION ENDPOINT
# ============================================================================

@router.post(
    "/explain",
    status_code=200,
    summary="Explain Prediction",
    description="Get detailed explanation of why a prediction was made"
)
async def explain_prediction(
    case_input: CaseInputModel,
    request: Request
) -> Dict[str, Any]:
    """
    Get detailed SHAP-based explanation for a case prediction.
    
    Shows:
    - Top features that increased prediction confidence
    - Top features that decreased prediction confidence
    - Summary of feature impacts
    - Model's certainty score
    
    Args:
        case_input: CaseInputModel with case details
        request: HTTP request object
    
    Returns:
        Dictionary with explanation details
    """
    explanation_id = f"exp_{str(uuid.uuid4())[:12]}"
    
    try:
        logger.info(f"[{explanation_id}] Explanation requested for: {case_input.case_name}")
        
        # Get predictor service
        service = get_predictor_service()
        
        # Convert to dictionary
        case_dict = {
            'case_name': case_input.case_name,
            'case_type': case_input.case_type,
            'year': case_input.year,
            'jurisdiction_state': case_input.jurisdiction_state,
            'damages_awarded': case_input.damages_awarded or 0,
            'parties_count': case_input.parties_count or 2,
            'is_appeal': case_input.is_appeal or False,
        }
        
        # Get explanation
        explanation = service.explain_prediction(case_dict, num_top_features=10)
        
        response = {
            'explanation_id': explanation_id,
            'case_name': case_input.case_name,
            'case_type': case_input.case_type,
            'jurisdiction': case_input.jurisdiction_state,
            'explanation': {
                'method': explanation.get('method'),
                'top_positive_features': explanation.get('top_positive_features', []),
                'top_negative_features': explanation.get('top_negative_features', []),
                'summary': explanation.get('summary'),
                'feature_count_analyzed': len(explanation.get('top_positive_features', [])) + len(explanation.get('top_negative_features', []))
            },
            'model_certainty': explanation.get('model_certainty'),
            'interpretation': {
                'primary_driver': explanation.get('top_positive_features', [{}])[0].get('feature', 'N/A') if explanation.get('top_positive_features') else 'N/A',
                'confidence_assessment': 'Shows model reasoning using SHAP values' if explanation.get('method') == 'SHAP' else 'Shows model feature importance',
                'details': f"Model analyzed {len(explanation.get('top_positive_features', []))} key features that influenced the prediction."
            },
            'timestamp': datetime.utcnow().isoformat()
        }
        
        logger.info(f"[{explanation_id}] ✓ Explanation generated using {explanation.get('method')}")
        return response
        
    except Exception as e:
        logger.error(f"[{explanation_id}] ✗ Explanation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Explanation generation failed: {str(e)}"
        )


# ============================================================================
# MODEL INFO ENDPOINT
# ============================================================================

@router.get(
    "/model-info",
    status_code=200,
    summary="Get Model Information",
    description="Get details about the prediction model"
)
async def get_model_info(request: Request) -> Dict[str, Any]:
    """
    Get information about the loaded prediction model.
    
    Returns:
        Dictionary with model details including:
        - Model type and version
        - Number of features
        - Available verdict classes
        - Metadata about training
    """
    try:
        service = get_predictor_service()
        info = service.get_model_info()
        
        return {
            'model_type': info['model_type'],
            'model_loaded': info['model_loaded'],
            'feature_count': info['feature_count'],
            'sample_features': info['feature_names'],
            'verdict_classes': info['verdict_classes'],
            'shap_available': info['shap_available'],
            'metadata': info['metadata'],
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get model info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve model information"
        )


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _get_risk_factors(verdict: str, case_dict: Dict[str, Any]) -> List[str]:
    """
    Get risk factors based on predicted verdict and case characteristics.
    
    Args:
        verdict: Predicted verdict
        case_dict: Case information
    
    Returns:
        List of risk factor strings
    """
    risks = []
    
    verdict_risks = {
        'Rejected': ["Case dismissed based on case characteristics", "May need to appeal"],
        'Convicted': ["Criminal conviction likely", "Consider stronger defense strategy"],
        'Other': ["Unclear outcome - more information needed"],
        'Settlement': ["Parties may be inclined to settle"],
        'Accepted': ["Favorable outcome expected", "Proceed with confidence"],
        'Acquitted': ["Strong defense indicated", "Acquittal likely"],
        'Unknown': ["Insufficient information to assess risk"]
    }
    
    risks.extend(verdict_risks.get(verdict, []))
    
    if case_dict.get('damages_awarded', 0) > 1000000:
        risks.append("High damages amount involved")
    
    if case_dict.get('is_appeal'):
        risks.append("This is an appeal - higher legal standards may apply")
    
    return risks


def _get_recommendations(verdict: str, case_dict: Dict[str, Any]) -> List[str]:
    """
    Get recommendations based on predicted verdict.
    
    Args:
        verdict: Predicted verdict
        case_dict: Case information
    
    Returns:
        List of recommendation strings
    """
    recommendations = []
    
    verdict_recommendations = {
        'Rejected': [
            "Review case grounds before filing",
            "Consider alternative dispute resolution",
            "Consult with expert legal counsel"
        ],
        'Convicted': [
            "Prepare strong defense evidence",
            "Consider technical objections",
            "Plan for appeal if necessary"
        ],
        'Accepted': [
            "File within statutory timeline",
            "Gather supporting documentation"
        ],
        'Settlement': [
            "Evaluate settlement terms carefully",
            "Document all agreements"
        ],
        'Acquitted': [
            "Strengthen evidence of innocence",
            "Prepare character witnesses"
        ]
    }
    
    recommendations.extend(
        verdict_recommendations.get(verdict, ["Consult with legal professional"])
    )
    
    return recommendations


def _get_similar_cases(verdict: str, case_dict: Dict[str, Any]) -> List[SimilarCase]:
    """
    Get similar historical cases with similar verdicts and characteristics.
    
    Args:
        verdict: Predicted verdict
        case_dict: Case information
    
    Returns:
        List of similar cases from mock database
    """
    # Mock similar cases database - in production, this would query a real database
    # with vector similarity search or semantic matching
    similar_cases_db = {
        'Accepted': [
            SimilarCase(
                case_id='SC_2023_001',
                case_name='Corporation v. State Authority - Contract Dispute',
                case_type='writ_petition',
                year=2023,
                verdict='Accepted',
                similarity_score=0.92,
                jurisdiction='Karnataka'
            ),
            SimilarCase(
                case_id='SC_2022_045',
                case_name='Sharma v. Municipal Corporation - Public Interest',
                case_type='writ_petition',
                year=2022,
                verdict='Accepted',
                similarity_score=0.87,
                jurisdiction='Delhi'
            ),
            SimilarCase(
                case_id='SC_2023_082',
                case_name='Tech Solutions Ltd v. Government - Administrative Law',
                case_type='appeal',
                year=2023,
                verdict='Accepted',
                similarity_score=0.84,
                jurisdiction='Mumbai'
            )
        ],
        'Rejected': [
            SimilarCase(
                case_id='SC_2023_102',
                case_name='Individual v. State - Property Matter',
                case_type='property_dispute',
                year=2023,
                verdict='Rejected',
                similarity_score=0.88,
                jurisdiction='Tamil Nadu'
            ),
            SimilarCase(
                case_id='SC_2022_067',
                case_name='Sharma v. Bank - Financial Claim',
                case_type='criminal_complaint',
                year=2022,
                verdict='Rejected',
                similarity_score=0.85,
                jurisdiction='Maharashtra'
            )
        ],
        'Settlement': [
            SimilarCase(
                case_id='SC_2023_156',
                case_name='Company A v. Company B - Commercial Dispute',
                case_type='property_dispute',
                year=2023,
                verdict='Settlement',
                similarity_score=0.90,
                jurisdiction='Delhi'
            ),
            SimilarCase(
                case_id='SC_2023_178',
                case_name='Individual v. Individual - Family Matter',
                case_type='divorce_contested',
                year=2023,
                verdict='Settlement',
                similarity_score=0.86,
                jurisdiction='Karnataka'
            )
        ],
        'Acquitted': [
            SimilarCase(
                case_id='SC_2023_203',
                case_name='Defendant v. State - Criminal Case',
                case_type='criminal_complaint',
                year=2023,
                verdict='Acquitted',
                similarity_score=0.89,
                jurisdiction='Delhi'
            )
        ],
        'Convicted': [
            SimilarCase(
                case_id='SC_2023_245',
                case_name='State v. Accused - Criminal Conviction',
                case_type='criminal_complaint',
                year=2023,
                verdict='Convicted',
                similarity_score=0.91,
                jurisdiction='West Bengal'
            )
        ]
    }
    
    # Return top 2-3 similar cases for the predicted verdict
    cases = similar_cases_db.get(verdict, [])
    return cases[:3]  # Return up to 3 most similar cases
