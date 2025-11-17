"""
Health check and utility routes.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models import Student
from app.schemas import HealthResponse
from app.services.model_server_service import model_server_service
from app.services.stream_processor import stream_manager
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Check backend health status.
    
    Returns:
    - Database connection status
    - Model server connection status
    - Number of active streams
    - Total students count
    """
    # Check database
    try:
        result = await db.execute(select(func.count(Student.student_id)))
        total_students = result.scalar_one()
        db_status = "healthy"
    except Exception as e:
        logger.error(f"❌ Database health check failed: {e}")
        db_status = "unhealthy"
        total_students = 0
    
    # Check model server
    try:
        model_health = await model_server_service.health_check()
        model_status = model_health.get("status", "unknown")
    except Exception as e:
        logger.error(f"❌ Model server health check failed: {e}")
        model_status = "unreachable"
    
    # Get active streams count
    active_streams = len(stream_manager.get_active_streams())
    
    return HealthResponse(
        status="healthy" if db_status == "healthy" and model_status == "healthy" else "degraded",
        database=db_status,
        model_server=model_status,
        active_streams=active_streams,
        total_students=total_students
    )


@router.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Face Recognition Backend",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }
