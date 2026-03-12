import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def parse_llm_output(raw_output: str) -> Dict[str, Any]:
    """
    Parse LLM output and validate structure.
    
    Args:
        raw_output: Raw string output from LLM
        
    Returns:
        Dictionary with keys: summary, laws, suggestions
    """
    try:
        parsed = json.loads(raw_output)
        
        # Validate required fields
        if not isinstance(parsed.get("summary"), str):
            logger.warning("Missing or invalid 'summary' field in LLM output")
            parsed["summary"] = raw_output
        
        if not isinstance(parsed.get("laws"), list):
            logger.warning("Missing or invalid 'laws' field in LLM output, defaulting to empty list")
            parsed["laws"] = []
        
        if not isinstance(parsed.get("suggestions"), list):
            logger.warning("Missing or invalid 'suggestions' field in LLM output, defaulting to empty list")
            parsed["suggestions"] = []
            
        # Clean up data
        parsed["summary"] = str(parsed["summary"]).strip()
        parsed["laws"] = [
            str(l).strip() for l in parsed["laws"] 
            if isinstance(l, str) and l.strip()
        ]
        parsed["suggestions"] = [
            str(s).strip() for s in parsed["suggestions"] 
            if isinstance(s, str) and s.strip()
        ]
        
        logger.info("LLM output parsed successfully")
        return parsed
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from LLM output: {str(e)}")
        logger.debug(f"Raw output (first 500 chars): {raw_output[:500]}")
        return {
            "summary": raw_output,
            "laws": [],
            "suggestions": []
        }
    except Exception as e:
        logger.error(f"Unexpected error while parsing LLM output: {str(e)}")
        return {
            "summary": "Unable to process the query. Please try again.",
            "laws": [],
            "suggestions": []
        }
