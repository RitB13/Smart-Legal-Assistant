"""
Simulator Routes
API endpoints for consequence simulation
"""

import logging
import time
from fastapi import APIRouter, HTTPException, status, Request
from src.models.simulator_model import (
    PlannedActionInput,
    ConsequenceSimulationResult,
    SimulationFeedback
)
from src.services.consequence_simulator import get_consequence_simulator
from src.services.enhanced_simulator_detection import get_enhanced_simulator_detection
from src.services.audit_trail_service import get_audit_trail_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/consequence-simulator", tags=["Consequence Simulator"])


@router.post(
    "/simulate",
    response_model=ConsequenceSimulationResult,
    status_code=200,
    summary="Simulate Legal Consequences",
    description="Analyze a planned action and simulate its legal consequences"
)
def simulate_consequence(req: PlannedActionInput, request: Request) -> ConsequenceSimulationResult:
    """
    Simulate legal consequences of a planned action.
    
    User provides description of an action they're considering, and the system
    analyzes potential legal consequences, risks, penalties, and safer alternatives.
    
    Args:
        req: PlannedActionInput containing action description and optional context
        request: HTTP request object
        
    Returns:
        ConsequenceSimulationResult with detailed legal analysis
        
    Raises:
        HTTPException: For validation or processing errors
    """
    
    request_id = f"sim_{int(time.time() * 1000)}"
    start_time = time.time()
    
    try:
        logger.info(f"[{request_id}] Consequence simulation requested")
        logger.info(f"[{request_id}] Action: {req.action_description[:80]}...")
        logger.info(f"[{request_id}] Jurisdiction: {req.jurisdiction}")
        
        # Get simulator service
        simulator = get_consequence_simulator()
        
        # Run simulation
        logger.debug(f"[{request_id}] Starting consequence analysis")
        result = simulator.simulate_planned_action(
            action_description=req.action_description,
            jurisdiction=req.jurisdiction,
            state=req.state,
            context=req.context,
            language=req.language
        )
        
        # Log to audit trail
        try:
            audit_service = get_audit_trail_service()
            audit_service.log_event(
                event_type="consequence_simulation",
                description=f"Simulated consequences for: {req.action_description[:100]}",
                details={
                    "simulation_id": result.simulation_id,
                    "risk_level": result.risk_level,
                    "jurisdiction": result.jurisdiction,
                    "confidence": result.confidence_score
                },
                request_id=request_id
            )
        except Exception as e:
            logger.warning(f"[{request_id}] Failed to log audit trail: {str(e)}")
        
        elapsed = time.time() - start_time
        logger.info(f"[{request_id}] Simulation completed in {elapsed:.2f}s")
        logger.info(f"[{request_id}] Risk level: {result.risk_level}, Confidence: {result.confidence_score:.2%}")
        
        return result
    
    except ValueError as e:
        elapsed = time.time() - start_time
        logger.error(f"[{request_id}] Validation error after {elapsed:.2f}s: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid input: {str(e)}"
        )
    
    except Exception as e:
        elapsed = time.time() - start_time
        logger.exception(f"[{request_id}] Error after {elapsed:.2f}s: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while simulating consequences. Please try again."
        )


@router.post(
    "/detect-mode",
    status_code=200,
    summary="Detect Query Mode",
    description="Determine if query is for consequence simulation or regular chatbot"
)
def detect_query_mode(query: str, language: str = "en", request: Request = None):
    """
    Intelligently detect whether a query should use the consequence simulator
    or regular chatbot using enhanced multilingual detection.
    
    Args:
        query: User's query text
        language: Language code (auto-detected if not provided)
        request: HTTP request object
        
    Returns:
        SimulatorDetectionResult with mode suggestion and confidence
    """
    
    try:
        logger.debug(f"Mode detection requested for: {query[:80]}...")
        
        detector = get_enhanced_simulator_detection()
        result = detector.is_simulator_query(query, language)
        
        logger.debug(
            f"Mode detection result: {result.suggested_mode} "
            f"(confidence: {result.confidence:.2%})"
        )
        
        return {
            "is_simulator_query": result.is_simulator_query,
            "confidence": result.confidence,
            "suggested_mode": result.suggested_mode,
            "extracted_action": result.extracted_action,
            "reasoning": result.reasoning
        }
    
    except Exception as e:
        logger.error(f"Mode detection failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to detect query mode"
        )


