"""
RTSP Stream Processor with BAFS (Background Subtraction) motion detection and FFmpeg.
"""
import asyncio
import cv2
import numpy as np
import ffmpeg
import logging
from typing import Optional, Dict, Any, Callable
from datetime import datetime
from pathlib import Path
from app.config import settings
from app.services.model_server_service import model_server_service
import io
from PIL import Image

logger = logging.getLogger(__name__)


class BAFSMotionDetector:
    """Background subtraction-based motion detector."""
    
    def __init__(self, threshold: int = 500):
        """
        Initialize motion detector.
        
        Args:
            threshold: Minimum number of changed pixels to detect motion
        """
        self.threshold = threshold
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=500,
            varThreshold=16,
            detectShadows=False
        )
        self.frame_count = 0
    
    def detect_motion(self, frame: np.ndarray) -> bool:
        """
        Detect motion in frame using background subtraction (synchronous).
        Should be called in thread pool via detect_motion_async().
        
        Args:
            frame: Input frame (BGR)
        
        Returns:
            True if motion detected, False otherwise
        """
        self.frame_count += 1
        
        # Apply background subtraction
        fg_mask = self.bg_subtractor.apply(frame)
        
        # Count non-zero pixels (foreground)
        motion_pixels = cv2.countNonZero(fg_mask)
        
        # Detect motion if pixels exceed threshold
        has_motion = motion_pixels > self.threshold
        
        # Removed debug logging for motion detection to reduce noise
        
        return has_motion
    
    async def detect_motion_async(self, frame: np.ndarray) -> bool:
        """
        Detect motion asynchronously (runs in thread pool to avoid blocking).
        
        Args:
            frame: Input frame (BGR)
        
        Returns:
            True if motion detected, False otherwise
        """
        # Run blocking OpenCV operations in thread pool
        loop = asyncio.get_event_loop()
        has_motion = await loop.run_in_executor(None, self.detect_motion, frame)
        return has_motion


