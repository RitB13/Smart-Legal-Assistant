import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def parse_llm_output(raw_output: str) -> Dict[str, Any]:
    """
    Parse LLM output and validate structure with UTF-8 support for multilingual text.
    
    This parser is designed to handle responses in multiple languages while maintaining
    the expected JSON structure (summary, laws, suggestions).
    
    Args:
        raw_output: Raw string output from LLM (supports UTF-8 encoded multilingual text)
        
    Returns:
        Dictionary with keys: summary, laws, suggestions (all UTF-8 safe)
    """
    if not raw_output or not isinstance(raw_output, str):
        logger.warning("Empty or invalid raw output provided to parser")
        return {
            "summary": "Unable to process the response. Please try again.",
            "laws": [],
            "suggestions": []
        }
    
    try:
        # Python 3's json module handles UTF-8 by default
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
            
        # Clean up data while preserving UTF-8 characters
        # strip() works safely with UTF-8 strings in Python 3
        parsed["summary"] = str(parsed["summary"]).strip()
        
        # Process laws list, filtering out empty items
        parsed["laws"] = [
            str(l).strip() for l in parsed["laws"] 
            if isinstance(l, str) and l.strip()
        ]
        
        # Process suggestions list, filtering out empty items
        parsed["suggestions"] = [
            str(s).strip() for s in parsed["suggestions"] 
            if isinstance(s, str) and s.strip()
        ]
        
        logger.info("LLM output parsed successfully")
        return parsed
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from LLM output: {str(e)}")
        logger.debug(f"Raw output (first 500 chars): {raw_output[:500]}")
        # Return the raw output as summary if JSON parsing fails
        # This preserves the original response even if it's not properly formatted
        return {
            "summary": raw_output,
            "laws": [],
            "suggestions": []
        }
    except UnicodeDecodeError as e:
        # Handle cases where UTF-8 decoding fails (rare in Python 3)
        logger.error(f"Unicode decoding error while parsing LLM output: {str(e)}")
        return {
            "summary": "Unable to process the response due to encoding error. Please try again.",
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
