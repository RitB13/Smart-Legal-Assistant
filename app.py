import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
from src.routes import chatbot, summarizer, case_outcome, auth_routes, conversation_routes, prediction_routes, chat_intelligence
from src.middleware.auth_middleware import jwt_auth_middleware
from config import CORS_ORIGINS, DEBUG
from src.services.model_manager import get_model_manager
from src.services.monitoring_service import get_prediction_monitor


# Configure logging
logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Smart Legal Assistant API",
    description="AI-powered legal assistant for providing legal information and guidance",
    version="1.0.0"
)

# Add CORS middleware
logger.info(f"Setting up CORS with allowed origins: {CORS_ORIGINS}")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Add JWT authentication middleware
logger.info("Adding JWT authentication middleware")
app.add_middleware(BaseHTTPMiddleware, dispatch=jwt_auth_middleware)

# Include routers
app.include_router(auth_routes.router, tags=["Authentication"])
app.include_router(conversation_routes.router, tags=["Conversations"])
app.include_router(prediction_routes.router, tags=["Predictions"])
app.include_router(chat_intelligence.router, tags=["Chat Intelligence"])
app.include_router(chatbot.router, tags=["Chatbot"])
app.include_router(summarizer.router, tags=["Document Summarizer"])
app.include_router(case_outcome.router, tags=["Case Outcome Prediction"])

# Health check endpoint
@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint to verify API is running."""
    logger.debug("Health check requested")
    return {
        "status": "ok",
        "service": "Smart Legal Assistant API",
        "version": "1.0.0"
    }

# Root endpoint
@app.get("/", tags=["Info"])
def root():
    """Root endpoint with API information."""
    return {
        "message": "Welcome to Smart Legal Assistant API",
        "docs": "/docs",
        "health": "/health"
    }

# Global exception handler for unhandled exceptions
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle any unhandled exceptions gracefully."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An unexpected error occurred. Please try again later.",
            "request_path": str(request.url)
        }
    )

# Log app startup
@app.on_event("startup")
async def startup_event():
    logger.info("Smart Legal Assistant API starting up...")
    logger.info(f"Debug mode: {DEBUG}")
    
    # PHASE 9: Load models at startup
    logger.info("\n" + "=" * 70)
    logger.info("PHASE 9 - DEPLOYMENT & MONITORING: Initializing at startup")
    logger.info("=" * 70)
    
    # Load and cache models in memory
    model_manager = get_model_manager()
    if model_manager.load_model_at_startup():
        logger.info("✓ Models loaded successfully and cached in memory")
        model_info = model_manager.get_model_info()
        logger.info(f"  Available versions: {len(model_info['available_versions'])}")
        logger.info(f"  Current version: {model_info['current_version']}")
        logger.info(f"  Fallback available: {model_info['fallback_version'] is not None}")
    else:
        logger.warning("⚠ Failed to load models, predictions may be unavailable")
    
    # Initialize monitoring
    monitor = get_prediction_monitor()
    logger.info("✓ Prediction monitoring initialized")
    
    logger.info("=" * 70)
    logger.info("Startup complete - API ready for requests")
    logger.info("=" * 70 + "\n")

# Log app shutdown
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Smart Legal Assistant API shutting down...")
