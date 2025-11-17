"""
Main FastAPI application for Face Recognition Backend.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import logging
from pathlib import Path

from app.config import settings
from app.database import init_db
from app.routes import auth_routes, student_routes, websocket_routes, health_routes
from app.services.model_server_service import model_server_service
from app.services.stream_processor import stream_manager
from app.routes.websocket_routes import broadcast_recognition_event
from app.models import AttendanceEvent, Student
from app.database import AsyncSessionLocal
from datetime import datetime
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Reduce noise from third-party libraries
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("aiosqlite").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.engine").setLevel(logging.ERROR)  # Hide all SQL queries including "cached"
logging.getLogger("sqlalchemy.pool").setLevel(logging.ERROR)
logging.getLogger("sqlalchemy.orm").setLevel(logging.ERROR)
logging.getLogger("hypercorn.error").setLevel(logging.INFO)
logging.getLogger("hypercorn.access").setLevel(logging.INFO)


async def handle_recognition_event(result: dict, stream_url: str):
    """
    Handle recognition events from stream processor.
    
    Args:
        result: Recognition result from model server
        stream_url: RTSP stream URL
    """
    try:
        detections_data = []
        
        async with AsyncSessionLocal() as db:
            for detection in result.get("detections", []):
                # Get student name if matched
                student_name = None
                if detection.get("matched") and detection.get("student_id"):
                    from sqlalchemy import select
                    result_query = await db.execute(
                        select(Student).where(Student.student_id == detection["student_id"])
                    )
                    student = result_query.scalar_one_or_none()
                    if student:
                        student_name = f"{student.first_name} {student.last_name or ''}".strip()
                
                # Store attendance event in database
                if detection.get("matched"):
                    attendance_event = AttendanceEvent(
                        student_id=detection.get("student_id"),
                        stream_url=stream_url,
                        camera_frame_time=datetime.fromisoformat(result.get("timestamp")),
                        match_confidence=detection.get("match_confidence", 0.0),
                        match_modality="face",
                        matcher_model_version=detection.get("model_version", "ArcFace"),
                        bbox=json.dumps(detection.get("bbox", [])),
                        is_live=detection.get("is_live", True)
                    )
                    db.add(attendance_event)
                    await db.commit()
                    
                    logger.info(f"✅ Attendance recorded: {detection['student_id']} ({student_name})")
                
                # Prepare detection data for WebSocket
                detections_data.append({
                    "bbox": detection.get("bbox", []),
                    "matched": detection.get("matched", False),
                    "student_id": detection.get("student_id"),
                    "student_name": student_name,
                    "match_confidence": detection.get("match_confidence"),
                    "match_modality": "face",
                    "models_used": {"face": detection.get("model_version", "ArcFace")},
                    "thumbnail_url": None,  # TODO: Store thumbnail if needed
                    "is_live": detection.get("is_live", True)
                })
        
        # Broadcast recognition event via WebSocket
        event = {
            "type": "recognition_event",
            "stream_url": stream_url,
            "frame_time": result.get("timestamp"),
            "detections": detections_data
        }
        
        await broadcast_recognition_event(event)
    
    except Exception as e:
        logger.error(f"❌ Error handling recognition event: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    # Startup
    logger.info("🚀 Starting Face Recognition Backend...")
    
    # Initialize database
    await init_db()
    logger.info("✅ Database initialized")
    
    # Initialize model server connection
    await model_server_service._login()
    logger.info("✅ Model server connected")
    
    # Start RTSP stream processors
    if settings.rtsp_stream_list:
        for stream_url in settings.rtsp_stream_list:
            await stream_manager.add_stream(
                stream_url=stream_url,
                on_recognition=handle_recognition_event
            )
        logger.info(f"✅ Started {len(settings.rtsp_stream_list)} RTSP stream processors")
    else:
        logger.warning("⚠️ No RTSP streams configured")
    
    logger.info("✅ Backend is ready!")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down Face Recognition Backend...")
    
    # Stop stream processors
    await stream_manager.stop_all()
    logger.info("✅ Stream processors stopped")
    
    # Close model server connection
    await model_server_service.close()
    logger.info("✅ Model server connection closed")
    
    logger.info("👋 Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Face Recognition Backend API",
    description="Backend service for face recognition attendance system",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (photos)
photos_dir = Path(settings.photos_dir)
photos_dir.mkdir(parents=True, exist_ok=True)
app.mount("/photos", StaticFiles(directory=str(photos_dir)), name="photos")

# Register routes
app.include_router(health_routes.router, prefix="/api/v1/backend")
app.include_router(auth_routes.router, prefix="/api/v1/backend")
app.include_router(student_routes.router, prefix="/api/v1/backend")
app.include_router(websocket_routes.router, prefix="/api/v1/backend")


if __name__ == "__main__":
    import asyncio
    from hypercorn.config import Config
    from hypercorn.asyncio import serve
    
    # Hypercorn 0.18.0 configuration
    config = Config()
    config.bind = [f"{settings.backend_host}:{settings.backend_port}"]
    config.accesslog = "-"
    config.errorlog = "-"
    config.loglevel = "DEBUG" if settings.debug else "INFO"
    config.worker_class = "asyncio"
    
    # HTTP/2 and WebSocket improvements in 0.18.0
    config.alpn_protocols = ["h2", "http/1.1"]
    config.websocket_ping_interval = 20
    config.keep_alive_timeout = 5
    
    if settings.debug:
        config.use_reloader = True
    
    logger.info(f"🚀 Starting Hypercorn v0.18.0 on {config.bind[0]}")
    asyncio.run(serve(app, config))
