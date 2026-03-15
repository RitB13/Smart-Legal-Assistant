import os
from dotenv import load_dotenv

load_dotenv()


# API Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY environment variable is not set. Please add it to your .env file.")

GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile")

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
