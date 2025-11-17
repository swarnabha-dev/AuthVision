"""
Model Server API Endpoints - Secure Internal Service.

Following the exact ML stack architecture:
- YOLOv8n (detection via DeepFace detector_backend="yolov8")
- Geometric alignment (using landmarks)
- ArcFace (512-D embeddings)
- Cosine similarity matching
- Anti-spoofing

API Contract (Internal - Never exposed to frontend):
1. POST /v1/enroll_embeddings - Generate embeddings from multi-view images
2. POST /v1/recognize_frame - Detect and recognize faces in frame
3. GET /v1/health - Health check
4. GET /v1/models - Model information
5. POST /v1/reload_enrollments - Reload enrollment database
"""

from __future__ import annotations

import logging
import uuid
import base64
from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, HTTPException, status, Header, Depends
from pydantic import BaseModel, StrictStr, StrictInt, StrictFloat, StrictBool, Field, ConfigDict
import numpy as np

from app.config import config
from app.recognizer import DeepFaceRecognitionEngine
from app.tracker import MultiStreamTracker, Track
from app.utils import decode_image_bytes, encode_image_to_base64, crop_bbox
from app.auth import User, get_current_active_user

logger = logging.getLogger(__name__)

router = APIRouter()

# Global instances (lazy-loaded)
recognizer: Optional[DeepFaceRecognitionEngine] = None
tracker: Optional[MultiStreamTracker] = None


def get_recognizer() -> DeepFaceRecognitionEngine:
    """Get or initialize recognition engine."""
    global recognizer
    if recognizer is None:
        logger.info("Initializing DeepFace Recognition Engine...")
        recognizer = DeepFaceRecognitionEngine(
            model_name=config.model_name,
            detector_backend=config.detector_backend,
            distance_metric=config.distance_metric,
            enrollment_db_path=config.enrollment_db_path,
            align=config.align,
            anti_spoof=config.anti_spoof_enabled,
            normalization=config.normalization,
            deepface_home=config.deepface_home
        )
    return recognizer


def get_tracker() -> MultiStreamTracker:
    """Get or initialize tracker."""
    global tracker
    if tracker is None:
        logger.info("Initializing MultiStreamTracker...")
        tracker = MultiStreamTracker(
            max_age=config.tracker_max_age,
            min_hits=config.tracker_min_hits,
            iou_threshold=config.tracker_iou_threshold
        )
    return tracker


# ===== Authentication Dependency =====

