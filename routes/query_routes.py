from fastapi import APIRouter, HTTPException, status
from models.query_model import QueryRequest, QueryResponse
from services.llm_service import get_legal_response
from services.parser import parse_llm_output
import logging
import uuid
import time
import requests

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/query", response_model=QueryResponse, status_code=200)
def handle_query(req: QueryRequest) -> QueryResponse:
    """
    Process a legal query and return structured legal information.
    
    Args:
        req: QueryRequest containing the user's legal question
        
    Returns:
        QueryResponse with summary, relevant laws, and suggestions
        
    Raises:
        HTTPException: For various error conditions during processing
    """
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    try:
        logger.info(f"[{request_id}] New legal query received: {req.query[:80]}...")
        
        # Get response from LLM
        logger.debug(f"[{request_id}] Calling LLM service...")
        raw_output = get_legal_response(req.query)
        
        # Parse the LLM output
        logger.debug(f"[{request_id}] Parsing LLM response...")
        parsed = parse_llm_output(raw_output)
        
        # Add metadata to response
        parsed["request_id"] = request_id
        
        # Log successful completion
        elapsed = time.time() - start_time
        logger.info(f"[{request_id}] Query processed successfully in {elapsed:.2f}s")
        
        # Create and return response
        response = QueryResponse(**parsed)
        return response
        
    except requests.exceptions.Timeout:
        elapsed = time.time() - start_time
        logger.error(
            f"[{request_id}] LLM API timeout after {elapsed:.2f}s",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Legal assistant service is taking too long to respond. Please try again."
        )
        
    except requests.exceptions.ConnectionError:
        elapsed = time.time() - start_time
        logger.error(
            f"[{request_id}] Failed to connect to LLM API after {elapsed:.2f}s",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to connect to legal assistant service. Please try again later."
        )
        
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if hasattr(e, 'response') else 500
        elapsed = time.time() - start_time
        logger.error(
            f"[{request_id}] LLM API HTTP error ({status_code}) after {elapsed:.2f}s",
            exc_info=True
        )
        
        if status_code == 401:
            # Misconfiguration on server side - don't expose to client
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error. Please contact support."
            )
        elif status_code == 429:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please wait a moment before trying again."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Legal assistant service is temporarily unavailable. Please try again."
            )
        
    except requests.exceptions.RequestException as e:
        elapsed = time.time() - start_time
        logger.error(
            f"[{request_id}] LLM API request failed after {elapsed:.2f}s: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to process your legal query. Please try again."
        )
        
    except ValueError as e:
        elapsed = time.time() - start_time
        logger.error(
            f"[{request_id}] Invalid response format after {elapsed:.2f}s: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Received invalid response from legal assistant service."
        )
        
    except Exception as e:
        elapsed = time.time() - start_time
        logger.exception(
            f"[{request_id}] Unexpected error after {elapsed:.2f}s: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing your query. Please try again."
        )
