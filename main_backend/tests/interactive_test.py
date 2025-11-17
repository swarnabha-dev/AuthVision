"""
Interactive Menu-Driven API Test Script
Test all backend APIs with your own data.
"""
import asyncio
import httpx
import base64
import json
from pathlib import Path
from datetime import datetime
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import config to get DB path
from app.config import settings

# ============================================================================
# GLOBAL CONFIGURATION - EDIT THESE VALUES
# ============================================================================

# Backend URL
BASE_URL = "http://localhost:8000/api/v1/backend"
WS_URL = "ws://localhost:8000/api/v1/backend/ws/events"

# Model Server URL (for direct testing)
MODEL_SERVER_URL = "http://localhost:8001"

# User credentials for authentication
USER_CREDENTIALS = {
    "username": "new1_admin",
    "password": "TestPassword123!",
    "email": "a1dminnew@test.com",
    "full_name": "Test Administrator",
    "role": "admin"  # admin or operator
}

# Student data for testing
STUDENT_DATA = {
    "student_id": "202200248",  # Must be exactly 9 digits
    "first_name": "Swarnabha",
    "last_name": "Halder",
    "email": "john.smith@student.com",
    "phone": "+1234567890",
    "metadata": {
        "department": "Computer Science",
        "year": "2022",
        "section": "B",
        "batch": "2022-2026"
    }
}

# Photo paths for enrollment (relative or absolute paths)
PHOTO_PATHS = {
    "front": r"C:\Users\swarn\OneDrive - 3602sv\Original Projects\5G LAB CCTV Project\Face Recognition v5\202200248_Swarnabha\202200248_Swarnabha_CSE_20250911_171529.jpg",
    "left": r"C:\Users\swarn\OneDrive - 3602sv\Original Projects\5G LAB CCTV Project\Face Recognition v5\202200248_Swarnabha\202200248_Swarnabha_CSE_20250911_171549.jpg",
    "right": r"C:\Users\swarn\OneDrive - 3602sv\Original Projects\5G LAB CCTV Project\Face Recognition v5\202200248_Swarnabha\202200248_Swarnabha_CSE_20250911_171603.jpg",
    "angled_left": r"C:\Users\swarn\OneDrive - 3602sv\Original Projects\5G LAB CCTV Project\Face Recognition v5\202200248_Swarnabha\202200248_Swarnabha_CSE_20250911_171621.jpg",
    "angled_right": r"C:\Users\swarn\OneDrive - 3602sv\Original Projects\5G LAB CCTV Project\Face Recognition v5\202200248_Swarnabha\202200248_Swarnabha_CSE_20250911_171637.jpg"
}

# ============================================================================
# DO NOT EDIT BELOW THIS LINE (unless you know what you're doing)
# ============================================================================

# Global variables for session management
access_token = None
refresh_token = None
client = None

# Model Server authentication
model_server_access_token = None
model_server_refresh_token = None