async def verify_internal_token(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """Verify authentication using JWT or API key."""
    return current_user


# ===== Pydantic v2 Schemas (Strict) =====

class EnrollmentImageInput(BaseModel):
    """Single view image for enrollment."""
    model_config = ConfigDict(extra='forbid')
    
    embedding_dim: StrictInt = Field(..., description="Embedding dimension")
    embedding_base64: StrictStr = Field(..., description="Base64 encoded embedding bytes")


class EnrollmentOptions(BaseModel):
    """Enrollment options."""
    model_config = ConfigDict(extra='forbid', protected_namespaces=())
    
    model_name: StrictStr = Field(default="ArcFace")
    detector_backend: StrictStr = Field(default="yolov8")
    align: StrictBool = Field(default=True)
    anti_spoof: StrictBool = Field(default=True)
    distance_metric: StrictStr = Field(default="cosine")


class EnrollEmbeddingsRequest(BaseModel):
    """Request for enrollment embedding generation."""
    model_config = ConfigDict(extra='forbid', validate_assignment=True)
    
    student_id: StrictStr = Field(..., min_length=1, max_length=100)
    images: Dict[str, str] = Field(
        ...,
        description="Dict of {view_name: base64_image}. Expected keys: front, left, right, angled_left, angled_right"
    )
    options: Optional[EnrollmentOptions] = Field(default=None)


class EmbeddingResult(BaseModel):
    """Single embedding result."""
    model_config = ConfigDict(extra='forbid')
    
    embedding_dim: StrictInt
    embedding_base64: StrictStr
    bbox: Optional[List[StrictInt]] = None
    is_live: StrictBool = Field(default=True)


class EnrollEmbeddingsResponse(BaseModel):
    """Response for enrollment (INTERNAL ONLY - never sent to frontend)."""
    model_config = ConfigDict(extra='forbid', protected_namespaces=())
    
    student_id: StrictStr
    model_version: StrictStr
    detector_backend: StrictStr
    embeddings: Dict[str, Dict[str, Any]] = Field(
        ...,
        description="Dict of {view_name: {success, embedding_dim, embedding_base64, bbox, is_live}}"
    )
    status: StrictStr


class RecognizeFrameOptions(BaseModel):
    """Recognition frame options."""
    model_config = ConfigDict(extra='forbid')
    
    align: StrictBool = Field(default=True)
    anti_spoof: StrictBool = Field(default=True)
    distance_metric: StrictStr = Field(default="cosine")
    min_confidence: StrictFloat = Field(default=0.35, ge=0.0, le=1.0)


class RecognizeFrameRequest(BaseModel):
    """Request for frame recognition."""
    model_config = ConfigDict(extra='forbid', validate_assignment=True)
    
    frame_id: StrictStr = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: StrictStr = Field(default_factory=lambda: datetime.utcnow().isoformat())
    stream_url: StrictStr = Field(..., description="RTSP stream URL")
    frame_base64: StrictStr = Field(..., description="Base64 encoded frame image")
    options: Optional[RecognizeFrameOptions] = Field(default=None)


class DetectionResult(BaseModel):
    """Single detection result (INTERNAL - backend only)."""
    model_config = ConfigDict(extra='forbid', protected_namespaces=())
    
    bbox: List[StrictInt] = Field(..., min_length=4, max_length=4, description="[x1, y1, x2, y2]")
    confidence: StrictFloat = Field(..., ge=0.0, le=1.0)
    is_live: StrictBool = Field(default=True)
    matched: StrictBool = Field(default=False)
    student_id: Optional[StrictStr] = None
    student_name: Optional[StrictStr] = None
    match_confidence: Optional[StrictFloat] = Field(default=None, ge=0.0, le=1.0)
    match_modality: StrictStr = Field(default="face")
    matched_view: Optional[StrictStr] = None
    model_version: StrictStr = Field(default="arcface_v1")
    thumbnail_base64: Optional[StrictStr] = None


class RecognizeFrameResponse(BaseModel):
    """Response for frame recognition (INTERNAL - backend only)."""
    model_config = ConfigDict(extra='forbid')
    
    frame_id: StrictStr
    timestamp: StrictStr
    stream_url: StrictStr
    detections: List[DetectionResult] = Field(default_factory=list)


class HealthResponse(BaseModel):
    """Health check response."""
    model_config = ConfigDict(extra='forbid')
    
    status: StrictStr = Field(default="healthy")
    models_loaded: Dict[str, StrictBool] = Field(default_factory=dict)
    enrollment_count: StrictInt = Field(default=0)
    total_embeddings: StrictInt = Field(default=0)
    ml_stack: Dict[str, str] = Field(default_factory=dict)


class ModelsResponse(BaseModel):
    """Active models response."""
    model_config = ConfigDict(extra='forbid', protected_namespaces=())
    
    recognizer: StrictStr
    detector: StrictStr
    distance_metric: StrictStr
    embedding_dim: StrictInt
    alignment_enabled: StrictBool
    anti_spoof_enabled: StrictBool
    normalization: StrictStr




# ===== API Endpoints =====

@router.post(
    "/v1/enroll_embeddings",
    response_model=EnrollEmbeddingsResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_internal_token)]
)
async def enroll_embeddings(request: EnrollEmbeddingsRequest) -> EnrollEmbeddingsResponse:
    """
    Generate embeddings for multi-view enrollment.
    
    🔒 INTERNAL ONLY - Called by main backend, never by frontend.
    
    Pipeline:
    1. Decode base64 images
    2. YOLOv8n detection (via DeepFace)
    3. Face alignment (geometric transform)
    4. ArcFace embedding extraction (512-D)
    5. Anti-spoofing check
    6. Return embeddings (base64 encoded)
    
    Backend will:
    - Store embeddings in its database (encrypted)
    - Never send embeddings to frontend
    - Return only enrollment status to frontend
    
    Args:
        request: Enrollment request with student_id and base64 images
        
    Returns:
        Embeddings for each view (INTERNAL - never exposed)
    """
    try:
        logger.info(f"📸 Enrollment request for student: {request.student_id}")
        
        # Decode images
        images = {}
        for view_name, base64_str in request.images.items():
            try:
                image_bytes = base64.b64decode(base64_str)
                image_array = decode_image_bytes(image_bytes)
                images[view_name] = image_array
                logger.debug(f"  ✓ Decoded {view_name}: {image_array.shape}")
            except Exception as e:
                logger.error(f"  ✗ Failed to decode {view_name}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid image data for view: {view_name}"
                )
        
        # Get recognizer
        rec = get_recognizer()
        
        # Process enrollment (multi-view)
        result = rec.enroll_multi_view(
            student_id=request.student_id,
            images=images,
            replace=True
        )
        
        logger.info(
            f"✓ Enrollment complete: {request.student_id} - "
            f"status={result['status']}, views={len(result['embeddings'])}"
        )
        
        return EnrollEmbeddingsResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Enrollment failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Enrollment processing failed: {str(e)}"
        )


