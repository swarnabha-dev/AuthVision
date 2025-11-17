"""
Student management routes.
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models import User, Student, StudentPhoto
from app.schemas import (
    StudentCreate, StudentResponse, StudentEnrollRequest,
    StudentEnrollResponse, StudentDetailResponse,
    StudentDetailPhotos
)
from app.dependencies import require_admin_or_operator, get_current_user
from app.services.model_server_service import model_server_service
from app.config import settings
from pathlib import Path
import base64
import json
from datetime import datetime
import logging
import shutil

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/students", tags=["Students"])


def is_base64(s: str) -> bool:
    """Check if string is base64 encoded."""
    try:
        if isinstance(s, str):
            # Check if it's a valid base64 string
            base64.b64decode(s, validate=True)
            return True
    except Exception:
        return False
    return False


async def save_image(image_data: str, student_id: str, view_name: str) -> str:
    """
    Save image to disk.
    
    Args:
        image_data: Base64 encoded image or file path
        student_id: Student ID
        view_name: View name (front, left, right, angled_left, angled_right)
    
    Returns:
        Saved file path
    """
    # Create student directory
    year = student_id[:4]  # Extract year from student_id
    student_dir = Path(settings.photos_dir) / year / student_id
    student_dir.mkdir(parents=True, exist_ok=True)
    
    # Determine file extension and decode if needed
    file_path = student_dir / f"{view_name}.jpg"
    
    if is_base64(image_data):
        # Decode base64 and save
        img_bytes = base64.b64decode(image_data)
        with open(file_path, "wb") as f:
            f.write(img_bytes)
    else:
        # Assume it's a file path, copy file
        source_path = Path(image_data)
        if source_path.exists():
            shutil.copy(source_path, file_path)
        else:
            raise ValueError(f"File not found: {image_data}")
    
    # Return relative path
    return str(file_path.relative_to(settings.photos_dir))


@router.post("", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
async def create_student(
    student_data: StudentCreate,
    current_user: User = Depends(require_admin_or_operator),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new student record.
    
    - **student_id**: 9-digit student ID (e.g., 202500568)
    - **first_name**: Student's first name
    - **last_name**: Student's last name (optional)
    - **email**: Student's email (optional)
    - **phone**: Contact number (optional)
    - **metadata**: Additional metadata as JSON (optional)
    """
    # Check if student already exists
    result = await db.execute(select(Student).where(Student.student_id == student_data.student_id))
    existing_student = result.scalar_one_or_none()
    
    if existing_student:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Student already exists"
        )
    
    # Create new student
    new_student = Student(
        student_id=student_data.student_id,
        first_name=student_data.first_name,
        last_name=student_data.last_name,
        email=student_data.email,
        phone=student_data.phone,
        student_metadata=json.dumps(student_data.metadata) if student_data.metadata else None
    )
    
    db.add(new_student)
    await db.commit()
    await db.refresh(new_student)
    
    logger.info(f"✅ Student created: {new_student.student_id} ({new_student.first_name})")
    
    return StudentResponse(
        student_id=new_student.student_id,
        status="created",
        created_at=new_student.created_at
    )


