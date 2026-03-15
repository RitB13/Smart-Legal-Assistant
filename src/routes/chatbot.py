from fastapi import APIRouter, HTTPException, status, Request
from src.models.query_model import QueryRequest, QueryResponse, ImpactScoreModel
from src.services.llm_service import get_legal_response
from src.services.parser import parse_llm_output
from src.services.language_service import detect_language, get_language_name
from src.services.feedback_processor import FeedbackProcessor, ScoreFeedback, ScoreFeedbackResponse
from src.services.smart_mode_router import get_smart_mode_router, ModeRecommendation
import logging
import uuid
import time

logger = logging.getLogger(__name__)
router = APIRouter()
smart_router = get_smart_mode_router()


@router.post("/detect-mode")
def detect_query_mode(req: QueryRequest, request: Request):
    """
    Phase 3: Smart mode detection endpoint.
    Analyzes a query and recommends the most appropriate mode.
    
    Modes:
    - 'chat': Traditional chatbot for legal advice about existing situations
    - 'predict': ML-based case outcome prediction
    - 'simulate': Consequence simulator for planned actions
    
    Args:
        req: QueryRequest with query text and optional language
        request: HTTP request object
        
    Returns:
        Mode recommendation with confidence and reasoning
    """
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    try:
        logger.info(f"[{request_id}] Mode detection requested: {req.query[:80]}...")
        
        # Detect language if not provided
        language = req.language or detect_language(req.query)
        if not language:
            language = "en"
        
        # Get mode recommendation from smart router
        result = smart_router.route_query(
            req.query,
            language=language,
            session_id=None  # Optional: client can provide session_id
        )
        
        recommendation = result.mode_recommendation
        
        response = {
            "request_id": request_id,
            "suggested_mode": recommendation.primary_mode,
            "confidence": recommendation.confidence,
            "confidence_tier": recommendation.confidence_tier,
            "alternative_modes": recommendation.alternative_modes,
            "reasoning": recommendation.reasoning,
            "extracted_action": recommendation.extracted_action,
            "needs_context": result.needs_context,
            "language": language,
            "processing_time_ms": (time.time() - start_time) * 1000
        }
        
        logger.info(
            f"[{request_id}] Mode detected: {recommendation.primary_mode} "
            f"({recommendation.confidence:.0%} confidence)"
        )
        
        return response
        
    except Exception as e:
        elapsed = time.time() - start_time
        logger.exception(f"[{request_id}] Error in mode detection after {elapsed:.2f}s: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to detect mode. Please try again."
        )


@router.post("/query", response_model=QueryResponse, status_code=200)
def handle_query(req: QueryRequest, request: Request) -> QueryResponse:
    """
    Process a legal chatbot query and return structured response.
    
    Simple pipeline:
    1. Detect language from query
    2. Call LLM for legal analysis
    3. Parse response
    4. Return summary, laws, and suggestions
    
    Args:
        req: QueryRequest containing the user's legal question and optional language code
        request: HTTP request object
        
    Returns:
        QueryResponse with summary, laws, and suggestions
        
    Raises:
        HTTPException: For various error conditions during processing
    """
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    try:
        logger.info(f"[{request_id}] New chatbot query received: {req.query[:80]}...")
        
        # Detect language
        if req.language:
            language = req.language.lower()
            logger.info(f"[{request_id}] Language: {language} (provided)")
        else:
            language = detect_language(req.query)
            logger.info(f"[{request_id}] Language auto-detected: {language}")
        
        # Phase 3: Smart mode detection
        logger.debug(f"[{request_id}] Detecting query mode...")
        mode_result = smart_router.route_query(
            req.query,
            language=language,
            session_id=None
        )
        mode_rec = mode_result.mode_recommendation
        
        logger.info(
            f"[{request_id}] Query mode: {mode_rec.primary_mode} "
            f"({mode_rec.confidence:.0%} confidence)"
        )
        
        # Call LLM for legal analysis
        logger.debug(f"[{request_id}] Calling LLM service...")
        raw_output = get_legal_response(req.query, language=language)
        
        # Parse LLM response
        logger.debug(f"[{request_id}] Parsing LLM response...")
        parsed = parse_llm_output(raw_output)
        
        # Add required metadata
        parsed["request_id"] = request_id
        parsed["language"] = language
        
        # Add mode information
        parsed["suggested_mode"] = mode_rec.primary_mode
        parsed["mode_confidence"] = mode_rec.confidence
        parsed["mode_reasoning"] = mode_rec.reasoning
        parsed["extracted_action"] = mode_rec.extracted_action
        
        # Provide default impact score (required by QueryResponse model)
        if "impact_score" not in parsed or parsed["impact_score"] is None:
            parsed["impact_score"] = ImpactScoreModel(
                overall_score=0,
                financial_risk_score=0,
                legal_exposure_score=0,
                long_term_impact_score=0,
                rights_lost_score=0,
                risk_level="Assessment not performed",
                breakdown={"note": "This is a chatbot response without detailed impact analysis"},
                key_factors=[],
                mitigating_factors=[],
                recommendation="Please consult with a legal professional for detailed analysis"
            )
        
        # Log completion
        elapsed = time.time() - start_time
        logger.info(f"[{request_id}] Query processed successfully in {elapsed:.2f}s")
        
        # Return response
        response = QueryResponse(**parsed)
        return response
        
    except Exception as e:
        elapsed = time.time() - start_time
        logger.exception(f"[{request_id}] Error after {elapsed:.2f}s: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing your query. Please try again."
        )


# Initialize feedback processor
feedback_processor = FeedbackProcessor()


@router.post("/feedback/score", response_model=ScoreFeedbackResponse, status_code=200)
def submit_score_feedback(feedback: ScoreFeedback) -> ScoreFeedbackResponse:
    """
    Submit user feedback on impact score accuracy.
    Helps improve the scoring algorithm through continuous learning.
    
    Args:
        feedback: ScoreFeedback with rating (1-5) and optional comment
        
    Returns:
        Confirmation of feedback submission
    """
    try:
        logger.info(
            f"Received score feedback for request {feedback.request_id}: "
            f"rating={feedback.user_rating}/5, type={feedback.feedback_type}"
        )
        
        result = feedback_processor.submit_feedback(feedback)
        
        return ScoreFeedbackResponse(
            status=result["status"],
            message=result["message"]
        )
        
    except Exception as e:
        logger.error(f"Failed to process feedback: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit feedback. Please try again."
        )


@router.get("/feedback/analysis", status_code=200)
def get_feedback_analysis():
    """
    Get analysis of user feedback patterns.
    Shows how well the scoring algorithm is performing and improvement areas.
    
    Returns:
        Analysis of feedback patterns and insights
    """
    try:
        logger.info("Retrieving feedback analysis...")
        analysis = feedback_processor.get_analysis()
        return analysis
        
    except Exception as e:
        logger.error(f"Failed to retrieve feedback analysis: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve feedback analysis."
        )
