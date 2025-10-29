"""
FastAPI main application with strict typing and dependency injection.

Module 1: FastAPI skeleton with typed routes (no business logic).
"""

from fastapi import FastAPI

from app.api.v1 import (
    routes_attendance,
    routes_device,
    routes_health,
    routes_models,
    routes_stream,
)

# Create FastAPI app instance
app = FastAPI(
    title="Smart Attendance System",
    description="Production-grade smart attendance with MLflow orchestration",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Include routers under /api/v1
app.include_router(routes_health.router, prefix="/api/v1")
app.include_router(routes_device.router, prefix="/api/v1")
app.include_router(routes_models.router, prefix="/api/v1")
app.include_router(routes_stream.router, prefix="/api/v1")
app.include_router(routes_attendance.router, prefix="/api/v1")


@app.get("/")
def root() -> dict[str, str]:
    """Root endpoint.

    Returns:
        Welcome message
    """
    return {"message": "Smart Attendance API - visit /docs for interactive documentation"}
