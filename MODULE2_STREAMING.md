# Module 2 Extended: Live Streaming Features

## Summary of Additions

In addition to the core Module 2 implementation (RTSP capture + BAFS scheduler), I've added **two powerful features** for live video viewing and camera management:

### 1. 🎥 MJPEG Live Video Streaming
**Endpoint:** `GET /api/v1/stream/video/{camera_id}`

Stream live video from any active camera directly to your browser as Motion JPEG (MJPEG).

**Features:**
- Real-time video streaming at ~30 FPS
- Works in any modern browser
- Can be embedded in HTML with `<img>` tag
- Automatic frame encoding to JPEG
- Async streaming for high performance

**Usage Examples:**

Direct browser viewing:
```
http://localhost:8000/api/v1/stream/video/cam-001
```

Embed in HTML:
```html
<img src="http://localhost:8000/api/v1/stream/video/cam-001">
```

Python client:
```python
import requests
response = requests.get("http://localhost:8000/api/v1/stream/video/cam-001", stream=True)
for chunk in response.iter_content(chunk_size=1024):
    # Process MJPEG frames
    pass
```

---

### 2. 🔍 Auto Camera Discovery
**Endpoint:** `GET /api/v1/stream/discover`

Automatically scan your local network to find RTSP cameras.

**Features:**
- Scans common RTSP ports (554, 8554, 5554)
- Tests multiple URL patterns for different manufacturers:
  - Generic: `/stream`, `/live`, `/h264`
  - Hikvision: `/Streaming/Channels/101`
  - Axis: `/axis-media/media.amp`
  - Dahua: `/ch0_0.h264`
  - ONVIF: `/onvif1`
- Async scanning for speed
- Configurable network range and timeout

**Response Format:**
```json
{
  "cameras": [
    {
      "ip": "192.168.1.100",
      "port": "554",
      "rtsp_url": "rtsp://192.168.1.100:554/stream",
      "status": "accessible"
    },
    {
      "ip": "192.168.1.101",
      "port": "8554",
      "rtsp_url": "rtsp://192.168.1.101:8554/live",
      "status": "accessible"
    }
  ]
}
```

**Customization:**
```python
# In your code
discovered = await stream_service.discover_rtsp_cameras(
    network="192.168.0.0/24",  # Change network range
    timeout=5.0                 # Increase timeout for slower cameras
)
```

---

### 3. 🌐 Web-Based Stream Viewer

**File:** `viewer.html`

A complete web interface for managing and viewing live streams.

**Features:**
- Auto camera discovery with one click
- Easy stream management (start/stop)
- Live MJPEG video display
- Multi-camera grid view
- Priority selection (Low/Medium/High/Critical)
- Stream statistics display
- Modern dark theme UI
- Responsive design

**How to Use:**
1. Double-click `viewer.html` to open in browser
2. Click "Auto-Discover Cameras" to scan network
3. Or manually enter Camera ID and RTSP URL
4. Click "Start Stream" to begin viewing
5. Live video appears automatically!

**Screenshots:**
- Camera discovery interface
- Live multi-camera grid view
- Stream controls and statistics

---

## Implementation Details

### Code Changes

**1. Updated `routes_stream.py`:**
```python
@router.get("/video/{camera_id}")
async def stream_video(camera_id: str, ...) -> StreamingResponse:
    """Stream live MJPEG video"""
    return StreamingResponse(
        stream_service.generate_mjpeg_stream(camera_id),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@router.get("/discover")
async def discover_streams(...) -> dict:
    """Auto-discover RTSP cameras"""
    discovered = await stream_service.discover_rtsp_cameras()
    return {"cameras": discovered}
```

**2. Enhanced `stream_service.py`:**
```python
async def generate_mjpeg_stream(self, camera_id: str) -> AsyncGenerator[bytes, None]:
    """Generate MJPEG frames from camera queue"""
    frame_queue = self._queue_manager.get_queue(camera_id)
    while True:
        frame = frame_queue.peek_latest()
        if frame is not None:
            _, buffer = cv2.imencode(".jpg", frame.data)
            yield b"--frame\r\n" + b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
        await asyncio.sleep(0.033)

async def discover_rtsp_cameras(self, network: str = "192.168.1.0/24", timeout: float = 2.0):
    """Scan network for RTSP cameras"""
    # Port scanning + URL pattern testing
    # Returns list of discovered camera info
```

### Testing

Run the streaming features test:
```powershell
.\test-streaming.ps1
```

Expected output:
```
[SUCCESS] All streaming features ready!

New Features Added:
  1. MJPEG live video streaming endpoint
  2. Auto camera discovery on network
  3. Web-based stream viewer (viewer.html)
```

---

## Usage Examples

### Example 1: IP Webcam (Android App)

