"""
Main FastAPI application entry point.
Initializes the application with all routes and dependencies.
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from presentation.routers.transcription import router as transcription_router
from presentation.middleware import RequestLoggingMiddleware, CORSMiddleware
from infrastructure.external import EnvironmentSettingsAdapter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting TranscriberApp...")

    # Startup tasks
    logger.info("Application startup complete")

    yield

    # Shutdown tasks
    logger.info("Shutting down TranscriberApp...")


def create_application() -> FastAPI:
    """Create and configure FastAPI application."""

    # Get settings
    settings = EnvironmentSettingsAdapter().get_settings()

    # Create FastAPI app
    app = FastAPI(
        title="TranscriberApp",
        description="AI-powered audio transcription and summarization service",
        version="2.0.0",
        lifespan=lifespan
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add custom middleware
    app.add_middleware(RequestLoggingMiddleware)

    # Include routers
    app.include_router(transcription_router)

    # Health check endpoint
    @app.get("/health", tags=["health"])
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "version": "2.0.0",
            "services": {
                "groq": bool(settings.groq_api_key),
                "gemini": bool(settings.gemini_api_key),
                "ffmpeg": bool(settings.ffmpeg_api_url)
            }
        }

    # Root endpoint
    @app.get("/", tags=["root"])
    async def root():
        """Root endpoint."""
        return {
            "message": "TranscriberApp API v2.0.0",
            "docs": "/docs",
            "health": "/health"
        }

    return app


# Create application instance
app = create_application()


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )