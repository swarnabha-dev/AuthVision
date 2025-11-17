"""Model Server FastAPI Application."""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import config
from app.server import router
from app.auth_routes import router as auth_router

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Model Server...")
    logger.info(f"Config: model={config.model_name}, detector={config.detector_backend}, workers={config.workers}")
    logger.info(f"Recognition threshold: {config.recognition_threshold}")
    logger.info(f"Embedding dimension: {config.embedding_dim}")
    
    # Initialize components (detector, recognizer, tracker are lazy-loaded on first request)
    logger.info("Model Server ready - CPU optimized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Model Server...")


def create_app() -> FastAPI:
    """Create FastAPI application."""
    app = FastAPI(
        title="Face Recognition Model Server",
        description="ArcFace Recognition and YOLO Detection Service",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json"
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure based on environment
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(auth_router)  # Auth endpoints first
    app.include_router(router)  # Model endpoints
    
    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=config.host,
        port=config.port,
        reload=True
    )