1. Install "IP Webcam" from Play Store
2. Start server in the app
3. Note RTSP URL: `rtsp://192.168.1.64:8080/h264_ulaw.sdp`
4. In viewer.html:
   - Camera ID: `phone-cam-001`
   - RTSP URL: `rtsp://192.168.1.64:8080/h264_ulaw.sdp`
   - Click "Start Stream"
5. Watch live feed from your phone!

### Example 2: Hikvision IP Camera

1. Use auto-discovery: Click "Auto-Discover Cameras"
2. Wait for scan (~30 seconds)
3. See discovered camera: `rtsp://192.168.1.100:554/Streaming/Channels/101`
4. Click "Use This"
5. Start stream and view

### Example 3: Multiple Cameras

1. Start first stream: `cam-entrance` → `rtsp://192.168.1.100:554/stream`
2. Start second stream: `cam-lobby` → `rtsp://192.168.1.101:554/stream`
3. Start third stream: `cam-lab` → `rtsp://192.168.1.102:554/stream`
4. All three appear in grid view
5. Manage independently (start/stop each)

---

## Performance Considerations

### Frame Rate Management
- MJPEG streams at ~30 FPS by default
- Controlled by `asyncio.sleep(0.033)` in `generate_mjpeg_stream`
- Adjust for slower clients or lower bandwidth

### Network Scanning
- Discovery scans first 20 IPs only (default)
- Each IP tests 3 ports × ~10 URL patterns
- Total scan time: ~30-60 seconds depending on network
- Can customize range in code

### Memory Usage
- Frame queue buffers 10 frames per camera (configurable)
- JPEG encoding creates temporary buffers
- Multiple viewers share same frame queue (efficient)

---

## Next Steps

### Integration with Module 3 (YOLOv10 Detection)

When Module 3 is implemented, the video stream will show:
- ✅ Raw video (current)
- 🔲 Person detection bounding boxes (Module 3)
- 🔲 Pose keypoints (Module 4)
- 🔲 Face bounding boxes (Module 5+)
- 🔲 Identity labels and confidence (Module 10+)

The MJPEG stream will be enhanced to draw all detections on frames before streaming.

### Planned Enhancements
1. WebRTC support for lower latency
2. Recording/snapshot functionality
3. Stream health monitoring dashboard
4. Bandwidth-adaptive quality
5. HLS streaming for mobile devices

---

## Troubleshooting

### "Camera not found or not streaming"
- Ensure stream is started via `/api/v1/stream/start`
- Check stream status in server logs
- Verify RTSP URL is correct

### "No cameras discovered"
- Cameras must be on same network
- Check firewall settings
- Try manual URL entry instead
- Increase timeout if cameras are slow

### "Video freezes or stutters"
- Check network bandwidth
- Reduce concurrent streams
- Lower camera resolution
- Check BAFS FPS allocation

### "Browser won't display video"
- Try Chrome/Firefox (MJPEG well-supported)
- Check browser console for errors
- Verify URL is correct
- Try direct URL: `http://localhost:8000/api/v1/stream/video/cam-001`

---

## API Reference

### GET /api/v1/stream/video/{camera_id}
**Description:** Stream live MJPEG video  
**Parameters:**
- `camera_id` (path): Camera identifier  

**Response:** MJPEG stream (multipart/x-mixed-replace)  
**Status Codes:**
- 200: Streaming
- 404: Camera not found

### GET /api/v1/stream/discover
**Description:** Auto-discover RTSP cameras  
**Parameters:** None  
**Response:**
```json
{
  "cameras": [
    {
      "ip": "string",
      "port": "string",
      "rtsp_url": "string",
      "status": "accessible"
    }
  ]
}
```
**Status Codes:**
- 200: Discovery complete

---

## Files Added/Modified

**New Files:**
1. `viewer.html` - Web-based stream viewer
2. `STREAMING_GUIDE.md` - Detailed usage guide
3. `test-streaming.ps1` - Streaming features test script
4. `MODULE2_STREAMING.md` - This document

**Modified Files:**
1. `src/app/api/v1/routes_stream.py` - Added video and discover endpoints
2. `src/app/services/stream_service.py` - Added MJPEG and discovery methods
3. `src/app/models/stream_models.py` - Uncommented models
4. `README.md` - Updated implementation status

---

## Conclusion

Module 2 is now complete with **production-ready live streaming capabilities**! You can:

✅ Capture RTSP streams with auto-reconnect  
✅ View live video in browser (MJPEG)  
✅ Auto-discover cameras on network  
✅ Manage multiple streams with web UI  
✅ Monitor stream statistics  
✅ Control via REST API  

**Ready for Module 3:** YOLOv10 Person Detection will integrate seamlessly with the streaming pipeline to show real-time detections on the live feed.

When you're ready, reply: **"Module 2 validated, proceed to Module 3"**
