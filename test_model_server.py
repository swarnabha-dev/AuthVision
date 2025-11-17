"""
Model Server Testing Script - Standalone Testing

This script tests the model server (authentication, enrollment, and recognition)
without needing the main backend.

Features:
- User authentication (login to get JWT token)
- Enroll students with photos
- Test recognition with RTSP stream frames
- Easy configuration section at top

Requirements:
- Model server running on http://localhost:8001
- RTSP camera accessible
- OpenCV for frame capture (pip install opencv-python)
"""

import asyncio
import base64
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional
import httpx
import cv2
from datetime import datetime

# ============================================================================
# 📝 CONFIGURATION - EDIT THIS SECTION
# ============================================================================

# Model Server Settings
MODEL_SERVER_URL = "http://localhost:8001"

# Authentication Credentials (create user first via auth endpoints)
USERNAME = "test_user"
PASSWORD = "test_password123"  # Min 8 characters required
EMAIL = "test_user@example.com"  # Required for registration

# RTSP Stream URL
RTSP_STREAM = "rtsp://admin:admin123@192.168.128.10:554/avstream/channel=0/stream=1.sdp"

# Student Data for Enrollment
STUDENTS_TO_ENROLL = [
    {
        "student_id": "202200248",
        "photos": {
            "view_1": r"C:\Users\swarn\OneDrive - 3602sv\Original Projects\5G LAB CCTV Project\Face Recognition v5\202200248_Swarnabha\202200248_Swarnabha_CSE_20250911_171529.jpg",
            "view_2": r"C:\Users\swarn\OneDrive - 3602sv\Original Projects\5G LAB CCTV Project\Face Recognition v5\202200248_Swarnabha\202200248_Swarnabha_CSE_20250911_171549.jpg",
            "view_3": r"C:\Users\swarn\OneDrive - 3602sv\Original Projects\5G LAB CCTV Project\Face Recognition v5\202200248_Swarnabha\202200248_Swarnabha_CSE_20250911_171603.jpg",
            "view_4": r"C:\Users\swarn\OneDrive - 3602sv\Original Projects\5G LAB CCTV Project\Face Recognition v5\202200248_Swarnabha\202200248_Swarnabha_CSE_20250911_171621.jpg",
            "view_5": r"C:\Users\swarn\OneDrive - 3602sv\Original Projects\5G LAB CCTV Project\Face Recognition v5\202200248_Swarnabha\202200248_Swarnabha_CSE_20250911_171637.jpg"
        }
    },
    # Add more students here:
    # {
    #     "student_id": "202200249",
    #     "photos": {
    #         "view_1": "path/to/another_student_front.jpg",
    #         "view_2": "path/to/another_student_left.jpg",
    #         "view_3": "path/to/another_student_right.jpg"
    #     }
    # }
]

# Recognition Test Settings
RECOGNITION_DURATION_SECONDS = 30  # How long to test recognition
FRAME_INTERVAL = 1.0  # Capture frame every N seconds

# ============================================================================
# 🔧 HELPER FUNCTIONS
# ============================================================================

class Colors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_header(text: str):
    """Print section header."""
    print(f"\n{'=' * 80}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text}{Colors.ENDC}")
    print('=' * 80)


def print_success(text: str):
    """Print success message."""
    print(f"{Colors.OKGREEN}✅ {text}{Colors.ENDC}")


def print_error(text: str):
    """Print error message."""
    print(f"{Colors.FAIL}❌ {text}{Colors.ENDC}")


def print_info(text: str):
    """Print info message."""
    print(f"{Colors.OKCYAN}ℹ️  {text}{Colors.ENDC}")


def print_warning(text: str):
    """Print warning message."""
    print(f"{Colors.WARNING}⚠️  {text}{Colors.ENDC}")


def encode_image_to_base64(image_path: str) -> str:
    """Encode image file to base64 string."""
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')


def encode_frame_to_base64(frame) -> str:
    """Encode OpenCV frame to base64 string."""
    _, buffer = cv2.imencode('.jpg', frame)
    return base64.b64encode(buffer).decode('utf-8')


# ============================================================================
# 🔐 AUTHENTICATION
# ============================================================================

