"""
SQLAlchemy database models.
"""
from sqlalchemy import Column, String, Boolean, DateTime, Float, Integer, ForeignKey, LargeBinary, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base
import uuid


def generate_uuid():
    """Generate UUID string."""
    return str(uuid.uuid4())


class User(Base):
    """User model for authentication."""
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    username = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=True)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(String, nullable=False)  # admin or operator
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Student(Base):
    """Student model (dynamic partitioning by year in table name handled at runtime)."""
    __tablename__ = "students"
    
    student_id = Column(String, primary_key=True)  # e.g., 202500568
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    student_metadata = Column(Text, nullable=True)  # JSON string (renamed from 'metadata' to avoid SQLAlchemy conflict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    photos = relationship("StudentPhoto", back_populates="student", cascade="all, delete-orphan")
    # NOTE: Enrollments (embeddings) are stored in model_server DB, not here
    attendance_events = relationship("AttendanceEvent", back_populates="student", cascade="all, delete-orphan")


class StudentPhoto(Base):
    """Student photo storage paths."""
    __tablename__ = "student_photos"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    student_id = Column(String, ForeignKey("students.student_id", ondelete="CASCADE"), nullable=False)
    front_path = Column(String, nullable=False)
    left_path = Column(String, nullable=False)
    right_path = Column(String, nullable=False)
    angled_left_path = Column(String, nullable=False)
    angled_right_path = Column(String, nullable=False)
    uploaded_by = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    student = relationship("Student", back_populates="photos")
    uploader = relationship("User")


class AttendanceEvent(Base):
    """Real-time attendance events from recognition."""
    __tablename__ = "attendance_events"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    student_id = Column(String, ForeignKey("students.student_id", ondelete="SET NULL"), nullable=True)
    stream_url = Column(String, nullable=False)
    camera_frame_time = Column(DateTime(timezone=True), nullable=False)
    match_confidence = Column(Float, nullable=False)
    match_modality = Column(String, nullable=False)  # face, fused, etc.
    matcher_model_version = Column(String, nullable=False)
    bbox = Column(String, nullable=True)  # JSON string [x1, y1, x2, y2]
    thumbnail_path = Column(String, nullable=True)
    is_live = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    student = relationship("Student", back_populates="attendance_events")


class RefreshToken(Base):
    """Store refresh tokens for invalidation."""
    __tablename__ = "refresh_tokens"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = Column(String, unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_revoked = Column(Boolean, default=False)
