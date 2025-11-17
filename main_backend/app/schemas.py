"""
Pydantic schemas for request/response validation.
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, List, Any
from datetime import datetime


# ==================== Authentication Schemas ====================

class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    email: Optional[EmailStr] = None
    full_name: str
    role: str = Field(..., pattern="^(admin|operator)$")


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: Optional[Dict[str, Any]] = None


class TokenRefresh(BaseModel):
    refresh_token: str


class TokenRefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class LogoutRequest(BaseModel):
    refresh_token: str


class LogoutResponse(BaseModel):
    status: str = "logged_out"


# ==================== Student Schemas ====================

class StudentCreate(BaseModel):
    student_id: str = Field(..., pattern="^[0-9]{9}$")  # e.g., 202500568
    first_name: str
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class StudentResponse(BaseModel):
    student_id: str
    status: str
    created_at: datetime


class StudentEnrollImages(BaseModel):
    front: str  # base64 or file path
    left: str
    right: str
    angled_left: str
    angled_right: str


class StudentEnrollMetadata(BaseModel):
    uploaded_by: Optional[str] = None
    remarks: Optional[str] = None
    timestamp: Optional[datetime] = None


class StudentEnrollRequest(BaseModel):
    images: StudentEnrollImages
    metadata: Optional[StudentEnrollMetadata] = None


class StudentEnrollResponse(BaseModel):
    student_id: str
    photo_record_id: str
    model_server_status: str  # Status from model server enrollment
    model_version: str  # Model version used (e.g., "ArcFace")
    views_enrolled: int  # Number of views successfully enrolled
    status: str


class StudentDetailPhotos(BaseModel):
    front: str
    left: str
    right: str
    angled_left: str
    angled_right: str


class StudentDetailResponse(BaseModel):
    student_id: str
    first_name: str
    last_name: Optional[str]
    email: Optional[str]
    photos: Optional[StudentDetailPhotos]
    model_server_enrolled: bool  # True if enrolled in model server
    status: str


# ==================== Recognition Event Schemas ====================

class DetectionInfo(BaseModel):
    bbox: List[int]  # [x1, y1, x2, y2]
    matched: bool
    student_id: Optional[str]
    student_name: Optional[str]
    match_confidence: Optional[float]
    match_modality: str
    models_used: Optional[Dict[str, str]]
    thumbnail_url: Optional[str]
    is_live: bool = True


class RecognitionEvent(BaseModel):
    type: str = "recognition_event"
    stream_url: str
    frame_time: datetime
    detections: List[DetectionInfo]


# ==================== WebSocket Messages ====================

class WSMessage(BaseModel):
    type: str
    data: Dict[str, Any]


# ==================== Health Check ====================

class HealthResponse(BaseModel):
    status: str
    database: str
    model_server: str
    active_streams: int
    total_students: int
