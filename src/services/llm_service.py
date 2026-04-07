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


def create_jurisdiction_aware_prompt(
    language_code: str,
    country: str = "India",
    state: str = "National",
    relevant_laws: list = None
) -> str:
    """
    Create a jurisdiction-aware system prompt that includes relevant laws.
    
    Args:
        language_code: ISO language code (e.g., 'en', 'hi')
        country: Country jurisdiction (e.g., 'India', 'USA')
        state: State/region jurisdiction (e.g., 'Maharashtra')
        relevant_laws: List of relevant law objects with 'name' and 'statute_text' keys
        
    Returns:
        System prompt string with jurisdiction-specific context
    """
    language_names = {
        'en': 'English',
        'hi': 'Hindi (हिन्दी)',
        'bn': 'Bengali (বাংলा)',
        'ta': 'Tamil (தమిଲ)',
        'te': 'Telugu (తెలుగు)',
        'mr': 'Marathi (मराठी)',
        'gu': 'Gujarati (ગુજરાતી)',
        'kn': 'Kannada (ಕನ್ನಡ)',
        'ml': 'Malayalam (മലയാളം)',
        'pa': 'Punjabi (ਪੰਜਾਬੀ)'
    }
    
    language_name = language_names.get(language_code, language_code)
    jurisdiction_str = f"{country}/{state}" if state != "National" else country
    
    # Build laws context
    laws_context = ""
    if relevant_laws:
        laws_context = "\n\nMOST RELEVANT APPLICABLE LAWS:\n"
        for law in relevant_laws[:3]:  # Top 3 laws
            law_name = law.get("name", "Unknown Law")
            law_id = law.get("law_id", "")
            laws_context += f"\n- {law_id}: {law_name}\n"
            if "statute_text" in law:
                laws_context += f"  Text: {law.get('statute_text', '')[:200]}...\n"
    
    prompt = f"""You are a legal assistant specialized in providing accurate and helpful legal information.
You have expertise in various areas of law including civil, criminal, employment, property, constitutional, and contract law.

JURISDICTION: You are providing legal guidance for {jurisdiction_str}. 
All advice, laws, and procedures mentioned MUST be specific to {jurisdiction_str} jurisdiction.
{laws_context}

CRITICAL INSTRUCTIONS:
1. You must respond ONLY in the SAME LANGUAGE as the user's query ({language_name})
2. Focus exclusively on laws applicable in {jurisdiction_str}
3. Always mention the specific acts, sections, and statutes relevant to this jurisdiction
4. If a law from this jurisdiction applies, cite it with the full section/act name and number
5. Do not provide generic advice - tailor everything to {jurisdiction_str} legal system

Always structure your responses in valid JSON format:
{{
    "summary": "<detailed explanation of the legal issue in {jurisdiction_str} context>",
    "laws": ["<specific statute/section applicable in {jurisdiction_str}>", "..."],
    "suggestions": ["<actionable suggestion based on {jurisdiction_str} law>", "..."],
    "jurisdiction_note": "<specific note about applicability in {jurisdiction_str}>"
}}

Guidelines:
- The "summary" field MUST be in {language_name}
- The "suggestions" field MUST be in {language_name}
- Law names and sections MUST be those applicable in {jurisdiction_str}
- Ensure all JSON is valid and properly formatted
- Provide clear, concise, and accurate legal guidance specific to {jurisdiction_str}
- Do not include any text outside the JSON structure"""
    
    return prompt


def get_legal_response(
    user_query: str,
    language: str = "en",
    temperature: float = None,
    max_tokens: int = None,
    timeout: int = None
) -> str:
    """
    Get legal response from Groq LLM with multilingual support.
    
    Args:
        user_query: The user's legal question
        language: ISO language code (e.g., 'en', 'hi', 'bn'). Defaults to 'en'
        temperature: Sampling temperature (0.0-1.0), defaults to config value
        max_tokens: Maximum tokens in response, defaults to config value
        timeout: Request timeout in seconds, defaults to config value
        
    Returns:
        String response from the LLM
        
    Raises:
        requests.exceptions.RequestException: If API call fails
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

        logger.debug(f"Making request to Groq API with model: {GROQ_MODEL}, language: {language}, timeout={timeout}s")
        logger.debug(f"System prompt length: {len(system_prompt)} chars")
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
        
    except requests.exceptions.Timeout as e:
        logger.error(f"LLM API request timeout after {timeout}s")
        raise Exception(f"AI service timeout - request exceeded {timeout} seconds. Please try again.")
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error to LLM API: {str(e)}")
        raise Exception(f"Unable to connect to AI service. Please check your internet connection.")
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if hasattr(e, 'response') else 'unknown'
        error_body = "No response body"
        try:
            if hasattr(e, 'response') and e.response is not None:
                error_body = e.response.text[:500]
        except:
            pass
        logger.error(f"LLM API HTTP error (status {status_code}): {str(e)}")
        logger.error(f"Groq API response body: {error_body}")
        
        if status_code == 429:
            raise Exception("AI service is rate limited. Please try again in a moment.")
        elif status_code == 401 or status_code == 403:
            raise Exception("AI service authentication failed. Please contact support.")
        else:
            raise Exception(f"AI service error ({status_code}): Unable to process your request.")
    except (KeyError, IndexError) as e:
        logger.error(f"Unexpected response format from LLM API: {str(e)}")
        raise Exception("AI service returned an unexpected response format.")
    except requests.exceptions.RequestException as e:
        logger.error(f"LLM API request failed: {str(e)}")
        raise Exception(f"AI service request failed: {str(e)}")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
def get_legal_response_with_jurisdiction(
    user_query: str,
    language: str = "en",
    country: str = "India",
    state: str = "National",
    relevant_laws: list = None,
    temperature: float = None,
    max_tokens: int = None,
    timeout: int = None
) -> str:
    """
    Get legal response from Groq LLM with jurisdiction-aware context.
    
    Args:
        user_query: The user's legal question
        language: ISO language code (e.g., 'en', 'hi', 'bn'). Defaults to 'en'
        country: Country jurisdiction (e.g., 'India', 'USA'). Defaults to 'India'
        state: State/region jurisdiction. Defaults to 'National'
        relevant_laws: List of relevant law objects from law_matcher
        temperature: Sampling temperature (0.0-1.0), defaults to config value
        max_tokens: Maximum tokens in response, defaults to config value
        timeout: Request timeout in seconds, defaults to config value
        
    Returns:
        String response from the LLM with jurisdiction-specific context
        
    Raises:
        requests.exceptions.RequestException: If API call fails after retries
    """
    temperature = temperature if temperature is not None else LLM_TEMPERATURE
    max_tokens = max_tokens if max_tokens is not None else LLM_MAX_TOKENS
    timeout = timeout if timeout is not None else LLM_TIMEOUT
    
    # Create jurisdiction-aware system prompt
    system_prompt = create_jurisdiction_aware_prompt(
        language,
        country=country,
        state=state,
        relevant_laws=relevant_laws
    )
    
    try:
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        jurisdiction_str = f"{country}/{state}" if state != "National" else country
        
        payload = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_query}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        logger.debug(f"Making jurisdiction-aware request to Groq API")
        logger.debug(f"Jurisdiction: {jurisdiction_str}, Language: {language}")
        logger.debug(f"Number of relevant laws provided: {len(relevant_laws) if relevant_laws else 0}")
        
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
        logger.info(f"Successfully received jurisdiction-aware LLM response ({len(content)} chars) for {jurisdiction_str}")
        
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
                error_body = e.response.text[:500]
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
