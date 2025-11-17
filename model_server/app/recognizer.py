"""
ArcFace Recognition Engine using DeepFace.

Complete ML Stack Implementation:
1. Face Detection (YOLOv8n via DeepFace)
2. Face Alignment (Geometric transform using landmarks)
3. Embedding Extraction (ArcFace ResNet100 - 512D)
4. Matching (Cosine similarity)
5. Anti-Spoofing (Optional liveness detection)

Architecture follows:
Camera → YOLOv8n → Alignment → Preprocessing → ArcFace → Matching → Result
"""

from __future__ import annotations

import logging
import sqlite3
import os
from typing import List, Tuple, Optional, Dict, Any
import numpy as np
from pathlib import Path
import base64

logger = logging.getLogger(__name__)


class DeepFaceRecognitionEngine:
    """
    Complete DeepFace-based recognition engine.
    
    Pipeline:
    1. YOLOv8n detection (via DeepFace detector_backend="yolov8")
    2. Geometric alignment (using eye/nose landmarks)
    3. ArcFace embedding extraction (512-D)
    4. Cosine similarity matching
    5. Anti-spoofing (optional)
    """
    
    def __init__(
        self,
        model_name: str = "ArcFace",
        detector_backend: str = "yolov8",
        distance_metric: str = "cosine",
        enrollment_db_path: str = "./storage/enrollments.db",
        align: bool = True,
        anti_spoof: bool = True,
        normalization: str = "ArcFace",
        deepface_home: str = "./storage/.deepface"
    ):
        """
        Initialize DeepFace recognition engine.
        
        Args:
            model_name: Recognition model (ArcFace for 512-D embeddings)
            detector_backend: Detector (yolov8 for YOLOv8n)
            distance_metric: Distance metric (cosine recommended for ArcFace)
            enrollment_db_path: Path to enrollment database
            align: Enable face alignment
            anti_spoof: Enable anti-spoofing
            normalization: Normalization technique
            deepface_home: DeepFace model cache directory
        """
        self.model_name = model_name
        self.detector_backend = detector_backend
        self.distance_metric = distance_metric
        self.enrollment_db_path = enrollment_db_path
        self.align = align
        self.anti_spoof = anti_spoof
        self.normalization = normalization
        
        # Set DeepFace home directory
        os.environ["DEEPFACE_HOME"] = deepface_home
        Path(deepface_home).mkdir(parents=True, exist_ok=True)
        
        # Initialize DeepFace
        self._init_deepface()
        
        # Initialize enrollment database
        self._init_enrollment_db()
        
        # Load enrollments into memory
        self.enrollments: Dict[str, Dict[str, np.ndarray]] = {}  # {student_id: {view: embedding}}
        self._load_enrollments()
        
        logger.info(
            f"DeepFace Recognition Engine initialized: "
            f"model={model_name}, detector={detector_backend}, "
            f"metric={distance_metric}, align={align}, anti_spoof={anti_spoof}"
        )
    
    def _init_deepface(self) -> None:
        """Initialize DeepFace models (lazy loading)."""
        try:
            from deepface import DeepFace
            self.deepface = DeepFace
            
            # Warm up the model by building it (downloads weights if needed)
            logger.info(f"Initializing DeepFace model: {self.model_name}")
            logger.info(f"Detector backend: {self.detector_backend}")
            
            # Build model using new DeepFace 0.0.95 API
            # DeepFace.build_model() handles model loading internally
            try:
                model = self.deepface.build_model(self.model_name)
                logger.info(f"✓ {self.model_name} model loaded successfully")
                
                if self.model_name == "ArcFace":
                    logger.info("  → ResNet100 architecture, 512-D embeddings")
                elif self.model_name == "Facenet512":
                    logger.info("  → Inception ResNet v1, 512-D embeddings")
                elif self.model_name == "VGG-Face":
                    logger.info("  → VGG16 architecture")
            except Exception as e:
                logger.warning(f"Model build warning (will retry on first use): {e}")
            
            # Initialize detector
            logger.info(f"Initializing detector: {self.detector_backend}")
            
            # Test detection with dummy image
            dummy_img = np.ones((160, 160, 3), dtype=np.uint8) * 128
            
            try:
                faces = self.deepface.extract_faces(
                    img_path=dummy_img,
                    detector_backend=self.detector_backend,
                    enforce_detection=False,
                    align=self.align
                )
                logger.info(f"✓ Detector {self.detector_backend} initialized successfully")
            except Exception as e:
                logger.warning(f"Detector initialization warning: {e}")
            
            logger.info("✓ DeepFace initialization complete")
            
        except ImportError as e:
            logger.error(f"DeepFace not installed: {e}")
            logger.error("Install with: pip install deepface")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize DeepFace: {e}")
            raise
    
    def _init_enrollment_db(self) -> None:
        """Initialize enrollment database."""
        db_path = Path(self.enrollment_db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.enrollment_db_path)
        cursor = conn.cursor()
        
        # Create enrollments table with multi-view support
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS enrollments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                view TEXT NOT NULL,
                embedding BLOB NOT NULL,
                embedding_dim INTEGER NOT NULL,
                model_version TEXT NOT NULL,
                detector_backend TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(student_id, view)
            )
        """)
        
        # Create index for fast lookup
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_student_id ON enrollments(student_id)
        """)
        
        conn.commit()
        conn.close()
        logger.info(f"✓ Enrollment database initialized at {self.enrollment_db_path}")
    
    def _load_enrollments(self) -> None:
        """Load all enrollments from database into memory."""
        conn = sqlite3.connect(self.enrollment_db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT student_id, view, embedding, embedding_dim 
            FROM enrollments
        """)
        rows = cursor.fetchall()
        
        for student_id, view, embedding_bytes, dim in rows:
            embedding = np.frombuffer(embedding_bytes, dtype=np.float32).reshape(dim)
            
            if student_id not in self.enrollments:
                self.enrollments[student_id] = {}
            
            self.enrollments[student_id][view] = embedding
        
        conn.close()
        
        total_embeddings = sum(len(views) for views in self.enrollments.values())
        logger.info(
            f"✓ Loaded {len(self.enrollments)} students with "
            f"{total_embeddings} total embeddings"
        )
    
    def extract_embedding(
        self,
        image: np.ndarray,
        enforce_detection: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Extract face embedding from image using complete DeepFace pipeline.
        
        Pipeline:
        1. Face detection (YOLOv8n)
        2. Face alignment (geometric transform)
        3. Preprocessing (resize to 112x112, normalize)
        4. ArcFace forward pass (512-D embedding)
        5. Optional anti-spoofing
        
        Args:
            image: Image array in BGR or RGB format (H, W, 3)
            enforce_detection: Raise error if no face detected
            
        Returns:
            Dict with:
                - embedding: np.ndarray (512,) for ArcFace
                - bbox: Bounding box [x, y, w, h]
                - confidence: Detection confidence
                - is_live: Anti-spoof result (if enabled)
                - facial_area: Dict with detailed face location
            Or None if no face detected
        """
        try:
            # Extract faces with full pipeline
            # This internally does: detection → alignment → embedding
            result = self.deepface.represent(
                img_path=image,
                model_name=self.model_name,
                detector_backend=self.detector_backend,
                enforce_detection=enforce_detection,
                align=self.align,
                normalization=self.normalization
            )
            
            if not result:
                logger.warning("No face detected in image")
                return None
            
            # Get first face (highest confidence)
            face_result = result[0]
            
            # Filter by detection confidence to reduce false positives
            from app.config import config as model_config
            detection_confidence = face_result.get("face_confidence", 0.99)
            if detection_confidence < model_config.detection_confidence_threshold:
                logger.info(
                    f"❌ Face detection confidence too low: {detection_confidence:.3f} "
                    f"(threshold: {model_config.detection_confidence_threshold:.3f})"
                )
                return None
            
            embedding = np.array(face_result["embedding"], dtype=np.float32)
            facial_area = face_result["facial_area"]
            
            # Anti-spoofing check if enabled
            is_live = True
            if self.anti_spoof:
                try:
                    # Extract face for anti-spoof check
                    faces = self.deepface.extract_faces(
                        img_path=image,
                        detector_backend=self.detector_backend,
                        enforce_detection=False,
                        align=self.align,
                        anti_spoofing=True
                    )
                    
                    if faces and len(faces) > 0:
                        is_live = faces[0].get("is_real", True)
                        logger.debug(f"Anti-spoof check: is_live={is_live}")
                
                except Exception as e:
                    logger.warning(f"Anti-spoof check failed: {e}")
                    is_live = True  # Default to accepting if anti-spoof fails
            
            logger.debug(
                f"Embedding extracted: dim={len(embedding)}, "
                f"bbox={facial_area}, is_live={is_live}"
            )
            
            return {
                "embedding": embedding,
                "bbox": [
                    facial_area["x"],
                    facial_area["y"],
                    facial_area["w"],
                    facial_area["h"]
                ],
                "confidence": face_result.get("face_confidence", 0.99),
                "is_live": is_live,
                "facial_area": facial_area
            }
            
        except ValueError as e:
            # No face detected
            if enforce_detection:
                logger.error(f"No face detected (enforce_detection=True): {e}")
                raise
            else:
                logger.warning(f"No face detected: {e}")
                return None
        
        except Exception as e:
            logger.error(f"Failed to extract embedding: {e}", exc_info=True)
            if enforce_detection:
                raise
            return None
    
    def match_embedding(
        self,
        query_embedding: np.ndarray,
        threshold: Optional[float] = None
    ) -> Optional[Tuple[str, float, str]]:
        """
        Match query embedding against all enrolled embeddings.
        
        Uses cosine distance:
        D_cosine(A, B) = 1 - (A · B) / (||A|| * ||B||)
        
        For ArcFace with cosine metric, threshold ≈ 0.35 is recommended.
        
        Args:
            query_embedding: Query face embedding (512,)
            threshold: Distance threshold (None uses default from config)
            
        Returns:
            Tuple of (student_id, match_confidence, matched_view) or None
            match_confidence = 1 - distance (higher is better)
        """
        if not self.enrollments:
            logger.warning("No enrollments available for matching")
            return None
        
        if threshold is None:
            # Import config here to avoid circular dependency
            from app.config import config
            threshold = config.recognition_threshold
        
        best_match = None
        best_distance = float('inf')
        best_view = None
        
        # Normalize query embedding for cosine similarity
        query_norm = query_embedding / (np.linalg.norm(query_embedding) + 1e-6)
        
        # Compare against all enrolled embeddings
        for student_id, views in self.enrollments.items():
            for view_name, enrolled_emb in views.items():
                # Normalize enrolled embedding
                enrolled_norm = enrolled_emb / (np.linalg.norm(enrolled_emb) + 1e-6)
                
                # Compute cosine distance
                if self.distance_metric == "cosine":
                    similarity = np.dot(query_norm, enrolled_norm)
                    distance = 1.0 - similarity
                elif self.distance_metric == "euclidean_l2":
                    distance = np.linalg.norm(query_norm - enrolled_norm)
                else:  # euclidean
                    distance = np.linalg.norm(query_embedding - enrolled_emb)
                
                if distance < best_distance:
                    best_distance = distance
                    best_match = student_id
                    best_view = view_name
        
        # Check threshold
        if best_match and best_distance <= threshold:
            confidence = 1.0 - best_distance  # Convert distance to confidence
            logger.info(
                f"✅ Match found: {best_match} (view: {best_view}, "
                f"confidence: {confidence:.3f}, distance: {best_distance:.3f}, threshold: {threshold:.3f})"
            )
            return best_match, confidence, best_view
        
        logger.info(
            f"❌ No match (best: {best_match}, distance: {best_distance:.3f}, "
            f"threshold: {threshold:.3f}, diff: {(best_distance - threshold):.3f})"
        )
        return None
    
    def enroll_multi_view(
        self,
        student_id: str,
        images: Dict[str, np.ndarray],
        replace: bool = True
    ) -> Dict[str, Any]:
        """
        Enroll student with multiple view images.
        
        Args:
            student_id: Student identifier
            images: Dict of {view_name: image_array}
                   e.g., {"front": img1, "left": img2, ...}
            replace: Whether to replace existing enrollments
            
        Returns:
            Dict with enrollment results for each view
        """
        results = {}
        embeddings_stored = []
        
        conn = sqlite3.connect(self.enrollment_db_path)
        cursor = conn.cursor()
        
        try:
            for view_name, image in images.items():
                logger.info(f"Processing {view_name} view for {student_id}")
                
                # Extract embedding
                result = self.extract_embedding(image, enforce_detection=True)
                
                if result is None:
                    results[view_name] = {
                        "success": False,
                        "error": "No face detected"
                    }
                    continue
                
                embedding = result["embedding"]
                is_live = result["is_live"]
                
                if not is_live and self.anti_spoof:
                    results[view_name] = {
                        "success": False,
                        "error": "Spoofing detected"
                    }
                    continue
                
                # Store in database
                embedding_bytes = embedding.astype(np.float32).tobytes()
                
                if replace:
                    cursor.execute("""
                        INSERT OR REPLACE INTO enrollments 
                        (student_id, view, embedding, embedding_dim, model_version, detector_backend)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        student_id,
                        view_name,
                        embedding_bytes,
                        len(embedding),
                        self.model_name,
                        self.detector_backend
                    ))
                else:
                    cursor.execute("""
                        INSERT INTO enrollments 
                        (student_id, view, embedding, embedding_dim, model_version, detector_backend)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        student_id,
                        view_name,
                        embedding_bytes,
                        len(embedding),
                        self.model_name,
                        self.detector_backend
                    ))
                
                # Update in-memory cache
                if student_id not in self.enrollments:
                    self.enrollments[student_id] = {}
                
                self.enrollments[student_id][view_name] = embedding
                embeddings_stored.append(view_name)
                
                results[view_name] = {
                    "success": True,
                    "embedding_dim": len(embedding),
                    "embedding_base64": base64.b64encode(embedding_bytes).decode('utf-8'),
                    "bbox": result["bbox"],
                    "is_live": is_live
                }
                
                logger.info(f"✓ {view_name} view enrolled for {student_id}")
            
            conn.commit()
            
            logger.info(
                f"✓ Enrollment complete for {student_id}: "
                f"{len(embeddings_stored)}/{len(images)} views stored"
            )
            
            return {
                "student_id": student_id,
                "model_version": self.model_name,
                "detector_backend": self.detector_backend,
                "embeddings": results,
                "status": "success" if embeddings_stored else "failed"
            }
        
        except Exception as e:
            conn.rollback()
            logger.error(f"Enrollment failed for {student_id}: {e}", exc_info=True)
            raise
        
        finally:
            conn.close()
    
    def recognize_frame(
        self,
        frame: np.ndarray,
        threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Recognize all faces in a frame.
        
        Pipeline:
        1. Detect all faces (YOLOv8n)
        2. Extract embeddings for each face (ArcFace)
        3. Match against enrollment database
        4. Return recognition results
        
        Args:
            frame: Frame image array (H, W, 3)
            threshold: Recognition threshold
            
        Returns:
            List of detection dicts with recognition results
        """
        detections = []
        
        try:
            # Extract all faces from frame
            faces = self.deepface.extract_faces(
                img_path=frame,
                detector_backend=self.detector_backend,
                enforce_detection=False,
                align=self.align,
                anti_spoofing=self.anti_spoof
            )
            
            logger.info(f"🔍 YOLO detected {len(faces)} face(s) in frame")
            
            # Import config for detection confidence threshold
            from app.config import config as model_config
            
            for idx, face_obj in enumerate(faces):
                facial_area = face_obj.get("facial_area", {})
                if not facial_area:
                    logger.warning(f"⚠️ Face {idx+1} has no facial_area")
                    continue
                
                # Check YOLO detection confidence
                detection_conf = face_obj.get("confidence", 0.99)
                if detection_conf < model_config.detection_confidence_threshold:
                    logger.info(
                        f"⚠️ Face {idx+1} confidence too low: {detection_conf:.3f} "
                        f"(threshold: {model_config.detection_confidence_threshold:.3f}) - SKIPPING"
                    )
                    continue
                
                # Extract embedding for this face
                x, y, w, h = facial_area["x"], facial_area["y"], facial_area["w"], facial_area["h"]
                
                # Validate bbox size - reject if too large (likely false detection)
                frame_h, frame_w = frame.shape[:2]
                bbox_area = w * h
                frame_area = frame_w * frame_h
                bbox_ratio = bbox_area / frame_area
                
                if bbox_ratio > 0.9:  # If bbox covers >90% of frame, it's likely a false detection
                    logger.warning(
                        f"⚠️ Face {idx+1} bbox too large ({bbox_ratio*100:.1f}% of frame) - likely false detection, SKIPPING"
                    )
                    continue
                
                face_crop = frame[y:y+h, x:x+w]
                
                embedding_result = self.extract_embedding(
                    face_crop,
                    enforce_detection=False
                )
                
                if embedding_result is None:
                    continue
                
                embedding = embedding_result["embedding"]
                is_live = embedding_result["is_live"]
                
                # Match against enrollments
                match_result = self.match_embedding(embedding, threshold)
                
                detection = {
                    "bbox": [x, y, x + w, y + h],  # Convert to [x1, y1, x2, y2]
                    "confidence": face_obj.get("confidence", 0.99),
                    "is_live": is_live,
                    "matched": match_result is not None,
                    "student_id": None,
                    "match_confidence": None,
                    "matched_view": None
                }
                
                if match_result:
                    student_id, match_conf, matched_view = match_result
                    detection.update({
                        "student_id": student_id,
                        "match_confidence": match_conf,
                        "matched_view": matched_view
                    })
                
                detections.append(detection)
            
            return detections
        
        except Exception as e:
            logger.error(f"Frame recognition failed: {e}", exc_info=True)
            return []
    
    def get_enrollment_count(self) -> int:
        """Get total number of enrolled students."""
        return len(self.enrollments)
    
    def get_total_embeddings(self) -> int:
        """Get total number of stored embeddings (across all views)."""
        return sum(len(views) for views in self.enrollments.values())
    
    def reload_enrollments(self) -> None:
        """Reload enrollments from database (for syncing after external updates)."""
        logger.info("Reloading enrollments from database...")
        self.enrollments.clear()
        self._load_enrollments()
