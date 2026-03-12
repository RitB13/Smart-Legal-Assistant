import requests
import logging
from config import GROQ_API_KEY, GROQ_MODEL, LLM_TIMEOUT, LLM_MAX_TOKENS, LLM_TEMPERATURE
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

BASE_URL = "https://api.groq.com/openai/v1/chat/completions"

# System prompt moved to a constant for better maintainability
SYSTEM_PROMPT = """You are a legal assistant specialized in providing accurate and helpful legal information. 
You have expertise in various areas of law including civil, criminal, employment, and property law.
Always structure your responses in this JSON format: 
{
    "summary": "<detailed explanation of the legal issue>",
    "laws": ["<relevant law or statute 1>", "<relevant law or statute 2>"],
    "suggestions": ["<actionable suggestion 1>", "<actionable suggestion 2>"]
}
Ensure all JSON is valid and properly formatted."""


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
def get_legal_response(
    user_query: str,
    temperature: float = None,
    max_tokens: int = None,
    timeout: int = None
) -> str:
    """
    Get legal response from Groq LLM with retry logic.
    
    Args:
        user_query: The user's legal question
        temperature: Sampling temperature (0.0-1.0), defaults to config value
        max_tokens: Maximum tokens in response, defaults to config value
        timeout: Request timeout in seconds, defaults to config value
        
    Returns:
        String response from the LLM
        
    Raises:
        requests.exceptions.RequestException: If API call fails after retries
    """
    temperature = temperature if temperature is not None else LLM_TEMPERATURE
    max_tokens = max_tokens if max_tokens is not None else LLM_MAX_TOKENS
    timeout = timeout if timeout is not None else LLM_TIMEOUT
    
    try:
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_query}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        logger.debug(f"Making request to Groq API with model: {GROQ_MODEL}")
        response = requests.post(
            BASE_URL,
            headers=headers,
            json=payload,
            timeout=timeout
        )
        
        # Raise exception for non-200 status codes
        response.raise_for_status()
        
        # Extract content from response
        content = response.json()["choices"][0]["message"]["content"]
        logger.info(f"Successfully received LLM response ({len(content)} chars)")
        
        return content
        
    except requests.exceptions.Timeout:
        logger.error(f"LLM API request timeout after {timeout}s")
        raise
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error to LLM API: {str(e)}")
        raise
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if hasattr(e, 'response') else 'unknown'
        logger.error(f"LLM API HTTP error (status {status_code}): {str(e)}")
        raise
    except (KeyError, IndexError) as e:
        logger.error(f"Unexpected response format from LLM API: {str(e)}")
        raise
    except requests.exceptions.RequestException as e:
        logger.error(f"LLM API request failed: {str(e)}")
        raise
