# Live Streaming Test Guide

## Features Added

### 1. MJPEG Video Streaming
View live camera feeds directly in your browser as MJPEG streams.

**Endpoint:** `GET /api/v1/stream/video/{camera_id}`

**Usage:**
```bash
# Direct browser access
http://localhost:8000/api/v1/stream/video/cam-001

# In HTML
<img src="http://localhost:8000/api/v1/stream/video/cam-001">
```

### 2. Auto Camera Discovery
Automatically scan your network to find RTSP cameras.

**Endpoint:** `GET /api/v1/stream/discover`

**Response:**
```json
{
  "cameras": [
    {
      "ip": "192.168.1.100",
      "port": "554",
      "rtsp_url": "rtsp://192.168.1.100:554/stream",
      "status": "accessible"
    }
  ]
}
```

## Quick Start

### Step 1: Start the Server
```powershell
.\start-dev.ps1
```

### Step 2: Open the Web Viewer
Open `viewer.html` in your browser:
```
file:///C:/Users/swarn/OneDrive - 3602sv/Original Projects/5G LAB CCTV Project/Face Recognition v3/viewer.html
```

Or simply double-click `viewer.html` in File Explorer.

### Step 3: Discover Cameras (Optional)
1. Click "Auto-Discover Cameras" button
2. Wait for scan to complete (~30 seconds)
3. Click "Use This" on any discovered camera

### Step 4: Start Streaming
1. Enter Camera ID (e.g., `cam-001`)
2. Enter RTSP URL (e.g., `rtsp://192.168.1.64:8080/h264_ulaw.sdp`)
3. Select Priority (Low/Medium/High/Critical)
4. Click "Start Stream"
5. Live video will appear automatically!

## Testing with IP Webcam App (Android)

1. Install "IP Webcam" app from Play Store
2. Open app and scroll to bottom
3. Tap "Start server"
4. Note the RTSP URL shown (e.g., `rtsp://192.168.1.64:8080/h264_ulaw.sdp`)
5. Use this URL in the viewer

## API Testing with cURL

### Start Stream
```powershell
curl -X POST http://localhost:8000/api/v1/stream/start `
  -H "Content-Type: application/json" `
  -d '{\"camera_id\": \"cam-001\", \"rtsp_url\": \"rtsp://192.168.1.64:8080/h264_ulaw.sdp\", \"config_name\": \"default\"}'
```

### View Stream
```powershell
# Open in browser
start http://localhost:8000/api/v1/stream/video/cam-001
```

### Stop Stream
```powershell
curl -X POST http://localhost:8000/api/v1/stream/stop `
  -H "Content-Type: application/json" `
  -d '{\"camera_id\": \"cam-001\"}'
```

### Discover Cameras
```powershell
curl http://localhost:8000/api/v1/stream/discover
```

## Troubleshooting

### Stream Not Showing
1. Check server is running: `http://localhost:8000/docs`
2. Verify RTSP URL is correct
3. Check if camera is accessible on network
4. Try lower resolution settings on camera

### Discovery Not Finding Cameras
1. Ensure cameras are on same network (192.168.1.x)
2. Discovery scans first 20 IPs only (customize in code if needed)
3. Some cameras may use non-standard ports
4. Try manual URL entry instead

### Slow Performance
1. Reduce frame rate in BAFS settings
2. Lower camera resolution
3. Check network bandwidth
4. Limit number of concurrent streams

## Network Configuration

The discovery scans:
- Network: `192.168.1.0/24` (customizable)
- Ports: `554`, `8554`, `5554`
- URL patterns:
  - `/stream`, `/stream1`, `/live`
  - Hikvision: `/Streaming/Channels/101`
  - Axis: `/axis-media/media.amp`
  - Dahua: `/ch0_0.h264`
  - ONVIF: `/onvif1`

To customize, edit `stream_service.py`:
```python
await stream_service.discover_rtsp_cameras(
    network="192.168.0.0/24",  # Change network
    timeout=5.0                 # Increase timeout
)
```

## Next Steps

Once streaming works:
1. Reply: "Module 2 validated, proceed to Module 3"
2. Module 3 will add YOLOv10 person detection
3. You'll see bounding boxes drawn on the live stream
4. Then pose estimation and face recognition in later modules