def print_header(title):
    """Print formatted header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_response(response, show_full=False):
    """Print formatted response."""
    print(f"\n📡 Status Code: {response.status_code}")
    
    try:
        data = response.json()
        if show_full:
            print(f"📄 Response:\n{json.dumps(data, indent=2)}")
        else:
            # Truncate long responses
            response_str = json.dumps(data, indent=2)
            if len(response_str) > 500:
                print(f"📄 Response (truncated):\n{response_str[:500]}...")
                print(f"\n💡 Use 'Show full response' option to see complete data")
            else:
                print(f"📄 Response:\n{response_str}")
    except:
        print(f"📄 Response: {response.text[:200]}")


def load_image_base64(image_path: str) -> str:
    """Load image file and convert to base64."""
    try:
        with open(image_path, 'rb') as f:
            img_bytes = f.read()
        return base64.b64encode(img_bytes).decode('utf-8')
    except FileNotFoundError:
        print(f"❌ Error: Image file not found: {image_path}")
        return None
    except Exception as e:
        print(f"❌ Error loading image: {e}")
        return None


async def get_client():
    """Get or create HTTP client."""
    global client
    if client is None:
        client = httpx.AsyncClient(timeout=120.0)
    return client


# ============================================================================
# API TEST FUNCTIONS
# ============================================================================

async def test_health_check():
    """Test health check endpoint."""
    print_header("Health Check")
    
    try:
        client = await get_client()
        response = await client.get(f"{BASE_URL}/health")
        print_response(response)
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ System Status: {data.get('status')}")
            print(f"   Database: {data.get('database')}")
            print(f"   Model Server: {data.get('model_server')}")
            print(f"   Active Streams: {data.get('active_streams')}")
            print(f"   Total Students: {data.get('total_students')}")
        
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def test_register():
    """Test user registration."""
    print_header("User Registration")
    
    print(f"📝 Registering user: {USER_CREDENTIALS['username']}")
    
    try:
        client = await get_client()
        response = await client.post(
            f"{BASE_URL}/auth/register",
            json=USER_CREDENTIALS
        )
        print_response(response)
        
        if response.status_code in [201, 409]:
            print(f"\n✅ User ready (Status: {response.status_code})")
            if response.status_code == 409:
                print("   (User already exists)")
            return True
        else:
            print(f"\n❌ Registration failed")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def test_login():
    """Test user login and get tokens."""
    global access_token, refresh_token
    
    print_header("User Login")
    
    print(f"🔐 Logging in as: {USER_CREDENTIALS['username']}")
    
    try:
        client = await get_client()
        response = await client.post(
            f"{BASE_URL}/auth/login",
            json={
                "username": USER_CREDENTIALS["username"],
                "password": USER_CREDENTIALS["password"]
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            access_token = data["access_token"]
            refresh_token = data["refresh_token"]
            
            print(f"\n✅ Login successful!")
            print(f"   Access Token: {access_token[:30]}...")
            print(f"   Refresh Token: {refresh_token[:30]}...")
            print(f"   User ID: {data['user']['id']}")
            print(f"   Role: {data['user']['role']}")
            return True
        else:
            print_response(response)
            print(f"\n❌ Login failed")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def test_refresh_token():
    """Test token refresh."""
    global access_token, refresh_token
    
    print_header("Token Refresh")
    
    if not refresh_token:
        print("❌ No refresh token available. Please login first.")
        return False
    
    try:
        client = await get_client()
        response = await client.post(
            f"{BASE_URL}/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        
        if response.status_code == 200:
            data = response.json()
            access_token = data["access_token"]
            print(f"\n✅ Token refreshed!")
            print(f"   New Access Token: {access_token[:30]}...")
            return True
        else:
            print_response(response)
            print(f"\n❌ Token refresh failed")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def test_create_student():
    """Test student creation."""
    print_header("Create Student")
    
    if not access_token:
        print("❌ Not authenticated. Please login first.")
        return False
    
    print(f"👤 Creating student: {STUDENT_DATA['student_id']}")
    print(f"   Name: {STUDENT_DATA['first_name']} {STUDENT_DATA['last_name']}")
    
    try:
        client = await get_client()
        response = await client.post(
            f"{BASE_URL}/students",
            json=STUDENT_DATA,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        print_response(response)
        
        if response.status_code in [201, 409]:
            print(f"\n✅ Student ready (Status: {response.status_code})")
            if response.status_code == 409:
                print("   (Student already exists)")
            return True
        else:
            print(f"\n❌ Student creation failed")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def test_enroll_student():
    """Test student enrollment with face photos."""
    print_header("Enroll Student")
    
    if not access_token:
        print("❌ Not authenticated. Please login first.")
        return False
    
    print(f"📸 Enrolling student: {STUDENT_DATA['student_id']}")
    print(f"   Loading photos from:")
    
    # Load all images
    images = {}
    for view, path in PHOTO_PATHS.items():
        print(f"   - {view}: {path}")
        img_base64 = load_image_base64(path)
        if img_base64 is None:
            print(f"\n❌ Failed to load image: {path}")
            print(f"💡 Make sure photo files exist at the specified paths")
            return False
        images[view] = img_base64
    
    print(f"\n✅ All {len(images)} images loaded")
    print(f"🔄 Sending to model server (this may take 30-60 seconds)...")
    
    try:
        client = await get_client()
        response = await client.post(
            f"{BASE_URL}/students/{STUDENT_DATA['student_id']}/enroll",
            json={"images": images},
            headers={"Authorization": f"Bearer {access_token}"}
        )
        print_response(response, show_full=True)
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ Enrollment successful!")
            print(f"   Student ID: {data['student_id']}")
            print(f"   Status: {data['status']}")
            print(f"   Photo Record ID: {data['photo_record_id']}")
            print(f"   Model Server Status: {data.get('model_server_status', 'N/A')}")
            print(f"   Model Version: {data.get('model_version', 'N/A')}")
            print(f"   Views Enrolled: {data.get('views_enrolled', 0)}")
            return True
        else:
            print(f"\n❌ Enrollment failed")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def test_get_student():
    """Test get student details."""
    print_header("Get Student Details")
    
    if not access_token:
        print("❌ Not authenticated. Please login first.")
        return False
    
    student_id = input(f"Enter student ID (default: {STUDENT_DATA['student_id']}): ").strip()
    if not student_id:
        student_id = STUDENT_DATA['student_id']
    
    print(f"\n🔍 Fetching student: {student_id}")
    
    try:
        client = await get_client()
        response = await client.get(
            f"{BASE_URL}/students/{student_id}",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        print_response(response, show_full=True)
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ Student found:")
            print(f"   ID: {data['student_id']}")
            print(f"   Name: {data['first_name']} {data['last_name']}")
            print(f"   Email: {data['email']}")
            print(f"   Phone: {data.get('phone', 'N/A')}")
            print(f"   Model Server Enrolled: {'Yes' if data.get('model_server_enrolled') else 'No'}")
            
            if data.get('photos'):
                print(f"   Photos: Available")
            return True
        else:
            print(f"\n❌ Student not found")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def test_list_students():
    """Test list all students."""
    print_header("List All Students")
    
    if not access_token:
        print("❌ Not authenticated. Please login first.")
        return False
    
    print(f"📋 Fetching all students...")
    
    try:
        client = await get_client()
        response = await client.get(
            f"{BASE_URL}/students",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        print_response(response, show_full=True)
        
        if response.status_code == 200:
            data = response.json()
            students = data.get('students', [])
            print(f"\n✅ Found {len(students)} student(s):")
            
            for student in students:
                print(f"\n   📌 {student['student_id']}")
                print(f"      Name: {student['first_name']} {student['last_name']}")
                print(f"      Email: {student['email']}")
            return True
        else:
            print(f"\n❌ Failed to fetch students")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def test_logout():
    """Test user logout."""
    global access_token, refresh_token
    
    print_header("User Logout")
    
    if not access_token:
        print("❌ Not authenticated. Nothing to logout.")
        return False
    
    try:
        client = await get_client()
        response = await client.post(
            f"{BASE_URL}/auth/logout",
            json={"refresh_token": refresh_token},
            headers={"Authorization": f"Bearer {access_token}"}
        )
        print_response(response)
        
        if response.status_code == 200:
            print(f"\n✅ Logged out successfully!")
            access_token = None
            refresh_token = None
            return True
        else:
            print(f"\n❌ Logout failed")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def test_websocket():
    """Test WebSocket connection (shows first 5 messages)."""
    print_header("WebSocket Test")
    
    print(f"🔌 Connecting to: {WS_URL}")
    print(f"📡 Will show first 5 messages, then disconnect")
    print(f"💡 Press Ctrl+C to stop early\n")
    
    try:
        import websockets
        
        async with websockets.connect(WS_URL) as websocket:
            print("✅ Connected to WebSocket!\n")
            
            for i in range(5):
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    event = json.loads(message)
                    
                    print(f"📨 Message {i+1}:")
                    print(f"   {json.dumps(event, indent=2)}\n")
                except asyncio.TimeoutError:
                    print(f"⏱️  No message received in 10 seconds")
                    break
            
            print("✅ WebSocket test completed")
            return True
    except ImportError:
        print("❌ Error: 'websockets' library not installed")
        print("💡 Install with: pip install websockets")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def test_recognition_monitor():
    """Monitor real-time face recognition from RTSP stream."""
    print_header("Face Recognition Monitor")
    
    print("🎥 REAL-TIME FACE RECOGNITION MONITOR")
    print("=" * 70)
    print("\n📹 Backend is processing RTSP stream frames")
    print("🔍 Checking enrolled students against detected faces")
    print("📡 Listening for recognition events via WebSocket")
    print("\n💡 Instructions:")
    print("   1. Make sure RTSP stream is active (check backend logs)")
    print("   2. Enrolled students should stand in front of camera")
    print("   3. Recognition events will appear here in real-time")
    print("   4. Press Ctrl+C to stop monitoring\n")
    
    duration = input("Monitor duration in seconds (default: 60, 0=unlimited): ").strip()
    if not duration:
        duration = 60
    else:
        try:
            duration = int(duration)
        except:
            duration = 60
    
    print(f"\n🔄 Starting monitor for {duration if duration > 0 else 'unlimited'} seconds...")
    print("=" * 70)
    print()
    
    try:
        import websockets
        from datetime import datetime
        
        recognition_count = 0
        start_time = datetime.now()
        
        async with websockets.connect(WS_URL) as websocket:
            print("✅ Connected to backend WebSocket")
            print("⏳ Waiting for recognition events...\n")
            
            while True:
                try:
                    # Check duration
                    if duration > 0:
                        elapsed = (datetime.now() - start_time).total_seconds()
                        if elapsed >= duration:
                            print(f"\n⏱️  Monitoring duration reached ({duration}s)")
                            break
                    
                    # Wait for message with timeout
                    timeout_duration = min(10.0, duration) if duration > 0 else 10.0
                    message = await asyncio.wait_for(
                        websocket.recv(), 
                        timeout=timeout_duration
                    )
                    event = json.loads(message)
                    
                    # Filter for recognition events
                    if event.get("type") == "recognition_event":
                        recognition_count += 1
                        
                        print("=" * 70)
                        print(f"🎯 RECOGNITION EVENT #{recognition_count}")
                        print("=" * 70)
                        
                        # Extract recognition data
                        timestamp = event.get("timestamp", "N/A")
                        stream_url = event.get("stream_url", "N/A")
                        detections = event.get("detections", [])
                        
                        print(f"⏰ Time: {timestamp}")
                        print(f"📹 Stream: {stream_url}")
                        print(f"👥 Detections: {len(detections)} face(s) found\n")
                        
                        for idx, detection in enumerate(detections, 1):
                            student_id = detection.get("student_id")
                            student_name = detection.get("student_name", "Unknown")
                            confidence = detection.get("match_confidence", 0)
                            bbox = detection.get("bbox", [])
                            
                            print(f"   👤 Detection #{idx}:")
                            
                            if student_id:
                                print(f"      ✅ RECOGNIZED!")
                                print(f"      Student ID: {student_id}")
                                print(f"      Name: {student_name}")
                                print(f"      Confidence: {confidence:.2%}")
                            else:
                                print(f"      ❓ UNKNOWN FACE")
                                print(f"      (No match in database)")
                            
                            if bbox and len(bbox) == 4:
                                x1, y1, x2, y2 = bbox
                                print(f"      Location: [{x1}, {y1}, {x2}, {y2}]")
                            print()
                        
                        print("=" * 70)
                        print()
                    
                    elif event.get("type") == "motion_detected":
                        # Show motion detection events
                        print(f"🔴 Motion detected: {event.get('pixels_changed', 0)} pixels changed")
                    
                    elif event.get("type") == "connection":
                        # Connection status
                        print(f"🔌 WebSocket: {event.get('status', 'unknown')}")
                
                except asyncio.TimeoutError:
                    # No message in timeout period
                    elapsed = (datetime.now() - start_time).total_seconds()
                    print(f"⏳ No events... (monitoring for {int(elapsed)}s, "
                          f"{recognition_count} recognition(s) so far)")
                    
                    if duration > 0 and elapsed >= duration:
                        break
                
                except KeyboardInterrupt:
                    print("\n\n⏹️  Monitoring stopped by user")
                    break
            
            # Summary
            elapsed_time = (datetime.now() - start_time).total_seconds()
            print("\n" + "=" * 70)
            print("📊 MONITORING SUMMARY")
            print("=" * 70)
            print(f"⏱️  Duration: {int(elapsed_time)} seconds")
            print(f"🎯 Recognitions: {recognition_count} event(s)")
            print(f"📈 Rate: {recognition_count/elapsed_time*60:.1f} events/minute" 
                  if elapsed_time > 0 else "N/A")
            print("=" * 70)
            
            return True
    
    except ImportError:
        print("❌ Error: 'websockets' library not installed")
        print("💡 Install with: pip install websockets")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def test_view_attendance_records():
    """View attendance records from database."""
    print_header("View Attendance Records")
    
    print("📊 Fetching attendance records from database...")
    print("💡 This shows recognition events stored in the database\n")
    
    # Ask for filters
    print("Filters (press Enter to skip):")
    student_id = input("  Student ID (9 digits, or blank for all): ").strip()
    limit = input("  Number of records (default: 10): ").strip()
    
    if not limit:
        limit = 10
    else:
        try:
            limit = int(limit)
        except:
            limit = 10
    
    try:
        # Import sqlite3 to query database directly
        import sqlite3
        
        # Get database path from config
        db_path = settings.db_path
        
        if not db_path.exists():
            print(f"\n❌ Database not found at: {db_path}")
            print("💡 Make sure backend has been started at least once")
            return False
        
        print(f"\n🔍 Querying database: {db_path}")
        
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Build query
        query = """
            SELECT 
                id,
                student_id,
                timestamp,
                match_confidence,
                stream_url,
                bbox_x,
                bbox_y,
                bbox_w,
                bbox_h
            FROM attendance_events
        """
        
        params = []
        if student_id:
            query += " WHERE student_id = ?"
            params.append(student_id)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        # Execute query
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        if not rows:
            print(f"\n📭 No attendance records found")
            if student_id:
                print(f"   (for student ID: {student_id})")
            return False
        
        print(f"\n✅ Found {len(rows)} attendance record(s):\n")
        print("=" * 70)
        
        for row in rows:
            record_id, student_id, timestamp, confidence, stream_url, x, y, w, h = row
            
            print(f"\n📌 Record ID: {record_id}")
            print(f"   👤 Student ID: {student_id}")
            print(f"   ⏰ Timestamp: {timestamp}")
            print(f"   🎯 Confidence: {confidence:.2%}")
            print(f"   📹 Stream: {stream_url}")
            print(f"   📍 BBox: x={x}, y={y}, w={w}, h={h}")
        
        print("\n" + "=" * 70)
        
        # Get student names
        print("\n🔍 Looking up student names...")
        
        student_ids = [row[1] for row in rows]
        unique_ids = list(set(student_ids))
        
        if unique_ids:
            placeholders = ','.join('?' * len(unique_ids))
            cursor.execute(
                f"SELECT student_id, first_name, last_name FROM students WHERE student_id IN ({placeholders})",
                unique_ids
            )
            students = {row[0]: f"{row[1]} {row[2]}" for row in cursor.fetchall()}
            
            print("\n📋 Student Summary:")
            for sid in unique_ids:
                count = sum(1 for row in rows if row[1] == sid)
                name = students.get(sid, "Unknown")
                print(f"   {sid}: {name} ({count} record(s))")
        
        conn.close()
        
        return True
    
    except ImportError:
        print("❌ Error: sqlite3 module not available")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def custom_request():
    """Make a custom API request."""
    print_header("Custom API Request")
    
    print("\n📝 Custom Request Builder")
    print("=" * 70)
    
    # Get method
    print("\nSelect HTTP Method:")
    print("1. GET")
    print("2. POST")
    print("3. PUT")
    print("4. DELETE")
    method_choice = input("Choice (1-4): ").strip()
    
    methods = {"1": "GET", "2": "POST", "3": "PUT", "4": "DELETE"}
    method = methods.get(method_choice, "GET")
    
    # Get endpoint
    endpoint = input(f"\nEndpoint (e.g., /students/202500001): ").strip()
    if not endpoint.startswith("/"):
        endpoint = "/" + endpoint
    
    url = f"{BASE_URL}{endpoint}"
    
    # Get headers
    headers = {}
    if access_token:
        use_auth = input("\nInclude authentication token? (Y/n): ").strip().lower()
        if use_auth != 'n':
            headers["Authorization"] = f"Bearer {access_token}"
    
    # Get body (for POST/PUT)
    body = None
    if method in ["POST", "PUT"]:
        print("\nRequest Body (JSON):")
        print("Enter JSON data (or press Enter for none):")
        body_str = input().strip()
        if body_str:
            try:
                body = json.loads(body_str)
            except json.JSONDecodeError:
                print("⚠️  Invalid JSON, sending as-is")
                body = body_str
    
    # Make request
    print(f"\n🔄 Making request...")
    print(f"   Method: {method}")
    print(f"   URL: {url}")
    print(f"   Headers: {headers}")
    if body:
        print(f"   Body: {json.dumps(body, indent=2)[:200]}")
    
    try:
        client = await get_client()
        
        if method == "GET":
            response = await client.get(url, headers=headers)
        elif method == "POST":
            response = await client.post(url, json=body, headers=headers)
        elif method == "PUT":
            response = await client.put(url, json=body, headers=headers)
        elif method == "DELETE":
            response = await client.delete(url, headers=headers)
        
        print_response(response, show_full=True)
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def show_config():
    """Show current configuration."""
    print_header("Current Configuration")
    
    print("\n🔧 Global Settings:")


async def test_model_server_recognition():
    """Test model server recognition directly (bypassing backend)."""
    global model_server_access_token, model_server_refresh_token
    
    print_header("Model Server Recognition Test (Direct)")
    
    print("\n🎯 This test directly calls the Model Server's /v1/recognize_frame endpoint")
    print("   (Simulating what the backend does when processing RTSP frames)")
    
    # Step 1: Authenticate with Model Server
    print("\n🔐 Step 1: Authenticating with Model Server...")
    
    if not model_server_access_token:
        print("   No model server token found. Logging in...")
        
        # Use same credentials as main backend
        login_data = {
            "username": USER_CREDENTIALS["username"],
            "password": USER_CREDENTIALS["password"]
        }
        
        try:
            client = await get_client()
            
            # Try to login to model server
            response = await client.post(
                f"{MODEL_SERVER_URL}/v1/auth/login",
                json=login_data,
                timeout=10.0
            )
            
            if response.status_code == 200:
                tokens = response.json()
                model_server_access_token = tokens["access_token"]
                model_server_refresh_token = tokens.get("refresh_token")
                print(f"   ✅ Model server authentication successful")
            elif response.status_code == 401:
                # User doesn't exist on model server, try to register first
                print("   ℹ️  User not found on model server. Registering...")
                
                register_data = {
                    "username": USER_CREDENTIALS["username"],
                    "password": USER_CREDENTIALS["password"],
                    "email": USER_CREDENTIALS["email"]
                }
                
                reg_response = await client.post(
                    f"{MODEL_SERVER_URL}/v1/auth/register",
                    json=register_data,
                    timeout=10.0
                )
                
                if reg_response.status_code in [200, 201]:
                    print("   ✅ Registration successful. Logging in...")
                    
                    # Now try login again
                    response = await client.post(
                        f"{MODEL_SERVER_URL}/v1/auth/login",
                        json=login_data,
                        timeout=10.0
                    )
                    
                    if response.status_code == 200:
                        tokens = response.json()
                        model_server_access_token = tokens["access_token"]
                        model_server_refresh_token = tokens.get("refresh_token")
                        print(f"   ✅ Model server authentication successful")
                    else:
                        print(f"   ❌ Login failed: {response.status_code}")
                        print(f"      {response.text}")
                        return False
                else:
                    print(f"   ❌ Registration failed: {reg_response.status_code}")
                    print(f"      {reg_response.text}")
                    return False
            else:
                print(f"   ❌ Authentication failed: {response.status_code}")
                print(f"      {response.text}")
                return False
                
        except Exception as e:
            print(f"   ❌ Error during authentication: {e}")
            return False
    else:
        print("   ✅ Using existing model server token")
    
    # Step 2: Select image to test
    print("\n📸 Step 2: Select an image to test recognition:")
    print("  1. Use enrolled student photo (front)")
    print("  2. Use enrolled student photo (left)")
    print("  3. Use enrolled student photo (right)")
    print("  4. Use custom image path")
    
    choice = input("\nChoice (1-4): ").strip()
    
    image_path = None
    if choice == "1":
        image_path = PHOTO_PATHS["front"]
    elif choice == "2":
        image_path = PHOTO_PATHS["left"]
    elif choice == "3":
        image_path = PHOTO_PATHS["right"]
    elif choice == "4":
        image_path = input("Enter full path to image: ").strip()
    else:
        print("❌ Invalid choice")
        return False
    
    if not Path(image_path).exists():
        print(f"❌ Error: Image not found: {image_path}")
        return False
    
    print(f"\n📷 Loading image: {Path(image_path).name}")
    
    try:
        # Load and encode image
        image_b64 = load_image_base64(image_path)
        
        # Prepare request
        request_data = {
            "frame_base64": image_b64,
            "stream_url": "test_direct_call",
            "options": {
                "align": True,
                "anti_spoof": True,
                "distance_metric": "cosine",
                "min_confidence": 0.35
            }
        }
        
        print(f"\n🔄 Step 3: Calling Model Server: {MODEL_SERVER_URL}/v1/recognize_frame")
        print(f"   Frame size: {len(image_b64)} bytes (base64)")
        print(f"   Options: align=True, anti_spoof=True, min_confidence=0.35")
        
        client = await get_client()
        
        # Call model server directly with model server token
        response = await client.post(
            f"{MODEL_SERVER_URL}/v1/recognize_frame",
            json=request_data,
            headers={"Authorization": f"Bearer {model_server_access_token}"},
            timeout=30.0
        )
        
        print(f"\n📡 Response Status: {response.status_code}")
        
        if response.status_code == 401:
            # Token expired, try to refresh
            print("   ⚠️  Token expired. Refreshing...")
            
            if model_server_refresh_token:
                refresh_response = await client.post(
                    f"{MODEL_SERVER_URL}/v1/auth/refresh",
                    json={"refresh_token": model_server_refresh_token},
                    timeout=10.0
                )
                
                if refresh_response.status_code == 200:
                    tokens = refresh_response.json()
                    model_server_access_token = tokens["access_token"]
                    model_server_refresh_token = tokens.get("refresh_token")
                    print("   ✅ Token refreshed. Retrying...")
                    
                    # Retry the recognition request
                    response = await client.post(
                        f"{MODEL_SERVER_URL}/v1/recognize_frame",
                        json=request_data,
                        headers={"Authorization": f"Bearer {model_server_access_token}"},
                        timeout=30.0
                    )
                else:
                    print("   ❌ Token refresh failed. Please re-authenticate.")
                    model_server_access_token = None
                    model_server_refresh_token = None
                    return False
            else:
                print("   ❌ No refresh token available. Please re-authenticate.")
                model_server_access_token = None
                return False
        
        if response.status_code == 200:
            result = response.json()
            
            print("\n✅ Recognition Response:")
            print(f"   Timestamp: {result.get('timestamp', 'N/A')}")
            print(f"   Stream URL: {result.get('stream_url', 'N/A')}")
            
            detections = result.get('detections', [])
            print(f"\n👤 Detected Faces: {len(detections)}")
            
            if detections:
                for i, det in enumerate(detections, 1):
                    print(f"\n   Face #{i}:")
                    print(f"      Student ID: {det.get('student_id', 'Unknown')}")
                    print(f"      Confidence: {det.get('confidence', 0):.2%}")
                    print(f"      Is Live: {det.get('is_live', False)}")
                    print(f"      Track ID: {det.get('track_id', 'N/A')}")
                    
                    bbox = det.get('bbox', [])
                    if bbox:
                        print(f"      BBox: [{bbox[0]}, {bbox[1]}, {bbox[2]}, {bbox[3]}]")
                    
                    # Show what backend would do
                    print(f"\n   📊 Backend would:")
                    print(f"      - Look up student name from student_id: {det.get('student_id', 'Unknown')}")
                    print(f"      - Store attendance event in database")
                    print(f"      - Send WebSocket event to frontend with student name")
            else:
                print("\n   ⚠️  No faces detected in the frame")
            
            # Show full response
            show_full = input("\n\n💡 Show full JSON response? (y/N): ").strip().lower()
            if show_full == 'y':
                print(f"\n📄 Full Response:")
                print(json.dumps(result, indent=2))
            
            return True
        else:
            print(f"\n❌ Error: {response.status_code}")
            try:
                error = response.json()
                print(f"   Detail: {error.get('detail', response.text)}")
            except:
                print(f"   Response: {response.text}")
            return False
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def show_config():
    """Show current configuration."""
    print_header("Current Configuration")
    
    print("\n🔧 Global Settings:")
    print(f"   Base URL: {BASE_URL}")
    print(f"   WebSocket URL: {WS_URL}")
    
    print("\n👤 User Credentials:")
    print(f"   Username: {USER_CREDENTIALS['username']}")
    print(f"   Password: {'*' * len(USER_CREDENTIALS['password'])}")
    print(f"   Email: {USER_CREDENTIALS['email']}")
    print(f"   Full Name: {USER_CREDENTIALS['full_name']}")
    print(f"   Role: {USER_CREDENTIALS['role']}")
    
    print("\n🎓 Student Data:")
    print(f"   Student ID: {STUDENT_DATA['student_id']}")
    print(f"   Name: {STUDENT_DATA['first_name']} {STUDENT_DATA['last_name']}")
    print(f"   Email: {STUDENT_DATA['email']}")
    print(f"   Phone: {STUDENT_DATA['phone']}")
    print(f"   Metadata: {json.dumps(STUDENT_DATA['metadata'], indent=6)}")
    
    print("\n📸 Photo Paths:")
    for view, path in PHOTO_PATHS.items():
        exists = "✅" if Path(path).exists() else "❌"
        print(f"   {exists} {view}: {path}")
    
    print("\n🔐 Session Status:")
    if access_token:
        print(f"   ✅ Authenticated")
        print(f"   Access Token: {access_token[:30]}...")
        print(f"   Refresh Token: {refresh_token[:30]}...")
    else:
        print(f"   ❌ Not authenticated")


# ============================================================================
# MENU SYSTEM
# ============================================================================

def show_menu():
    """Display main menu."""
    print("\n" + "=" * 70)
    print("  🧪 INTERACTIVE API TEST MENU")
    print("=" * 70)
    print("\n📋 Authentication:")
    print("  1. Health Check")
    print("  2. Register User")
    print("  3. Login")
    print("  4. Refresh Token")
    print("  5. Logout")
    
    print("\n🎓 Student Management:")
    print("  6. Create Student")
    print("  7. Enroll Student (with photos)")
    print("  8. Get Student Details")
    print("  9. List All Students")
    
    print("\n🎥 Recognition & Monitoring:")
    print("  10. Test WebSocket Connection (5 messages)")
    print("  11. Monitor Face Recognition (Real-time)")
    print("  12. View Attendance Records (Database)")
    print("  17. 🔬 Test Model Server Recognition (Direct)")
    
    print("\n🔧 Advanced:")
    print("  13. Custom API Request")
    print("  14. Show Configuration")
    
    print("\n📊 Quick Actions:")
    print("  15. Run Full Test Suite")
    print("  16. Quick Setup (Register + Login)")
    
    print("\n  0. Exit")
    print("=" * 70)


async def run_full_test_suite():
    """Run all tests in sequence."""
    print_header("Running Full Test Suite")
    
    tests = [
        ("Health Check", test_health_check),
        ("Register User", test_register),
        ("Login", test_login),
        ("Token Refresh", test_refresh_token),
        ("Create Student", test_create_student),
        ("Enroll Student", test_enroll_student),
        ("Get Student", test_get_student),
        ("List Students", test_list_students),
    ]
    
    results = []
    for name, test_func in tests:
        print(f"\n{'─' * 70}")
        print(f"Running: {name}")
        result = await test_func()
        results.append((name, result))
        
        if not result and name in ["Register User", "Login"]:
            print(f"\n⚠️  Critical test failed: {name}")
            print("   Stopping test suite")
            break
        
        await asyncio.sleep(1)  # Brief pause between tests
    
    # Summary
    print("\n" + "=" * 70)
    print("  📊 TEST SUITE SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} - {name}")
    
    print(f"\n  Total: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    print("=" * 70)


async def quick_setup():
    """Quick setup: register + login."""
    print_header("Quick Setup")
    
    print("🚀 Running quick setup (Register + Login)...")
    
    # Register
    print("\n1️⃣ Registering user...")
    await test_register()
    await asyncio.sleep(1)
    
    # Login
    print("\n2️⃣ Logging in...")
    success = await test_login()
    
    if success:
        print("\n✅ Quick setup completed! You're now authenticated.")
    else:
        print("\n❌ Quick setup failed. Please check credentials.")


async def main():
    """Main menu loop."""
    global client
    
    print("\n" + "=" * 70)
    print("  🎉 WELCOME TO BACKEND API INTERACTIVE TESTER")
    print("=" * 70)
    print("\n💡 This tool allows you to test all backend APIs with your own data.")
    print("📝 Edit the GLOBAL CONFIGURATION section at the top of this file")
    print("   to customize user credentials, student data, and photo paths.")
    print("\n🔐 Tip: Start with 'Quick Setup' (option 16) to authenticate quickly.")
    
    try:
        while True:
            show_menu()
            
            choice = input("\nEnter your choice: ").strip()
            
            if choice == "0":
                print("\n👋 Goodbye!")
                break
            elif choice == "1":
                await test_health_check()
            elif choice == "2":
                await test_register()
            elif choice == "3":
                await test_login()
            elif choice == "4":
                await test_refresh_token()
            elif choice == "5":
                await test_logout()
            elif choice == "6":
                await test_create_student()
            elif choice == "7":
                await test_enroll_student()
            elif choice == "8":
                await test_get_student()
            elif choice == "9":
                await test_list_students()
            elif choice == "10":
                await test_websocket()
            elif choice == "11":
                await test_recognition_monitor()
            elif choice == "12":
                await test_view_attendance_records()
            elif choice == "13":
                await custom_request()
            elif choice == "14":
                await show_config()
            elif choice == "15":
                await run_full_test_suite()
            elif choice == "16":
                await quick_setup()
            elif choice == "17":
                await test_model_server_recognition()
            else:
                print("\n❌ Invalid choice. Please try again.")
            
            input("\nPress Enter to continue...")
    
    finally:
        # Cleanup
        if client:
            await client.aclose()


if __name__ == "__main__":
    print("\n🔧 Starting Interactive API Tester...")
    asyncio.run(main())
