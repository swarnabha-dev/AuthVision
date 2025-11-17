"""ByteTrack-like tracker with Kalman filter for stable tracking."""

from __future__ import annotations

import logging
from typing import List, Tuple, Dict, Optional
import numpy as np
from collections import defaultdict
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Track:
    """Represents a single tracked object."""
    
    track_id: int
    bbox: Tuple[int, int, int, int]  # (x1, y1, x2, y2)
    confidence: float
    age: int = 0  # Number of frames since first detection
    hits: int = 1  # Number of successful matches
    time_since_update: int = 0  # Frames since last update
    state: np.ndarray = field(default_factory=lambda: np.zeros(8))  # Kalman state
    covariance: np.ndarray = field(default_factory=lambda: np.eye(8))  # Kalman covariance
    
    # Recognition metadata
    recognized: bool = False
    student_id: Optional[str] = None
    student_name: Optional[str] = None
    match_confidence: Optional[float] = None
    last_recognition_frame: int = 0


class KalmanBoxTracker:
    """
    Kalman filter for tracking bounding boxes.
    State: [x_center, y_center, area, aspect_ratio, vx, vy, va, vr]
    """
    
    def __init__(self, bbox: Tuple[int, int, int, int]):
        """Initialize Kalman filter with initial bounding box."""
        self.kf = self._init_kalman()
        
        # Convert bbox to state [cx, cy, area, aspect_ratio]
        x1, y1, x2, y2 = bbox
        w = x2 - x1
        h = y2 - y1
        cx = x1 + w / 2
        cy = y1 + h / 2
        area = w * h
        aspect_ratio = w / (h + 1e-6)
        
        # Initialize state (reshape to column vector for filterpy)
        self.kf.x[:4] = np.array([[cx], [cy], [area], [aspect_ratio]])
    
    @staticmethod
    def _init_kalman():
        """Initialize Kalman filter matrices."""
        from filterpy.kalman import KalmanFilter
        
        kf = KalmanFilter(dim_x=8, dim_z=4)
        
        # State transition matrix (constant velocity model)
        kf.F = np.eye(8)
        for i in range(4):
            kf.F[i, i + 4] = 1
        
        # Measurement matrix (we observe position, area, aspect ratio)
        kf.H = np.zeros((4, 8))
        for i in range(4):
            kf.H[i, i] = 1
        
        # Measurement noise
        kf.R *= 10
        
        # Process noise
        kf.Q[-1, -1] *= 0.01
        kf.Q[4:, 4:] *= 0.01
        
        # Initial covariance
        kf.P[4:, 4:] *= 1000  # High uncertainty for velocity
        kf.P *= 10
        
        return kf
    
    def predict(self) -> np.ndarray:
        """Predict next state."""
        self.kf.predict()
        return self.kf.x
    
    def update(self, bbox: Tuple[int, int, int, int]) -> None:
        """Update with new measurement."""
        x1, y1, x2, y2 = bbox
        w = x2 - x1
        h = y2 - y1
        cx = x1 + w / 2
        cy = y1 + h / 2
        area = w * h
        aspect_ratio = w / (h + 1e-6)
        
        measurement = np.array([cx, cy, area, aspect_ratio])
        self.kf.update(measurement)
    
    def get_bbox(self) -> Tuple[int, int, int, int]:
        """Get current bounding box from state."""
        cx, cy, area, aspect_ratio = self.kf.x[:4].flatten()
        
        w = np.sqrt(area * aspect_ratio)
        h = area / (w + 1e-6)
        
        x1 = int(cx - w / 2)
        y1 = int(cy - h / 2)
        x2 = int(cx + w / 2)
        y2 = int(cy + h / 2)
        
        return (x1, y1, x2, y2)


