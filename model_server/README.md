# Face Recognition Model Server

**🔒 Internal Service - Backend ↔ Model Layer Communication Only**

ArcFace recognition with YOLOv8n detection service built with FastAPI, Hypercorn, and DeepFace.

> **⚠️ REFACTORED:** This service has been completely refactored to follow the exact ML stack architecture.  
> See `REFACTORING_COMPLETE.md` for detailed changes and migration guide.

## Features

- **Complete ML Pipeline**: YOLOv8n → Alignment → ArcFace → Matching → Anti-Spoofing
- **Face Detection**: YOLOv8n via DeepFace detector_backend="yolov8"
- **Face Alignment**: Geometric transformation using facial landmarks
- **Face Recognition**: ArcFace (ResNet100) 512-D embeddings with cosine similarity
- **Multi-View Enrollment**: 5-view support (front, left, right, angled_left, angled_right)
- **Anti-Spoofing**: Liveness detection integrated
- **Multi-Stream Tracking**: ByteTrack + Kalman filter for stable track IDs
- **Secure**: Internal service authentication, embeddings never exposed

## Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                    COMPLETE ML PIPELINE                         │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Frame (numpy array)                                           │
│      ↓                                                          │
│  ┌──────────────────────────────────────────┐                 │
│  │  Step 1: YOLOv8n Face Detection         │                 │
│  │  - Via DeepFace detector_backend         │                 │
│  │  - Output: bboxes + 5 facial landmarks  │                 │
│  └──────────────┬───────────────────────────┘                 │
│                 ↓                                               │
│  ┌──────────────────────────────────────────┐                 │
│  │  Step 2: Face Alignment                 │                 │
│  │  - Geometric transform using landmarks  │                 │
│  └──────────────┬───────────────────────────┘                 │
│                 ↓                                               │
│  ┌──────────────────────────────────────────┐                 │
│  │  Step 3: Preprocessing                  │                 │
│  │  - Resize 112×112, normalize            │                 │
│  └──────────────┬───────────────────────────┘                 │
│                 ↓                                               │
│  ┌──────────────────────────────────────────┐                 │
│  │  Step 4: ArcFace Embedding              │                 │
│  │  - ResNet100: 512-D vector              │                 │
│  │  - Accuracy: 99.6% on LFW               │                 │
│  └──────────────┬───────────────────────────┘                 │
│                 ↓                                               │
│  ┌──────────────────────────────────────────┐                 │
│  │  Step 5: Cosine Similarity Matching     │                 │
│  │  - Against enrolled embeddings          │                 │
│  │  - Threshold: 0.35                      │                 │
│  └──────────────┬───────────────────────────┘                 │
│                 ↓                                               │
│  ┌──────────────────────────────────────────┐                 │
│  │  Step 6: Anti-Spoofing                  │                 │
│  │  - Liveness detection                   │                 │
│  └──────────────┬───────────────────────────┘                 │
│                 ↓                                               │
│  ┌──────────────────────────────────────────┐                 │
│  │  Step 7: ByteTrack + Kalman             │                 │
│  │  - Consistent track IDs                 │                 │
│  └──────────────┬───────────────────────────┘                 │
│                 ↓                                               │
│  Recognition Result                                            │
│  {student_id, confidence, bbox, is_live}                      │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Or with development dependencies
pip install -e ".[dev]"
```

### Environment Variables

Create a `.env` file:

```env
# Server
HOST=0.0.0.0
PORT=8001
WORKERS=2

# Models
YOLO_MODEL_PATH=yolov8n.pt
ARCFACE_MODEL_NAME=ArcFace
DETECTOR_BACKEND=retinaface

# Recognition
RECOGNITION_THRESHOLD=0.4
ANTI_SPOOF_ENABLED=true
ANTI_SPOOF_THRESHOLD=0.5

# Tracker
TRACKER_MAX_AGE=30
TRACKER_MIN_HITS=3
TRACKER_IOU_THRESHOLD=0.3

# Processing
EMBEDDING_DIM=512
MAX_BATCH_SIZE=8
DEVICE=cpu

# Cache
EMBEDDING_CACHE_SIZE=1000

# Database
ENROLLMENT_DB_PATH=./storage/enrollments.db

# Logging
LOG_LEVEL=INFO
```

## Running

### Development

```bash
# Using Hypercorn (recommended)
hypercorn app.main:app --bind 0.0.0.0:8001 --reload

hypercorn app.main:app --bind 0.0.0.0:8001 -w 1 -k trio                                          


# Or using Python directly
python -m app.main
```

### Production

```bash
# Hypercorn with Trio workers
hypercorn app.main:app \
  --bind 0.0.0.0:8001 \
  -w 2 \
  -k trio \
  --access-logfile - \
  --error-logfile -