class RTSPStreamProcessor:
    """Process RTSP streams with motion detection and recognition."""
    
    def __init__(
        self,
        stream_url: str,
        motion_threshold: int = 500,
        keyframe_interval: int = 30,
        process_every_n_frames: int = 5,
        on_recognition: Optional[Callable] = None
    ):
        """
        Initialize RTSP stream processor.
        
        Args:
            stream_url: RTSP stream URL
            motion_threshold: Motion detection threshold
            keyframe_interval: Extract keyframe every N frames
            process_every_n_frames: Process every Nth frame for recognition
            on_recognition: Callback for recognition events
        """
        self.stream_url = stream_url
        self.motion_detector = BAFSMotionDetector(threshold=motion_threshold)
        self.keyframe_interval = keyframe_interval
        self.process_every_n_frames = process_every_n_frames
        self.on_recognition = on_recognition
        
        self.running = False
        self.frame_count = 0
        self.motion_detected_count = 0
        self.recognition_count = 0
        self.processing_recognition = False  # Flag to prevent concurrent recognitions
        
        # FFmpeg process
        self.process = None
        self.width = 640
        self.height = 480
    
    def _start_ffmpeg_stream(self):
        """Start FFmpeg process to capture RTSP stream."""
        try:
            # Use FFmpeg to read RTSP stream
            process = (
                ffmpeg
                .input(self.stream_url, rtsp_transport='tcp')
                .output('pipe:', format='rawvideo', pix_fmt='bgr24', s=f'{self.width}x{self.height}')
                .run_async(pipe_stdout=True, pipe_stderr=True)
            )
            
            logger.info(f"✅ FFmpeg stream started: {self.stream_url}")
            return process
        
        except Exception as e:
            logger.error(f"❌ Failed to start FFmpeg: {e}")
            return None
    
    def _read_frame_sync(self) -> Optional[np.ndarray]:
        """
        Read a frame from FFmpeg stdout synchronously (runs in thread pool).
        
        Returns:
            Frame as numpy array (BGR), or None if error
        """
        if not self.process:
            return None
        
        try:
            # Read raw bytes for one frame
            frame_size = self.width * self.height * 3  # BGR = 3 channels
            in_bytes = self.process.stdout.read(frame_size)
            
            if not in_bytes or len(in_bytes) != frame_size:
                return None
            
            # Convert bytes to numpy array
            frame = np.frombuffer(in_bytes, np.uint8).reshape([self.height, self.width, 3])
            return frame
        
        except Exception as e:
            logger.error(f"❌ Error reading frame: {e}")
            return None
    
    async def _read_frame(self) -> Optional[np.ndarray]:
        """
        Read a frame from FFmpeg stdout (runs in thread pool to avoid blocking).
        
        Returns:
            Frame as numpy array (BGR), or None if error
        """
        # Run blocking read in thread pool
        loop = asyncio.get_event_loop()
        frame = await loop.run_in_executor(None, self._read_frame_sync)
        return frame
    
    async def start(self):
        """Start processing RTSP stream."""
        logger.info(f"🎬 Starting stream processor for: {self.stream_url}")
        
        self.running = True
        self.process = self._start_ffmpeg_stream()
        
        if not self.process:
            logger.error("❌ Failed to start stream processor")
            return
        
        logger.info(f"🎥 Stream processor started: {self.stream_url}")
        logger.info(f"   Motion threshold: {self.motion_detector.threshold}")
        logger.info(f"   Keyframe interval: {self.keyframe_interval}")
        logger.info(f"   Process every N frames: {self.process_every_n_frames}")
        
        try:
            while self.running:
                # Read frame
                frame = await self._read_frame()
                
                if frame is None:
                    logger.warning("⚠️ No frame received, restarting stream...")
                    await asyncio.sleep(1)
                    self.process = self._start_ffmpeg_stream()
                    continue
                
                self.frame_count += 1
                
                # Removed debug frame count logging to reduce noise
                
                # Process every Nth frame to reduce load
                if self.frame_count % self.process_every_n_frames != 0:
                    continue
                
                # Detect motion using BAFS (async to avoid blocking)
                has_motion = await self.motion_detector.detect_motion_async(frame)
                
                if not has_motion:
                    continue
                
                self.motion_detected_count += 1
                # Removed motion count logging to reduce noise
                
                # Extract keyframe every N frames with motion
                if self.motion_detected_count % self.keyframe_interval != 0:
                    continue
                
                logger.info(f"📸 Keyframe extracted for recognition (motion: {self.motion_detected_count})")
                
                # Process frame for recognition in background (non-blocking)
                # Skip if previous recognition still in progress
                if not self.processing_recognition:
                    self.processing_recognition = True
                    asyncio.create_task(self._process_frame_for_recognition(frame.copy()))
                else:
                    logger.debug("⏭️ Skipping frame - previous recognition still in progress")
        
        except Exception as e:
            logger.error(f"❌ Stream processor error: {e}")
        
        finally:
            await self.stop()
    
    def _encode_frame_sync(self, frame: np.ndarray) -> Optional[bytes]:
        """
        Encode frame to JPEG synchronously (runs in thread pool).
        
        Args:
            frame: Input frame (BGR numpy array)
            
        Returns:
            JPEG bytes or None if encoding failed
        """
        is_success, buffer = cv2.imencode(".jpg", frame)
        if not is_success:
            return None
        return buffer.tobytes()
    
    async def _process_frame_for_recognition(self, frame: np.ndarray):
        """
        Process frame for face recognition (runs in background).
        
        Args:
            frame: Input frame (BGR numpy array)
        """
        try:
            logger.debug("🔄 Starting recognition processing...")
            
            # Convert frame to JPEG bytes (run in thread pool to avoid blocking)
            loop = asyncio.get_event_loop()
            frame_bytes = await loop.run_in_executor(None, self._encode_frame_sync, frame)
            
            if frame_bytes is None:
                logger.error("❌ Failed to encode frame")
                return
            
            # Call model server for recognition with timeout
            try:
                result = await asyncio.wait_for(
                    model_server_service.recognize_frame(
                        stream_url=self.stream_url,
                        frame=frame_bytes
                    ),
                    timeout=10.0  # 10 second timeout
                )
            except asyncio.TimeoutError:
                logger.error("❌ Recognition timeout (>10s) - model server may be overloaded")
                return
            
            self.recognition_count += 1
            
            # Log what we received from model server
            detections = result.get("detections", [])
            logger.info(f"📥 Model server response: {len(detections)} detection(s)")
            
            # Process recognition results
            if detections:
                num_detections = len(detections)
                logger.info(f"✅ Recognition: {num_detections} face(s) detected")
                
                # Log each detection for debugging
                for idx, det in enumerate(detections):
                    logger.info(f"   Detection {idx+1}: matched={det.get('matched')}, student_id={det.get('student_id')}, conf={det.get('match_confidence')}")
                
                # Call recognition callback
                if self.on_recognition:
                    await self.on_recognition(result, self.stream_url)
                else:
                    logger.warning("⚠️ No recognition callback set!")
            else:
                logger.info("ℹ️ No faces detected in frame")
            
        except Exception as e:
            logger.error(f"❌ Recognition error: {e}", exc_info=True)
        
        finally:
            # Reset flag to allow next recognition
            self.processing_recognition = False
            logger.debug("✅ Recognition processing completed, ready for next frame")
    
    async def stop(self):
        """Stop stream processor."""
        self.running = False
        
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except Exception as e:
                logger.error(f"❌ Error stopping FFmpeg: {e}")
                self.process.kill()
        
        logger.info(f"🛑 Stream processor stopped: {self.stream_url}")


class StreamManager:
    """Manage multiple RTSP stream processors."""
    
    def __init__(self):
        self.processors: Dict[str, RTSPStreamProcessor] = {}
        self.tasks: Dict[str, asyncio.Task] = {}
    
    async def add_stream(
        self,
        stream_url: str,
        on_recognition: Optional[Callable] = None
    ):
        """
        Add and start processing an RTSP stream.
        
        Args:
            stream_url: RTSP stream URL
            on_recognition: Callback for recognition events
        """
        if stream_url in self.processors:
            logger.warning(f"⚠️ Stream already exists: {stream_url}")
            return
        
        processor = RTSPStreamProcessor(
            stream_url=stream_url,
            motion_threshold=settings.motion_detection_threshold,
            keyframe_interval=settings.keyframe_interval,
            process_every_n_frames=settings.process_every_n_frames,
            on_recognition=on_recognition
        )
        
        self.processors[stream_url] = processor
        
        # Start processor in background task
        task = asyncio.create_task(processor.start())
        self.tasks[stream_url] = task
        
        logger.info(f"✅ Stream added: {stream_url}")
    
    async def remove_stream(self, stream_url: str):
        """
        Remove and stop an RTSP stream.
        
        Args:
            stream_url: RTSP stream URL
        """
        processor = self.processors.get(stream_url)
        if processor:
            await processor.stop()
        
        task = self.tasks.get(stream_url)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        self.processors.pop(stream_url, None)
        self.tasks.pop(stream_url, None)
        
        logger.info(f"✅ Stream removed: {stream_url}")
    
    async def stop_all(self):
        """Stop all stream processors."""
        for stream_url in list(self.processors.keys()):
            await self.remove_stream(stream_url)
        
        logger.info("🛑 All streams stopped")
    
    def get_active_streams(self) -> list:
        """Get list of active stream URLs."""
        return list(self.processors.keys())


# Global stream manager instance
stream_manager = StreamManager()
