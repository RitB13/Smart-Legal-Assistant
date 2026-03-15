"""
Configuration module for Smart Legal Assistant API.
Loads environment variables from .env file.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


# ==================== API CONFIGURATION ====================

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY environment variable is not set. Please add it to your .env file.")

GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile")


# ==================== SERVER CONFIGURATION ====================

API_PORT = int(os.getenv("API_PORT", 8000))
DEBUG = os.getenv("DEBUG", "False").lower() == "true"


# ==================== LLM CONFIGURATION ====================

LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", 30))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", 1000))
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", 0.3))


# ==================== CORS CONFIGURATION ====================

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")
CORS_ORIGINS = [origin.strip() for origin in CORS_ORIGINS]


# ==================== MULTILINGUAL CONFIGURATION ====================

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


# ==================== MONGODB CONFIGURATION ====================

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://127.0.0.1:27017/")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "smart_legal_db")


# ==================== SECURITY CONFIGURATION ====================

# Secret key for JWT tokens (should be in .env for production)
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 1440))  # 24 hours


# ==================== FEATURE FLAGS ====================

ENABLE_AUDIT_LOGGING = os.getenv("ENABLE_AUDIT_LOGGING", "True").lower() == "true"
ENABLE_FEEDBACK = os.getenv("ENABLE_FEEDBACK", "True").lower() == "true"
ENABLE_PREDICTIONS = os.getenv("ENABLE_PREDICTIONS", "True").lower() == "true"


__all__ = [
    "GROQ_API_KEY",
    "GROQ_MODEL",
    "API_PORT",
    "DEBUG",
    "LLM_TIMEOUT",
    "LLM_MAX_TOKENS",
    "LLM_TEMPERATURE",
    "CORS_ORIGINS",
    "ENABLE_MULTILINGUAL",
    "DEFAULT_LANGUAGE",
    "SUPPORTED_LANGUAGES",
    "MONGODB_URL",
    "MONGODB_DB_NAME",
    "SECRET_KEY",
    "ALGORITHM",
    "ACCESS_TOKEN_EXPIRE_MINUTES",
    "ENABLE_AUDIT_LOGGING",
    "ENABLE_FEEDBACK",
    "ENABLE_PREDICTIONS",
]

