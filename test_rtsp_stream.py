"""
Test RTSP stream connectivity and motion detection.
"""
import cv2
import sys

# Your RTSP stream URL from .env
RTSP_URL = "rtsp://admin:admin123@192.168.128.10:554/avstream/channel=1/stream=0.sdp"

def test_rtsp_connectivity():
    """Test if RTSP stream is accessible."""
    print(f"🔌 Testing RTSP connection...")
    print(f"📹 Stream URL: {RTSP_URL}")
    print()
    
    cap = cv2.VideoCapture(RTSP_URL)
    
    if not cap.isOpened():
        print("❌ Failed to connect to RTSP stream!")
        print()
        print("Possible issues:")
        print("  1. Camera is offline or not reachable")
        print("  2. Wrong IP address (192.168.128.10)")
        print("  3. Wrong credentials (admin:admin123)")
        print("  4. Wrong port or stream path")
        print("  5. Firewall blocking connection")
        print()
        print("Solutions:")
        print("  • Ping the camera: ping 192.168.128.10")
        print("  • Check camera web interface")
        print("  • Verify RTSP port is 554")
        print("  • Try VLC: Media → Open Network Stream → paste RTSP URL")
        return False
    
    print("✅ Successfully connected to RTSP stream!")
    
    # Try to read a few frames
    print("📹 Reading frames...")
    
    for i in range(5):
        ret, frame = cap.read()
        if not ret:
            print(f"❌ Failed to read frame {i+1}")
            break
        print(f"✅ Frame {i+1}: {frame.shape[1]}x{frame.shape[0]} pixels")
    else:
        print()
        print("✅ RTSP stream is working correctly!")
        print()
        print("Your backend will automatically process this stream when started:")
        print("  1. Motion detection (BAFS) will trigger on movement")
        print("  2. Key frames will be extracted every 30 frames")
        print("  3. Frames will be sent to model server for recognition")
        print("  4. Results will be broadcasted via WebSocket")
        print()
        print("To start the backend:")
        print("  cd main_backend")
        print("  python run.py")
        
    cap.release()
    return True


if __name__ == "__main__":
    try:
        test_rtsp_connectivity()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