```

### Docker

```bash
# Build image
docker build -t model-server:latest .

# Run container
docker run -d \
  -p 8001:8001 \
  -v $(pwd)/storage:/app/storage \
  --name model-server \
  model-server:latest
```

## API Endpoints

### POST /infer

Run inference on a frame.

**Request** (multipart/form-data):
- `stream_url`: Stream identifier (required)
- `frame_id`: Frame UUID (optional, auto-generated)
- `timestamp`: ISO8601 timestamp (optional, auto-generated)
- `frame`: Image file (required)
- `camera_meta`: Camera metadata JSON (optional)

**Response**:
```json
{
  "frame_id": "uuid-...",
  "stream_url": "rtsp://...",
  "detections": [
    {
      "bbox": [100, 150, 200, 250],
      "track_id": 123,
      "is_spoof": false,
      "recognized": true,
      "student_id": "202500568",
      "student_name": "Ishwan Roy",
      "match_confidence": 0.92,
      "models_used": {
        "face": "ArcFace",
        "detector": "retinaface"
      },
      "thumbnail": "base64-encoded-image"
    }
  ]
}
```

### GET /health

Health check.

**Response**:
```json
{
  "status": "healthy",
  "models_loaded": {
    "detector": true,
    "recognizer": true,
    "tracker": true
  },
  "enrollment_count": 42
}
```

### GET /models

Get active models.

**Response**:
```json
{
  "detector": "YOLOv8n",
  "recognizer": "ArcFace",
  "detector_backend": "retinaface",
  "embedding_dim": 512,
  "device": "cpu"
}
```

### POST /enroll

Enroll a student face.

**Request** (multipart/form-data):
- `student_id`: Student ID (required)
- `replace`: Replace existing enrollment (optional, default: true)
- `face_image`: Face image file (required)

**Response**:
```json
{
  "student_id": "202500568",
  "success": true,
  "embedding_dim": 512,
  "message": "Enrollment successful"
}
```

### POST /reload-enrollments

Reload enrollments from database.

**Response**:
```json
{
  "success": true,
  "enrollment_count": 42,
  "message": "Enrollments reloaded successfully"
}
```

## Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=app --cov-report=html

# Run specific test
pytest tests/test_server.py::test_health -v
```

### Manual Testing

```bash
# Health check
curl http://localhost:8001/health

# Get models
curl http://localhost:8001/models

# Enroll (requires a face image)
curl -X POST http://localhost:8001/enroll \
  -F "student_id=test123" \
  -F "face_image=@path/to/face.jpg"

# Infer (requires a frame image)
curl -X POST http://localhost:8001/infer \
  -F "stream_url=rtsp://test" \
  -F "frame=@path/to/frame.jpg"
```

## Performance Tuning

### CPU Optimization

1. **Reduce image size**: Resize frames to 640×480 before sending
2. **Batch processing**: Use `MAX_BATCH_SIZE` for multiple frames
3. **Tracker tuning**: Adjust `TRACKER_MIN_HITS` and `TRACKER_MAX_AGE`
4. **Recognition frequency**: Don't recognize every frame, use tracker

### GPU Acceleration

Set `DEVICE=cuda` in environment:

```env
DEVICE=cuda
```

Requires CUDA-compatible GPU and PyTorch with CUDA support.

## Troubleshooting

### DeepFace Installation Issues

If DeepFace fails to install or download models:

```bash
# Install dependencies manually
pip install tf-keras opencv-python gdown

# Download models manually
mkdir -p ~/.deepface/weights
# Download from DeepFace GitHub releases
```

### filterpy Import Error

Install filterpy for Kalman filtering:

```bash
pip install filterpy
```

### YOLO Model Download

YOLOv8n will auto-download on first run. To pre-download:

```bash
python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
```

## Architecture Notes

### Why Separate Model Server?

1. **Isolation**: Heavy CV models in separate process
2. **Scalability**: Scale model server independently
3. **Resource management**: CPU/GPU allocation per service
4. **Stateless**: Easy to add multiple model server replicas

### Tracker Design

- **Per-stream tracking**: Each RTSP stream has independent tracker state
- **Kalman filtering**: Smooth bounding boxes during detection misses
- **Confirmed tracks**: Only recognize after `min_hits` detections
- **Re-recognition**: Periodically re-run recognition on confirmed tracks

### Enrollment Database

SQLite database storing face embeddings as binary blobs:

```sql
CREATE TABLE enrollments (
    student_id TEXT PRIMARY KEY,
    embedding BLOB NOT NULL,
    embedding_dim INTEGER NOT NULL,
    model_version TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## License

MIT
