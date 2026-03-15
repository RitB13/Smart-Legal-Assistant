"""
Phase 4: Database Routes
API endpoints for storing and retrieving legal assistant data from MongoDB
"""

from fastapi import APIRouter, HTTPException, status, Request
from typing import List, Optional
import uuid
import logging
from datetime import datetime

from src.services.database_service import get_database_service
from src.models.database_models import (
    UserSessionModel, QueryRecordModel, SimulationRecordModel,
    ModeDecisionModel, UserFeedbackModel, UserAnalyticsModel
)

logger = logging.getLogger(__name__)
router = APIRouter()
db = get_database_service()


@router.post("/session/create")
def create_session(language: str = "en", user_id: Optional[str] = None):
    """
    Create a new user session for tracking conversation context
    
    Args:
        language: User's language preference
        user_id: Optional user identifier
        
    Returns:
        Session information with session_id
    """
    try:
        session_id = str(uuid.uuid4())
        session = UserSessionModel(
            session_id=session_id,
            user_id=user_id,
            language=language,
            start_time=datetime.utcnow(),
            last_activity=datetime.utcnow()
        )
        
        if db.save_session(session):
            logger.info(f"Session created: {session_id}")
            return {
                "session_id": session_id,
                "created_at": session.start_time.isoformat(),
                "language": language
            }
        else:
            logger.warning("Failed to save session to database")
            return {
                "session_id": session_id,
                "created_at": session.start_time.isoformat(),
                "language": language,
                "db_status": "offline"
            }
    
    except Exception as e:
        logger.error(f"Error creating session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create session"
        )


@router.get("/session/{session_id}")
def get_session(session_id: str):
    """
    Retrieve session information
    
    Args:
        session_id: The session ID
        
    Returns:
        Session details
    """
    try:
        session = db.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        return session.dict()
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve session"
        )


@router.post("/query/save")
def save_query(query_record: QueryRecordModel):
    """
    Save a query and its response
    
    Args:
        query_record: QueryRecordModel with query and response data
        
    Returns:
        Confirmation with query_id
    """
    try:
        # Generate ID if not provided
        if not query_record.query_id:
            query_record.query_id = str(uuid.uuid4())
        
        success = db.save_query_record(query_record)
        
        if success:
            logger.info(f"Query saved: {query_record.query_id}")
            return {
                "query_id": query_record.query_id,
                "saved": True,
                "timestamp": query_record.timestamp.isoformat()
            }
        else:
            logger.warning("Failed to save query to database")
            return {
                "query_id": query_record.query_id,
                "saved": False,
                "db_status": "offline"
            }
    
    except Exception as e:
        logger.error(f"Error saving query: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save query"
        )


@router.get("/query/{query_id}")
def get_query(query_id: str):
    """
    Retrieve a query record
    
    Args:
        query_id: The query ID
        
    Returns:
        Query and response details
    """
    try:
        record = db.get_query_record(query_id)
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Query not found"
            )
        
        return record.dict()
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving query: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve query"
        )


@router.get("/session/{session_id}/queries")
def get_session_queries(session_id: str, limit: int = 50):
    """
    Get all queries in a session
    
    Args:
        session_id: The session ID
        limit: Maximum number of queries to return
        
    Returns:
        List of query records
    """
    try:
        records = db.get_session_queries(session_id)
        
        # Apply limit
        if limit > 0:
            records = records[:limit]
        
        return {
            "session_id": session_id,
            "total_queries": len(records),
            "queries": [record.dict() for record in records]
        }
    
    except Exception as e:
        logger.error(f"Error retrieving session queries: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve session queries"
        )


@router.post("/query/{query_id}/feedback")
def save_query_feedback(query_id: str, rating: int, comment: Optional[str] = None):
    """
    Save user feedback on a query response
    
    Args:
        query_id: The query ID
        rating: User rating 1-5
        comment: Optional user comment
        
    Returns:
        Confirmation of feedback saved
    """
    try:
        if not 1 <= rating <= 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rating must be between 1 and 5"
            )
        
        success = db.save_query_feedback(query_id, rating, comment)
        
        if success:
            logger.info(f"Feedback saved for query: {query_id}")
            return {"query_id": query_id, "feedback_saved": True}
        else:
            return {"query_id": query_id, "feedback_saved": False, "db_status": "offline"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving query feedback: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save feedback"
        )