@router.post("/{student_id}/enroll", response_model=StudentEnrollResponse)
async def enroll_student(
    student_id: str,
    enroll_data: StudentEnrollRequest,
    current_user: User = Depends(require_admin_or_operator),
    db: AsyncSession = Depends(get_db)
):
    """
    Enroll a student by uploading 5 face images and generating embeddings.
    
    - **student_id**: Student ID (must exist in database)
    - **images**: Dict with keys: front, left, right, angled_left, angled_right
      - Each value can be base64 encoded image or file path
    - **metadata**: Optional metadata (uploaded_by, remarks, timestamp)
    
    This endpoint:
    1. Validates student exists
    2. Checks and encodes images to base64 if needed
    3. Saves images to disk
    4. Sends images to model server for embedding generation
    5. Stores photo paths in database
    6. Returns enrollment confirmation
    """
    # Check if student exists
    result = await db.execute(select(Student).where(Student.student_id == student_id))
    student = result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )
    
    # Validate all required images are present
    required_views = ["front", "left", "right", "angled_left", "angled_right"]
    images_dict = enroll_data.images.model_dump()
    
    for view in required_views:
        if not images_dict.get(view):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required image: {view}"
            )
    
    try:
        # Save images to disk
        logger.info(f"💾 Saving images for student: {student_id}")
        saved_paths = {}
        
        for view_name, image_data in images_dict.items():
            saved_path = await save_image(image_data, student_id, view_name)
            saved_paths[view_name] = saved_path
            logger.debug(f"  ✅ Saved {view_name}: {saved_path}")
        
        # Prepare images for model server (convert to base64 if needed and load bytes)
        logger.info(f"📤 Sending images to model server for embedding generation")
        images_for_model = {}
        
        for view_name, saved_path in saved_paths.items():
            # Read image from disk
            full_path = Path(settings.photos_dir) / saved_path
            with open(full_path, "rb") as f:
                img_bytes = f.read()
            
            # Send all views to model server with descriptive names
            # Model server can handle any number of views
            images_for_model[view_name] = img_bytes
            logger.debug(f"  ✓ Prepared {view_name} for model server ({len(img_bytes)} bytes)")
        
        # Call model server to generate embeddings
        enrollment_result = await model_server_service.enroll_student(
            student_id=student_id,
            images=images_for_model
        )
        
        logger.info(f"✅ Model server enrollment successful: {student_id}")
        logger.debug(f"   Model version: {enrollment_result.get('model_version', 'Unknown')}")
        logger.debug(f"   Views enrolled: {len(enrollment_result.get('embeddings', {}))}")
        
        # Store photo record in database
        photo_record = StudentPhoto(
            student_id=student_id,
            front_path=saved_paths["front"],
            left_path=saved_paths["left"],
            right_path=saved_paths["right"],
            angled_left_path=saved_paths["angled_left"],
            angled_right_path=saved_paths["angled_right"],
            uploaded_by=current_user.id
        )
        
        db.add(photo_record)
        await db.commit()
        await db.refresh(photo_record)
        
        logger.info(f"✅ Photo record saved for student: {student_id}")
        
        # Count successful enrollments from model server
        views_enrolled = 0
        if "embeddings" in enrollment_result:
            for view, embed_data in enrollment_result["embeddings"].items():
                if embed_data.get("success"):
                    views_enrolled += 1
        
        return StudentEnrollResponse(
            student_id=student_id,
            photo_record_id=photo_record.id,
            model_server_status="success",
            model_version=enrollment_result.get("model_version", "ArcFace"),
            views_enrolled=views_enrolled,
            status="enrolled"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Enrollment failed for {student_id}: {e}")
        error_msg = str(e)
        
        # Provide better error messages for common issues
        if "model server" in error_msg.lower() or "connect" in error_msg.lower() or "unreachable" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Model server is unavailable: {error_msg}"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Enrollment failed: {error_msg}"
            )


@router.get("/{student_id}", response_model=StudentDetailResponse)
async def get_student(
    student_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get student details including photos and enrollments.
    
    - **student_id**: Student ID
    
    Returns student information, photo paths, and enrollment details.
    """
    # Get student
    result = await db.execute(select(Student).where(Student.student_id == student_id))
    student = result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )
    
    # Get photos
    result = await db.execute(
        select(StudentPhoto)
        .where(StudentPhoto.student_id == student_id)
        .order_by(StudentPhoto.created_at.desc())
    )
    photo = result.first()
    
    photos = None
    if photo:
        photo_obj = photo[0]
        photos = StudentDetailPhotos(
            front=f"/photos/{photo_obj.front_path}",
            left=f"/photos/{photo_obj.left_path}",
            right=f"/photos/{photo_obj.right_path}",
            angled_left=f"/photos/{photo_obj.angled_left_path}",
            angled_right=f"/photos/{photo_obj.angled_right_path}"
        )
    
    # Check if student is enrolled in model server
    # Note: We don't store embeddings in main backend
    # Model server handles all enrollment data
    model_server_enrolled = photo is not None  # If photos exist, assume enrolled
    
    return StudentDetailResponse(
        student_id=student.student_id,
        first_name=student.first_name,
        last_name=student.last_name,
        email=student.email,
        photos=photos,
        model_server_enrolled=model_server_enrolled,
        status="enrolled" if model_server_enrolled else "registered"
    )