class MultiStreamTracker:
    """
    Manages multiple ByteTrack-like trackers, one per stream.
    """
    
    def __init__(
        self,
        max_age: int = 5,  # Reduced from 30 to 5 frames for faster track removal
        min_hits: int = 3,
        iou_threshold: float = 0.3
    ):
        """
        Initialize multi-stream tracker.
        
        Args:
            max_age: Max frames to keep lost tracks (reduced for real-time responsiveness)
            min_hits: Min detections before track is confirmed
            iou_threshold: IOU threshold for matching
        """
        self.max_age = max_age
        self.min_hits = min_hits
        self.iou_threshold = iou_threshold
        
        # Per-stream state
        self.stream_trackers: Dict[str, Dict[int, Track]] = defaultdict(dict)
        self.stream_next_id: Dict[str, int] = defaultdict(lambda: 1)
        self.stream_frame_count: Dict[str, int] = defaultdict(int)
    
    def update(
        self,
        stream_url: str,
        detections: List[Tuple[Tuple[int, int, int, int], float]]
    ) -> List[Track]:
        """
        Update tracker with new detections for a stream.
        
        Args:
            stream_url: Stream identifier
            detections: List of (bbox, confidence)
            
        Returns:
            List of active tracks
        """
        # Increment frame count
        self.stream_frame_count[stream_url] += 1
        current_frame = self.stream_frame_count[stream_url]
        
        tracks = self.stream_trackers[stream_url]
        
        # Predict all existing tracks
        for track in tracks.values():
            if hasattr(track, 'kalman'):
                track.kalman.predict()
                track.bbox = track.kalman.get_bbox()
        
        # Match detections to tracks
        if detections and tracks:
            matched, unmatched_dets, unmatched_tracks = self._match(
                list(tracks.values()),
                detections
            )
            
            # Update matched tracks
            for track_idx, det_idx in matched:
                track_id = list(tracks.keys())[track_idx]
                track = tracks[track_id]
                bbox, conf = detections[det_idx]
                
                # Update Kalman filter
                if hasattr(track, 'kalman'):
                    track.kalman.update(bbox)
                    track.bbox = track.kalman.get_bbox()
                else:
                    track.bbox = bbox
                
                track.confidence = conf
                track.hits += 1
                track.time_since_update = 0
                track.age += 1
            
            # Create new tracks for unmatched detections
            for det_idx in unmatched_dets:
                bbox, conf = detections[det_idx]
                track_id = self.stream_next_id[stream_url]
                self.stream_next_id[stream_url] += 1
                
                track = Track(
                    track_id=track_id,
                    bbox=bbox,
                    confidence=conf
                )
                track.kalman = KalmanBoxTracker(bbox)
                
                tracks[track_id] = track
            
            # Mark unmatched tracks
            for track_idx in unmatched_tracks:
                track_id = list(tracks.keys())[track_idx]
                tracks[track_id].time_since_update += 1
        
        elif detections:
            # No existing tracks, create new ones
            for bbox, conf in detections:
                track_id = self.stream_next_id[stream_url]
                self.stream_next_id[stream_url] += 1
                
                track = Track(
                    track_id=track_id,
                    bbox=bbox,
                    confidence=conf
                )
                track.kalman = KalmanBoxTracker(bbox)
                
                tracks[track_id] = track
        
        else:
            # No detections, increment time_since_update for all
            for track in tracks.values():
                track.time_since_update += 1
        
        # Remove dead tracks
        dead_tracks = []
        for track_id, track in tracks.items():
            if track.time_since_update > self.max_age:
                dead_tracks.append(track_id)
        
        for track_id in dead_tracks:
            del tracks[track_id]
        
        # Return confirmed tracks
        confirmed = [
            track for track in tracks.values()
            if track.hits >= self.min_hits
        ]
        
        return confirmed
    
    def _match(
        self,
        tracks: List[Track],
        detections: List[Tuple[Tuple[int, int, int, int], float]]
    ) -> Tuple[List[Tuple[int, int]], List[int], List[int]]:
        """
        Match detections to tracks using Hungarian algorithm on IOU.
        
        Returns:
            matched: List of (track_idx, detection_idx)
            unmatched_detections: List of detection indices
            unmatched_tracks: List of track indices
        """
        if not tracks or not detections:
            return [], list(range(len(detections))), list(range(len(tracks)))
        
        # Compute IOU matrix
        iou_matrix = np.zeros((len(tracks), len(detections)))
        
        for t, track in enumerate(tracks):
            for d, (bbox, _) in enumerate(detections):
                iou_matrix[t, d] = self._compute_iou(track.bbox, bbox)
        
        # Hungarian matching
        from scipy.optimize import linear_sum_assignment
        track_indices, det_indices = linear_sum_assignment(-iou_matrix)
        
        # Filter low IOU matches
        matched = []
        for t, d in zip(track_indices, det_indices):
            if iou_matrix[t, d] >= self.iou_threshold:
                matched.append((t, d))
        
        unmatched_dets = [d for d in range(len(detections)) if d not in det_indices]
        unmatched_tracks = [t for t in range(len(tracks)) if t not in track_indices]
        
        return matched, unmatched_dets, unmatched_tracks
    
    @staticmethod
    def _compute_iou(bbox1: Tuple[int, int, int, int], 
                     bbox2: Tuple[int, int, int, int]) -> float:
        """Compute IOU between two bounding boxes."""
        x1_1, y1_1, x2_1, y2_1 = bbox1
        x1_2, y1_2, x2_2, y2_2 = bbox2
        
        # Intersection
        x1_i = max(x1_1, x1_2)
        y1_i = max(y1_1, y1_2)
        x2_i = min(x2_1, x2_2)
        y2_i = min(y2_1, y2_2)
        
        if x2_i < x1_i or y2_i < y1_i:
            return 0.0
        
        intersection = (x2_i - x1_i) * (y2_i - y1_i)
        
        # Union
        area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
        area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
        union = area1 + area2 - intersection
        
        if union <= 0:
            return 0.0
        
        return intersection / union
    
    def get_track_by_id(self, stream_url: str, track_id: int) -> Optional[Track]:
        """Get specific track by ID."""
        return self.stream_trackers[stream_url].get(track_id)
    
    def update_track_recognition(
        self,
        stream_url: str,
        track_id: int,
        student_id: str,
        student_name: str,
        confidence: float
    ) -> bool:
        """
        Update recognition info for a track.
        
        Returns:
            True if track was found and updated
        """
        track = self.get_track_by_id(stream_url, track_id)
        if track:
            track.recognized = True
            track.student_id = student_id
            track.student_name = student_name
            track.match_confidence = confidence
            track.last_recognition_frame = self.stream_frame_count[stream_url]
            return True
        return False