@router.post(
    "/feedback/{simulation_id}",
    status_code=200,
    summary="Submit Simulation Feedback",
    description="Submit feedback on the quality and usefulness of a simulation"
)
def submit_simulation_feedback(simulation_id: str, feedback: SimulationFeedback):
    """
    Submit user feedback on a simulation result.
    
    This helps improve the simulator over time by learning which simulations
    were actually helpful and how accurate our predictions were.
    
    Args:
        simulation_id: ID of the simulation
        feedback: User's feedback including rating and comments
        
    Returns:
        Success response
    """
    
    try:
        logger.info(f"Feedback received for simulation: {simulation_id}")
        logger.info(f"Rating: {feedback.rating}/5, Helpful: {feedback.helpful}")
        if feedback.comments:
            logger.info(f"Comments: {feedback.comments}")

        # Store feedback in MongoDB 'feedback' collection
        from src.services.database_service import get_database_service
        from src.models.database_models import UserFeedbackModel
        import uuid
        from datetime import datetime

        feedback_id = str(uuid.uuid4())
        feedback_model = UserFeedbackModel(
            feedback_id=feedback_id,
            session_id=None,  # Optionally extract from request if available
            feedback_type="simulation_feedback",
            related_query_id=None,
            related_simulation_id=simulation_id,
            rating=feedback.rating if feedback.rating is not None else 0,
            comment=feedback.comments,
            timestamp=datetime.utcnow(),
            language="en"  # Optionally extract from request or feedback
        )
        db_service = get_database_service()
        saved = db_service.save_feedback(feedback_model)
        if not saved:
            raise Exception("Failed to save feedback to database")

        return {
            "status": "success",
            "message": "Feedback recorded successfully. Thank you!",
            "simulation_id": simulation_id,
            "feedback_id": feedback_id
        }
    except Exception as e:
        logger.error(f"Error recording feedback: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record feedback"
        )


@router.get(
    "/examples",
    status_code=200,
    summary="Get Simulator Examples",
    description="Get example planned actions for the simulator"
)
def get_simulator_examples():
    """
    Get example planned actions to help users understand the simulator.
    
    Returns:
        List of example actions and their risk levels
    """
    
    examples = [
        {
            "action": "I want to record a phone call with a business partner",
            "category": "Privacy/Recording",
            "risk_level": "Medium",
            "key_concern": "Recording without consent"
        },
        {
            "action": "I want to terminate an employee for poor performance",
            "category": "Employment",
            "risk_level": "High",
            "key_concern": "Wrongful termination claims"
        },
        {
            "action": "I want to post a negative review about a company",
            "category": "Defamation",
            "risk_level": "Medium",
            "key_concern": "Defamation or libel claims"
        },
        {
            "action": "I want to access my competitor's database",
            "category": "Cyber Crime",
            "risk_level": "Critical",
            "key_concern": "Unauthorized computer access"
        },
        {
            "action": "I want to delete evidence before court case",
            "category": "Obstruction of Justice",
            "risk_level": "Critical",
            "key_concern": "Criminal charges"
        },
        {
            "action": "I want to sublet my rented apartment",
            "category": "Property/Rental",
            "risk_level": "Medium",
            "key_concern": "Lease agreement violation"
        }
    ]
    
    return {
        "examples": examples,
        "message": "These are example actions to help you understand the consequence simulator"
    }


@router.get(
    "/health",
    status_code=200,
    summary="Health Check",
    description="Check if simulator service is operational"
)
def simulator_health_check():
    """
    Health check endpoint for the consequence simulator service.
    
    Returns:
        Service status and availability
    """
    
    try:
        simulator = get_consequence_simulator()
        return {
            "status": "healthy",
            "service": "Consequence Simulator",
            "version": "1.0.0",
            "message": "Consequence simulator service is operational"
        }
    
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Consequence simulator service is not available"
        )
