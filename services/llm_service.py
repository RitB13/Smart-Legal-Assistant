import requests
import logging
from config import GROQ_API_KEY, GROQ_MODEL, LLM_TIMEOUT, LLM_MAX_TOKENS, LLM_TEMPERATURE
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

BASE_URL = "https://api.groq.com/openai/v1/chat/completions"

# Base system prompt (language-agnostic guidance)
BASE_SYSTEM_PROMPT = """You are a legal assistant specialized in providing accurate and helpful legal information on Indian law and international legal principles.
You have expertise in various areas of law including civil, criminal, employment, property, constitutional, and contract law.

CRITICAL INSTRUCTION: You must respond ONLY in the SAME LANGUAGE as the user's query. If the user writes in Hindi, respond entirely in Hindi. If in English, respond in English. And so on for other languages.

Always structure your responses in this JSON format:
{
    "summary": "<detailed explanation of the legal issue>",
    "laws": ["<relevant law or statute 1>", "<relevant law or statute 2>"],
    "suggestions": ["<actionable suggestion 1>", "<actionable suggestion 2>"]
}

Guidelines:
- The "summary" field MUST be in the same language as the user's query
- The "suggestions" field MUST be in the same language as the user's query
- Law names or legal sections can remain in English if they are proper names (e.g., "Indian Penal Code")
- Ensure all JSON is valid and properly formatted
- Provide clear, concise, and accurate legal guidance
- Do not include any text outside the JSON structure"""


def create_language_aware_prompt(language_code: str) -> str:
    """
    Create a language-aware system prompt for multilingual support.
    
    Args:
        language_code: ISO language code (e.g., 'en', 'hi', 'bn')
        
    Returns:
        System prompt string with language-specific instructions
    """
    language_names = {
        'en': 'English',
        'hi': 'Hindi (हिन्दी)',
        'bn': 'Bengali (বাংলা)',
        'ta': 'Tamil (தமிழ்)',
        'te': 'Telugu (తెలుగు)',
        'mr': 'Marathi (मराठी)',
        'gu': 'Gujarati (ગુજરાતી)',
        'kn': 'Kannada (ಕನ್ನಡ)',
        'ml': 'Malayalam (മലയാളം)',
        'pa': 'Punjabi (ਪੰਜਾਬੀ)'
    }
    
    language_name = language_names.get(language_code, language_code)
    
    prompt = BASE_SYSTEM_PROMPT + f"\n\nIMPORTANT: The user is communicating in {language_name}. Your response MUST be entirely in {language_name}."
    
    return prompt


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
def get_legal_response(
    user_query: str,
    language: str = "en",
    temperature: float = None,
    max_tokens: int = None,
    timeout: int = None
) -> str:
    """
    Get legal response from Groq LLM with retry logic and multilingual support.
    
    Args:
        user_query: The user's legal question
        language: ISO language code (e.g., 'en', 'hi', 'bn'). Defaults to 'en'
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
    
    # Create language-aware system prompt
    system_prompt = create_language_aware_prompt(language)
    
    try:
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_query}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        logger.debug(f"Making request to Groq API with model: {GROQ_MODEL}, language: {language}")
        logger.debug(f"System prompt length: {len(system_prompt)} chars, first 150 chars: {system_prompt[:150]}...")
        logger.debug(f"Payload: model={GROQ_MODEL}, temperature={temperature}, max_tokens={max_tokens}")
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
        logger.info(f"Successfully received LLM response ({len(content)} chars) in language {language}")
        
        return content
        
    except requests.exceptions.Timeout:
        logger.error(f"LLM API request timeout after {timeout}s")
        raise
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error to LLM API: {str(e)}")
        raise
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if hasattr(e, 'response') else 'unknown'
        error_body = "No response body"
        try:
            if hasattr(e, 'response') and e.response is not None:
                error_body = e.response.text[:500]  # First 500 chars of error
        except:
            pass
        logger.error(f"LLM API HTTP error (status {status_code}): {str(e)}")
        logger.error(f"Groq API response body: {error_body}")
        raise
    except (KeyError, IndexError) as e:
        logger.error(f"Unexpected response format from LLM API: {str(e)}")
        raise
    except requests.exceptions.RequestException as e:
        logger.error(f"LLM API request failed: {str(e)}")
        raise
