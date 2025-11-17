"""Utility functions for model server."""

from __future__ import annotations

import io
import base64
import numpy as np
from PIL import Image
from typing import Tuple
import cv2


def decode_image_bytes(image_bytes: bytes) -> np.ndarray:
    """
    Decode image bytes to numpy array (BGR format for OpenCV).
    
    Args:
        image_bytes: Raw image bytes
        
    Returns:
        Numpy array in BGR format (H, W, 3)
    """
    image = Image.open(io.BytesIO(image_bytes))
    # Convert to RGB then to BGR for OpenCV
    image_rgb = np.array(image.convert("RGB"))
    image_bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)
    return image_bgr


def encode_image_to_base64(image: np.ndarray, format: str = "JPEG") -> str:
    """
    Encode numpy image array to base64 string.
    
    Args:
        image: Numpy array in BGR format
        format: Image format (JPEG, PNG)
        
    Returns:
        Base64 encoded string
    """
    # Convert BGR to RGB
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    pil_image = Image.fromarray(image_rgb)
    buffer = io.BytesIO()
    pil_image.save(buffer, format=format)
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("utf-8")


def crop_bbox(image: np.ndarray, bbox: Tuple[int, int, int, int]) -> np.ndarray:
    """
    Crop image using bounding box.
    
    Args:
        image: Full image array
        bbox: Bounding box (x1, y1, x2, y2)
        
    Returns:
        Cropped image
    """
    x1, y1, x2, y2 = bbox
    h, w = image.shape[:2]
    
    # Clip to image bounds
    x1 = max(0, min(x1, w - 1))
    y1 = max(0, min(y1, h - 1))
    x2 = max(0, min(x2, w))
    y2 = max(0, min(y2, h))
    
    return image[y1:y2, x1:x2]


def compute_iou(bbox1: Tuple[float, float, float, float], 
                bbox2: Tuple[float, float, float, float]) -> float:
    """
    Compute Intersection over Union between two bounding boxes.
    
    Args:
        bbox1: First bbox (x1, y1, x2, y2)
        bbox2: Second bbox (x1, y1, x2, y2)
        
    Returns:
        IOU value [0, 1]
    """
    x1_1, y1_1, x2_1, y2_1 = bbox1
    x1_2, y1_2, x2_2, y2_2 = bbox2
    
    # Compute intersection
    x1_i = max(x1_1, x1_2)
    y1_i = max(y1_1, y1_2)
    x2_i = min(x2_1, x2_2)
    y2_i = min(y2_1, y2_2)
    
    if x2_i < x1_i or y2_i < y1_i:
        return 0.0
    
    intersection = (x2_i - x1_i) * (y2_i - y1_i)
    
    # Compute union
    area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
    area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
    union = area1 + area2 - intersection
    
    if union <= 0:
        return 0.0
    
    return intersection / union


def normalize_bbox(bbox: Tuple[int, int, int, int], 
                   img_width: int, 
                   img_height: int) -> Tuple[float, float, float, float]:
    """
    Normalize bounding box to [0, 1] range.
    
    Args:
        bbox: Bounding box in pixels (x1, y1, x2, y2)
        img_width: Image width
        img_height: Image height
        
    Returns:
        Normalized bbox (x1, y1, x2, y2)
    """
    x1, y1, x2, y2 = bbox
    return (
        x1 / img_width,
        y1 / img_height,
        x2 / img_width,
        y2 / img_height,
    )


def denormalize_bbox(bbox: Tuple[float, float, float, float],
                     img_width: int,
                     img_height: int) -> Tuple[int, int, int, int]:
    """
    Denormalize bounding box from [0, 1] to pixel coordinates.
    
    Args:
        bbox: Normalized bbox (x1, y1, x2, y2)
        img_width: Image width
        img_height: Image height
        
    Returns:
        Bbox in pixels (x1, y1, x2, y2)
    """
    x1, y1, x2, y2 = bbox
    return (
        int(x1 * img_width),
        int(y1 * img_height),
        int(x2 * img_width),
        int(y2 * img_height),
    )


def serialize_embedding(embedding: np.ndarray) -> bytes:
    """
    Serialize numpy embedding to bytes.
    
    Args:
        embedding: Numpy array (typically float32)
        
    Returns:
        Serialized bytes
    """
    return embedding.astype(np.float32).tobytes()


def deserialize_embedding(embedding_bytes: bytes, dim: int) -> np.ndarray:
    """
    Deserialize embedding bytes to numpy array.
    
    Args:
        embedding_bytes: Serialized embedding
        dim: Embedding dimension
        
    Returns:
        Numpy array of shape (dim,)
    """
    return np.frombuffer(embedding_bytes, dtype=np.float32).reshape(dim)