@router.post(
    "/v1/recognize_frame",
    response_model=RecognizeFrameResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_internal_token)]
)
async def recognize_frame(request: RecognizeFrameRequest) -> RecognizeFrameResponse:
    """
    Recognize faces in a frame using complete ML pipeline.
    
    🔒 INTERNAL ONLY - Called by main backend, never by frontend.
    
    Complete Pipeline:
    1. YOLOv8n Detection (bbox + landmarks)
    2. Face Alignment (geometric transform using eye/nose landmarks)
    3. Preprocessing (resize to 112×112, normalize)
    4. ArcFace Embedding (512-D via ResNet100)
    5. Cosine Similarity Matching (against enrolled embeddings)
    6. Anti-Spoofing (liveness detection)
    7. Tracking (ByteTrack + Kalman for stable IDs)
    
    Backend will:
    - Store attendance events in DB
    - Push recognition results via WebSocket (no embeddings)
    - Frontend receives only: student_id, confidence, bbox
    
    Args:
        request: Frame recognition request
        
    Returns:
        Detection and recognition results (INTERNAL - no embeddings)
    """
    try:
        logger.info(f"🔍 Recognition request: frame_id={request.frame_id}, stream={request.stream_url}")
        
        # Decode frame
        try:
            frame_bytes = base64.b64decode(request.frame_base64)
            frame_array = decode_image_bytes(frame_bytes)
            logger.debug(f"  ✓ Decoded frame: {frame_array.shape}")
        except Exception as e:
            logger.error(f"  ✗ Failed to decode frame: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid frame data"
            )
        
        # Get components
        rec = get_recognizer()
        trk = get_tracker()
        
        # Override threshold if provided
        threshold = None
        if request.options:
            threshold = request.options.min_confidence
        
        # Step 1: Recognize all faces in frame
        # This internally does: detection → alignment → embedding → matching
        face_detections = rec.recognize_frame(frame_array, threshold=threshold)
        
        logger.info(f"  📊 Detected {len(face_detections)} faces")
        
        # Step 2: Convert to tracker format
        tracker_detections = []
        for det in face_detections:
            bbox = det["bbox"]
            conf = det["confidence"]
            tracker_detections.append((tuple(bbox), conf))
        
        # Step 3: Update tracker
        tracks = trk.update(request.stream_url, tracker_detections)
        
        logger.debug(f"  🎯 Active tracks: {len(tracks)}")
        
        # Step 4: Build detection results with tracking info
        detection_results = []
        
        for idx, det in enumerate(face_detections):
            # Find corresponding track
            track = None
            if idx < len(tracks):
                track = tracks[idx]
            
            # Create thumbnail
            thumbnail_base64 = None
            try:
                x1, y1, x2, y2 = det["bbox"]
                face_crop = frame_array[y1:y2, x1:x2]
                thumbnail_base64 = encode_image_to_base64(face_crop)
            except Exception as e:
                logger.warning(f"  ⚠️  Failed to create thumbnail: {e}")
            
            # Build result
            result = DetectionResult(
                bbox=det["bbox"],
                confidence=det["confidence"],
                is_live=det["is_live"],
                matched=det["matched"],
                student_id=det["student_id"],
                student_name=det["student_id"],  # Backend will resolve full name
                match_confidence=det["match_confidence"],
                match_modality="face",
                matched_view=det.get("matched_view"),
                model_version=config.model_name.lower() + "_v1",
                thumbnail_base64=thumbnail_base64
            )
            
            detection_results.append(result)
            
            if det["matched"]:
                logger.info(
                    f"  ✓ Match: {det['student_id']} "
                    f"(conf={det['match_confidence']:.3f}, view={det.get('matched_view')})"
                )
        
        response = RecognizeFrameResponse(
            frame_id=request.frame_id,
            timestamp=request.timestamp,
            stream_url=request.stream_url,
            detections=detection_results
        )
        
        logger.info(
            f"✓ Recognition complete: {len(detection_results)} detections, "
            f"{sum(1 for d in detection_results if d.matched)} matched"
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Recognition failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Recognition processing failed: {str(e)}"
        )