class ModelServerClient:
    """Client for interacting with model server."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.access_token: Optional[str] = None
        self.client = httpx.AsyncClient(timeout=60.0)
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with auth token."""
        headers = {"Content-Type": "application/json"}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers
    
    async def register_user(self, username: str, password: str, email: str) -> bool:
        """Register a new user (only works if user doesn't exist)."""
        try:
            response = await self.client.post(
                f"{self.base_url}/v1/auth/register",
                json={
                    "username": username,
                    "password": password,
                    "email": email
                }
            )
            
            if response.status_code == 201:
                data = response.json()
                print_success(f"User registered: {username}")
                return True
            elif response.status_code == 400:
                print_info("User already exists (this is fine)")
                return True
            else:
                print_error(f"Registration failed: {response.text}")
                return False
        except Exception as e:
            print_error(f"Registration error: {e}")
            return False
    
    async def login(self, username: str, password: str) -> bool:
        """Login and get JWT access token."""
        try:
            # JSON body for login endpoint
            response = await self.client.post(
                f"{self.base_url}/v1/auth/login",
                json={
                    "username": username,
                    "password": password
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data["access_token"]
                print_success(f"Logged in as: {username}")
                print_info(f"Token type: {data['token_type']}")
                print_info(f"Expires in: {data['expires_in']} seconds")
                return True
            else:
                print_error(f"Login failed: {response.text}")
                return False
        except Exception as e:
            print_error(f"Login error: {e}")
            return False
    
    async def check_health(self) -> bool:
        """Check if model server is healthy."""
        try:
            response = await self.client.get(f"{self.base_url}/v1/health")
            if response.status_code == 200:
                data = response.json()
                print_success(f"Model server healthy: {data['status']}")
                return True
            else:
                print_error(f"Health check failed: {response.status_code}")
                return False
        except Exception as e:
            print_error(f"Health check error: {e}")
            return False
    
    async def get_model_info(self) -> Optional[Dict]:
        """Get model information."""
        try:
            response = await self.client.get(
                f"{self.base_url}/v1/models",
                headers=self._get_headers()
            )
            
            if response.status_code == 200:
                data = response.json()
                print_success("Model info retrieved")
                return data
            else:
                print_error(f"Failed to get model info: {response.status_code}")
                return None
        except Exception as e:
            print_error(f"Model info error: {e}")
            return None
    
    async def enroll_student(self, student_id: str, images: Dict[str, str]) -> bool:
        """
        Enroll student with multi-view images.
        
        Args:
            student_id: Student ID
            images: Dict of {view_name: base64_image}
        """
        try:
            payload = {
                "student_id": student_id,
                "images": images,
                "options": {
                    "model_name": "ArcFace",
                    "detector_backend": "yolov8",
                    "align": True,
                    "anti_spoof": False,  # Disabled in current config
                    "distance_metric": "cosine"
                }
            }
            
            print_info(f"Enrolling student {student_id} with {len(images)} views...")
            
            response = await self.client.post(
                f"{self.base_url}/v1/enroll_embeddings",
                json=payload,
                headers=self._get_headers()
            )
            
            if response.status_code == 200:
                data = response.json()
                print_success(f"Student {student_id} enrolled successfully")
                print_info(f"  Model: {data.get('model_version', 'N/A')}")
                print_info(f"  Detector: {data.get('detector_backend', 'N/A')}")
                print_info(f"  Status: {data.get('status', 'N/A')}")
                
                # Show embedding details
                for view, result in data.get("embeddings", {}).items():
                    if result.get("success"):
                        is_live = result.get('is_live', 'N/A')
                        embedding_dim = result.get('embedding_dim', 'N/A')
                        print(f"  ✓ {view}: {embedding_dim}-D embedding, Live: {is_live}")
                    else:
                        print(f"  ✗ {view}: Failed - {result.get('error', 'Unknown error')}")
                
                return True
            else:
                print_error(f"Enrollment failed: {response.status_code}")
                print(response.text)
                return False
                
        except Exception as e:
            print_error(f"Enrollment error: {e}")
            return False
    
    async def recognize_frame(self, frame_base64: str, stream_url: str = "test_stream") -> Optional[Dict]:
        """
        Recognize faces in a frame.
        
        Args:
            frame_base64: Base64 encoded frame (JPEG)
            stream_url: RTSP stream identifier
        
        Returns:
            Recognition results or None
        """
        try:
            payload = {
                "stream_url": stream_url,
                "frame_base64": frame_base64,
                "options": {
                    "align": True,
                    "anti_spoof": False,  # Disabled in current config
                    "distance_metric": "cosine",
                    "min_confidence": 0.35
                }
            }
            
            response = await self.client.post(
                f"{self.base_url}/v1/recognize_frame",
                json=payload,
                headers=self._get_headers(),
                timeout=30.0
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print_error(f"Recognition failed: {response.status_code}")
                return None
                
        except Exception as e:
            print_error(f"Recognition error: {e}")
            return None


# ============================================================================
# 📸 RTSP FRAME CAPTURE
# ============================================================================

class RTSPCapture:
    """RTSP stream frame capture."""
    
    def __init__(self, stream_url: str):
        self.stream_url = stream_url
        self.cap: Optional[cv2.VideoCapture] = None
    
    def connect(self) -> bool:
        """Connect to RTSP stream."""
        try:
            print_info(f"Connecting to RTSP stream: {self.stream_url}")
            self.cap = cv2.VideoCapture(self.stream_url)
            
            if not self.cap.isOpened():
                print_error("Failed to open RTSP stream")
                return False
            
            # Test read
            ret, frame = self.cap.read()
            if not ret:
                print_error("Failed to read frame from RTSP stream")
                return False
            
            print_success(f"Connected to RTSP stream (Frame: {frame.shape[1]}x{frame.shape[0]})")
            return True
            
        except Exception as e:
            print_error(f"RTSP connection error: {e}")
            return False
    
    def get_frame(self):
        """Get current frame from stream."""
        if not self.cap or not self.cap.isOpened():
            return None
        
        ret, frame = self.cap.read()
        if ret:
            return frame
        return None
    
    def release(self):
        """Release stream."""
        if self.cap:
            self.cap.release()
            print_info("RTSP stream released")


# ============================================================================
# 🧪 TEST FUNCTIONS
# ============================================================================

async def test_enrollment(client: ModelServerClient, students: List[Dict]) -> bool:
    """Test student enrollment."""
    print_header("📝 ENROLLMENT TEST")
    
    success_count = 0
    for student in students:
        student_id = student["student_id"]
        photo_paths = student["photos"]
        
        print(f"\n📸 Processing student: {student_id}")
        
        # Check if all photo files exist
        missing_files = []
        for view, path in photo_paths.items():
            if not Path(path).exists():
                missing_files.append(f"{view}: {path}")
        
        if missing_files:
            print_error(f"Missing photo files for {student_id}:")
            for mf in missing_files:
                print(f"  - {mf}")
            continue
        
        # Encode images to base64
        try:
            images_base64 = {}
            for view, path in photo_paths.items():
                print_info(f"Encoding {view}: {path}")
                images_base64[view] = encode_image_to_base64(path)
            
            # Enroll student
            if await client.enroll_student(student_id, images_base64):
                success_count += 1
            
        except Exception as e:
            print_error(f"Failed to process {student_id}: {e}")
    
    print(f"\n📊 Enrollment Summary: {success_count}/{len(students)} successful")
    return success_count > 0


async def test_recognition(client: ModelServerClient, rtsp_url: str, duration: int) -> bool:
    """Test face recognition with RTSP stream."""
    print_header("🎯 RECOGNITION TEST")
    
    # Connect to RTSP stream
    capture = RTSPCapture(rtsp_url)
    if not capture.connect():
        return False
    
    print_info(f"Testing recognition for {duration} seconds...")
    print_info(f"Capturing frames every {FRAME_INTERVAL} seconds")
    print_info("Stand in front of the camera!")
    print()
    
    start_time = datetime.now()
    frame_count = 0
    recognition_count = 0
    last_capture_time = 0
    
    try:
        while (datetime.now() - start_time).total_seconds() < duration:
            current_time = (datetime.now() - start_time).total_seconds()
            
            # Capture frame at intervals
            if current_time - last_capture_time >= FRAME_INTERVAL:
                frame = capture.get_frame()
                
                if frame is None:
                    print_warning("Failed to get frame from stream")
                    await asyncio.sleep(0.1)
                    continue
                
                frame_count += 1
                last_capture_time = current_time
                
                print(f"\n⏱️  [{int(current_time)}s] Frame #{frame_count}")
                
                # Encode frame to base64
                frame_base64 = encode_frame_to_base64(frame)
                
                # Recognize
                result = await client.recognize_frame(frame_base64, rtsp_url)
                
                if result:
                    detections = result.get("detections", [])
                    
                    if detections:
                        for i, det in enumerate(detections, 1):
                            recognition_count += 1
                            
                            if det.get("matched"):
                                match_conf = det.get('match_confidence')
                                conf_str = f"{match_conf:.2%}" if match_conf is not None else "N/A"
                                print_success(
                                    f"  Face #{i}: MATCHED - Student {det['student_id']} "
                                    f"(Confidence: {conf_str}, "
                                    f"View: {det.get('matched_view', 'N/A')})"
                                )
                            else:
                                match_conf = det.get('match_confidence')
                                conf_str = f"{match_conf:.2%}" if match_conf is not None else "N/A"
                                print_warning(
                                    f"  Face #{i}: UNKNOWN (Detection confidence: {det.get('confidence', 0):.2%}, "
                                    f"Match confidence: {conf_str})"
                                )
                    else:
                        print_info("  No faces detected")
                else:
                    print_warning("  Recognition request failed")
            
            await asyncio.sleep(0.1)
    
    except KeyboardInterrupt:
        print_info("\nRecognition test interrupted by user")
    finally:
        capture.release()
    
    print(f"\n📊 Recognition Summary:")
    print(f"  Frames processed: {frame_count}")
    print(f"  Faces detected: {recognition_count}")
    
    return frame_count > 0


# ============================================================================
# 🚀 MAIN TEST RUNNER
# ============================================================================

async def main():
    """Main test runner."""
    print_header("🧪 MODEL SERVER TEST SCRIPT")
    print_info(f"Model Server: {MODEL_SERVER_URL}")
    print_info(f"RTSP Stream: {RTSP_STREAM}")
    print()
    
    client = ModelServerClient(MODEL_SERVER_URL)
    
    try:
        # Step 1: Check server health
        print_header("🏥 SERVER HEALTH CHECK")
        if not await client.check_health():
            print_error("Model server is not healthy. Please start the server first.")
            return
        
        # Step 2: Get model info (without auth - should work)
        print_header("ℹ️  MODEL INFORMATION")
        model_info = await client.get_model_info()
        if model_info:
            print(f"  Pipeline: {model_info.get('pipeline', 'N/A')}")
            print(f"  Recognizer: {model_info.get('recognizer', 'N/A')}")
            print(f"  Detector: {model_info.get('detector', 'N/A')}")
        
        # Step 3: Register user (if needed)
        print_header("👤 USER REGISTRATION")
        await client.register_user(USERNAME, PASSWORD, EMAIL)
        
        # Step 4: Login
        print_header("🔐 AUTHENTICATION")
        if not await client.login(USERNAME, PASSWORD):
            print_error("Failed to authenticate. Cannot continue.")
            return
        
        # Step 5: Test enrollment
        if STUDENTS_TO_ENROLL:
            if not await test_enrollment(client, STUDENTS_TO_ENROLL):
                print_warning("Enrollment had errors, but continuing to recognition test...")
        else:
            print_warning("No students configured for enrollment. Skipping enrollment test.")
        
        # Step 6: Test recognition
        input("\nPress Enter to start recognition test (or Ctrl+C to skip)...")
        await test_recognition(client, RTSP_STREAM, RECOGNITION_DURATION_SECONDS)
        
        print_header("✅ ALL TESTS COMPLETED")
        
    except KeyboardInterrupt:
        print_info("\nTests interrupted by user")
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print_info("\nExiting...")
