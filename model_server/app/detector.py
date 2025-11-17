"""YOLOv8 Face/Person Detector Wrapper."""

from __future__ import annotations

import logging
from typing import List, Tuple, Optional
import numpy as np

logger = logging.getLogger(__name__)


class YOLODetector:
    """YOLOv8 detector wrapper for face/person detection."""
    
    def __init__(self, model_path: str = "yolov8n.pt", device: str = "cpu"):
        """
        Initialize YOLO detector.
        
        Args:
            model_path: Path to YOLO model weights
            device: Device to run inference on ('cpu' or 'cuda')
        """
        self.model_path = model_path
        self.device = device
        self.model = None
        self._load_model()
    
    def _load_model(self) -> None:
        """Load YOLO model."""
        try:
            from ultralytics import YOLO
            logger.info(f"Loading YOLO model from {self.model_path}")
            self.model = YOLO(self.model_path)
            
            # Move to device
            if self.device == "cuda":
                self.model.to("cuda")
            
            logger.info(f"YOLO model loaded successfully on {self.device}")
            
        except ImportError:
            logger.error("ultralytics package not installed. Install with: pip install ultralytics")
            raise
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
            raise
    
    def detect(
        self, 
        image: np.ndarray, 
        conf_threshold: float = 0.5,
        target_class: Optional[int] = 0  # 0 = person in COCO
    ) -> List[Tuple[Tuple[int, int, int, int], float]]:
        """
        Detect objects in image.
        
        Args:
            image: Image array in BGR format (H, W, 3)
            conf_threshold: Confidence threshold
            target_class: Target class ID (0 for person, None for all)
            
        Returns:
            List of (bbox, confidence) where bbox is (x1, y1, x2, y2)
        """
        if self.model is None:
            raise RuntimeError("Model not loaded")
        
        try:
            # Run inference
            results = self.model(image, conf=conf_threshold, verbose=False)
            
            detections = []
            for result in results:
                boxes = result.boxes
                
                for box in boxes:
                    # Get box data
                    xyxy = box.xyxy[0].cpu().numpy()  # [x1, y1, x2, y2]
                    conf = float(box.conf[0].cpu().numpy())
                    cls = int(box.cls[0].cpu().numpy())
                    
                    # Filter by class if specified
                    if target_class is not None and cls != target_class:
                        continue
                    
                    bbox = (
                        int(xyxy[0]),
                        int(xyxy[1]),
                        int(xyxy[2]),
                        int(xyxy[3])
                    )
                    
                    detections.append((bbox, conf))
            
            logger.debug(f"Detected {len(detections)} objects with conf >= {conf_threshold}")
            return detections
            
        except Exception as e:
            logger.error(f"Detection failed: {e}")
            return []
    
    def detect_faces(
        self, 
        image: np.ndarray,
        conf_threshold: float = 0.5
    ) -> List[Tuple[Tuple[int, int, int, int], float]]:
        """
        Detect faces in image using person detection as proxy.
        
        Note: YOLOv8n doesn't have face class, so we detect persons.
        For actual face detection, use RetinaFace or MTCNN via DeepFace.
        
        Args:
            image: Image array in BGR format
            conf_threshold: Confidence threshold
            
        Returns:
            List of (bbox, confidence)
        """
        # For face-specific detection, we'll rely on DeepFace's detector
        # This is a fallback using person detection
        return self.detect(image, conf_threshold=conf_threshold, target_class=0)


# TODO: For production, consider using a dedicated face detector like RetinaFace
# which can be integrated via DeepFace or standalone libraries
