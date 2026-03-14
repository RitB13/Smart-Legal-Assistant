import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from src.routes import chatbot, summarizer
from config import CORS_ORIGINS, DEBUG


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

# Include routers
app.include_router(chatbot.router, tags=["Chatbot"])
app.include_router(summarizer.router, tags=["Document Summarizer"])

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

# Log app shutdown
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Smart Legal Assistant API shutting down...")