@router.get("/v1/health", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def health() -> HealthResponse:
    """
    Health check endpoint.
    
    Returns model loading status, enrollment counts, and ML stack info.
    """
    global recognizer, tracker
    
    enrollment_count = 0
    total_embeddings = 0
    
    if recognizer is not None:
        enrollment_count = recognizer.get_enrollment_count()
        total_embeddings = recognizer.get_total_embeddings()
    
    ml_stack = {
        "detector": f"YOLOv8n (via DeepFace detector_backend={config.detector_backend})",
        "alignment": "Geometric transform (eye/nose landmarks)",
        "preprocessor": "Resize 112×112, normalize",
        "recognizer": f"{config.model_name} (ResNet100, 512-D)",
        "matcher": f"{config.distance_metric} similarity",
        "anti_spoof": "Liveness detection" if config.anti_spoof_enabled else "Disabled",
        "tracker": "ByteTrack + Kalman filter"
    }
    
    return HealthResponse(
        status="healthy",
        models_loaded={
            "recognizer": recognizer is not None,
            "tracker": tracker is not None
        },
        enrollment_count=enrollment_count,
        total_embeddings=total_embeddings,
        ml_stack=ml_stack
    )


@router.get("/v1/models", response_model=ModelsResponse, status_code=status.HTTP_200_OK)
async def get_models() -> ModelsResponse:
    """Get active model configuration."""
    return ModelsResponse(
        recognizer=config.model_name,
        detector=config.detector_backend,
        distance_metric=config.distance_metric,
        embedding_dim=config.embedding_dim,
        alignment_enabled=config.align,
        anti_spoof_enabled=config.anti_spoof_enabled,
        normalization=config.normalization
    )


@router.post(
    "/v1/reload_enrollments",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_internal_token)]
)
async def reload_enrollments() -> Dict[str, Any]:
    """
    Reload enrollments from database.
    
    🔒 INTERNAL ONLY - Called by backend after external enrollment updates.
    """
    try:
        rec = get_recognizer()
        rec.reload_enrollments()
        
        return {
            "success": True,
            "enrollment_count": rec.get_enrollment_count(),
            "total_embeddings": rec.get_total_embeddings(),
            "message": "Enrollments reloaded successfully"
        }
    except Exception as e:
        logger.error(f"Reload failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Reload failed: {str(e)}"
        )
