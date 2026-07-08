import os
import logging
from dotenv import load_dotenv

load_dotenv()

_config_logger = logging.getLogger(__name__)

# API Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
if not GROQ_API_KEY:
    # Log a warning at import time — do NOT raise here.
    # Import-time exceptions prevent tests, scripts, and partial imports from working.
    # The server startup hook calls validate_config() which raises if the key is missing.
    _config_logger.warning(
        "GROQ_API_KEY is not set. LLM features will fail. "
        "Add GROQ_API_KEY to your .env file before starting the server."
    )


def validate_config() -> None:
    """
    Validate all required environment variables.
    Call this once at application startup — NOT at import time.
    Raises RuntimeError with a clear message for any missing required value.
    """
    missing = []
    if not os.getenv("GROQ_API_KEY"):
        missing.append("GROQ_API_KEY")
    if not os.getenv("JWT_SECRET_KEY"):
        missing.append("JWT_SECRET_KEY")
    if missing:
        raise RuntimeError(
            f"Required environment variables are not set: {', '.join(missing)}. "
            "Add them to your .env file and restart the server."
        )
    _config_logger.info("[CONFIG] All required environment variables are set")

GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# Server Configuration
API_PORT = int(os.getenv("API_PORT", 8000))
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# LLM Configuration
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", 30))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", 1000))
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", 0.3))

# CORS Configuration
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")
CORS_ORIGINS = [origin.strip() for origin in CORS_ORIGINS]

# Multilingual Configuration
ENABLE_MULTILINGUAL = os.getenv("ENABLE_MULTILINGUAL", "True").lower() == "true"
DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "en")

# Supported languages (ISO 639-1 codes)
SUPPORTED_LANGUAGES = [
    "en",  # English
    "hi",  # Hindi
    "bn",  # Bengali
    "ta",  # Tamil
    "te",  # Telugu
    "mr",  # Marathi
    "gu",  # Gujarati
    "kn",  # Kannada
    "ml",  # Malayalam
    "pa",  # Punjabi
]
