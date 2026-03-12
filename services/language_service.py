import logging
from langdetect import detect, LangDetectException

logger = logging.getLogger(__name__)

# Supported languages with their ISO codes
SUPPORTED_LANGUAGES = {
    'en': 'English',
    'hi': 'Hindi',
    'bn': 'Bengali',
    'ta': 'Tamil',
    'te': 'Telugu',
    'mr': 'Marathi',
    'gu': 'Gujarati',
    'kn': 'Kannada',
    'ml': 'Malayalam',
    'pa': 'Punjabi'
}

DEFAULT_LANGUAGE = 'en'


def detect_language(text: str) -> str:
    """
    Detect the language of the input text automatically.
    
    Uses langdetect library to identify the language of the text.
    Returns a standard ISO language code (e.g., 'en', 'hi', 'bn', etc.).
    
    Args:
        text: The input text to detect language from
        
    Returns:
        ISO language code (str). Examples: 'en', 'hi', 'bn', 'ta', 'te', 'mr', 'gu', 'kn', 'ml', 'pa'
        Defaults to 'en' if detection fails or language is not explicitly supported
        
    Raises:
        No exceptions - always returns a language code
    """
    if not text or not isinstance(text, str):
        logger.warning("Empty or invalid text provided for language detection, defaulting to English")
        return DEFAULT_LANGUAGE
    
    try:
        # Detect language using langdetect
        detected_lang = detect(text.strip())
        
        # Normalize the language code (langdetect may return codes like 'pt-br')
        lang_code = detected_lang.split('-')[0].lower()
        
        # Check if detected language is in supported list
        if lang_code in SUPPORTED_LANGUAGES:
            logger.info(f"Language detected: {lang_code} ({SUPPORTED_LANGUAGES[lang_code]})")
            return lang_code
        else:
            # Language detected but not explicitly supported
            # Still return the code and let LLM handle it
            logger.info(f"Language detected: {lang_code} (not in primary support list, but will attempt)")
            return lang_code
            
    except LangDetectException as e:
        logger.warning(f"Language detection failed: {str(e)}. Defaulting to English.")
        return DEFAULT_LANGUAGE
    except Exception as e:
        logger.error(f"Unexpected error during language detection: {str(e)}. Defaulting to English.")
        return DEFAULT_LANGUAGE


def get_language_name(lang_code: str) -> str:
    """
    Get the human-readable name of a language from its ISO code.
    
    Args:
        lang_code: ISO language code (e.g., 'en', 'hi', 'bn')
        
    Returns:
        Language name (str). Returns the code itself if language is not found.
    """
    return SUPPORTED_LANGUAGES.get(lang_code, lang_code)


def is_supported_language(lang_code: str) -> bool:
    """
    Check if a language code is in the explicitly supported list.
    
    Args:
        lang_code: ISO language code
        
    Returns:
        True if language is supported, False otherwise
    """
    return lang_code in SUPPORTED_LANGUAGES