@router.post("/simulation/save")
def save_simulation(simulation_record: SimulationRecordModel):
    """
    Save a consequence simulation record
    
    Args:
        simulation_record: SimulationRecordModel with simulation data
        
    Returns:
        Confirmation with simulation_id
    """
    try:
        # Generate ID if not provided
        if not simulation_record.simulation_id:
            simulation_record.simulation_id = str(uuid.uuid4())
        
        success = db.save_simulation_record(simulation_record)
        
        if success:
            logger.info(f"Simulation saved: {simulation_record.simulation_id}")
            return {
                "simulation_id": simulation_record.simulation_id,
                "saved": True,
                "timestamp": simulation_record.timestamp.isoformat()
            }
        else:
            return {
                "simulation_id": simulation_record.simulation_id,
                "saved": False,
                "db_status": "offline"
            }
    
    except Exception as e:
        logger.error(f"Error saving simulation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save simulation"
        )


@router.get("/simulation/{simulation_id}")
def get_simulation(simulation_id: str):
    """
    Retrieve a simulation record
    
    Args:
        simulation_id: The simulation ID
        
    Returns:
        Simulation details
    """
    try:
        record = db.get_simulation_record(simulation_id)
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Simulation not found"
            )
        
        return record.dict()
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving simulation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve simulation"
        )


@router.get("/session/{session_id}/simulations")
def get_session_simulations(session_id: str, limit: int = 50):
    """
    Get all simulations in a session
    
    Args:
        session_id: The session ID
        limit: Maximum number of simulations to return
        
    Returns:
        List of simulation records
    """
    try:
        records = db.get_session_simulations(session_id)
        
        if limit > 0:
            records = records[:limit]
        
        return {
            "session_id": session_id,
            "total_simulations": len(records),
            "simulations": [record.dict() for record in records]
        }
    
    except Exception as e:
        logger.error(f"Error retrieving session simulations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve session simulations"
        )


@router.post("/simulation/{simulation_id}/feedback")
def save_simulation_feedback(
    simulation_id: str,
    rating: int,
    comment: Optional[str] = None,
    helpful: Optional[bool] = None
):
    """
    Save user feedback on a simulation
    
    Args:
        simulation_id: The simulation ID
        rating: User rating 1-5
        comment: Optional user comment
        helpful: Whether user found it helpful
        
    Returns:
        Confirmation of feedback saved
    """
    try:
        if not 1 <= rating <= 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rating must be between 1 and 5"
            )
        
        success = db.save_simulation_feedback(simulation_id, rating, comment, helpful)
        
        if success:
            logger.info(f"Feedback saved for simulation: {simulation_id}")
            return {"simulation_id": simulation_id, "feedback_saved": True}
        else:
            return {"simulation_id": simulation_id, "feedback_saved": False, "db_status": "offline"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving simulation feedback: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save feedback"
        )


@router.post("/mode-decision/save")
def save_mode_decision(decision: ModeDecisionModel):
    """
    Save a mode detection decision
    
    Args:
        decision: ModeDecisionModel with decision data
        
    Returns:
        Confirmation
    """
    try:
        if not decision.decision_id:
            decision.decision_id = str(uuid.uuid4())
        
        success = db.save_mode_decision(decision)
        
        if success:
            logger.info(f"Mode decision saved: {decision.decision_id}")
            return {"decision_id": decision.decision_id, "saved": True}
        else:
            return {"decision_id": decision.decision_id, "saved": False, "db_status": "offline"}
    
    except Exception as e:
        logger.error(f"Error saving mode decision: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save mode decision"
        )


@router.get("/analytics/{session_id}")
def get_analytics(session_id: str):
    """
    Get session analytics/summary
    
    Args:
        session_id: The session ID
        
    Returns:
        Analytics summary for the session
    """
    try:
        analytics = db.get_analytics(session_id)
        if not analytics:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analytics not found"
            )
        
        return analytics.dict()
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving analytics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve analytics"
        )


@router.get("/stats")
def get_system_stats():
    """
    Get overall system statistics
    
    Returns:
        System-wide statistics
    """
    try:
        stats = db.get_system_stats()
        return {
            "status": "success" if stats else "database_offline",
            "statistics": stats
        }
    
    except Exception as e:
        logger.error(f"Error retrieving system stats: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }


@router.get("/health")
def database_health():
    """
    Health check for database connection
    
    Returns:
        Database health status
    """
    try:
        is_healthy = db.health_check()
        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "connected": is_healthy,
            "database": "mongodb"
        }
    
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "error",
            "connected": False,
            "message": str(e)
        }
