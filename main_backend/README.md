# Face Recognition Backend

Complete backend service for the Face Recognition Attendance System.

## 🏗️ Architecture

```
Frontend (React/Vue)
    ↓
Main Backend (Port 8000) ← THIS SERVICE
    ↓
Model Server (Port 8001)
```

## 📋 Features

- ✅ **JWT Authentication** - Secure login with access and refresh tokens
- ✅ **Student Management** - Create and manage student records
- ✅ **Face Enrollment** - Upload 5 face images per student and generate embeddings
- ✅ **RTSP Stream Processing** - Process multiple camera streams with FFmpeg
- ✅ **Motion Detection** - BAFS (Background Subtraction) for efficient processing
- ✅ **Real-time Recognition** - WebSocket updates for live attendance
- ✅ **Attendance Tracking** - Store all recognition events in database

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd main_backend
pip install -r requirements.txt
```
hypercorn main:app --bind 0.0.0.0:8000 --worker-class asyncio --workers 1 --access-logfile - --error-logfile -

**Note:** The backend uses:
- **SQLAlchemy** for all database operations (async ORM)
- **Hypercorn 0.18.0** for ASGI server with HTTP/2 and improved WebSocket support

### 2. Configure Environment

Copy `.env.example` to `.env` and update:

```bash
cp .env.example .env
```

Edit `.env`:
```env
# Model Server Configuration
MODEL_SERVER_URL=http://localhost:8001
MODEL_SERVER_USERNAME=backend_service
MODEL_SERVER_PASSWORD=SecurePassword123!

# RTSP Streams (comma-separated)
RTSP_STREAMS=rtsp://192.168.1.100:554/stream1,rtsp://192.168.1.101:554/stream1

# JWT Secret (change in production!)
JWT_SECRET_KEY=your-super-secret-jwt-key-change-this-in-production
```

### 3. Initialize Database

The database is automatically created on first run using SQLAlchemy migrations.

### 4. Start the Server

**Recommended (using run.py):**
```bash
python run.py
```

**Or directly with main.py:**
```bash
python main.py
```

**Or with hypercorn command:**
```bash
hypercorn main:app --bind 0.0.0.0:8000 --reload
```

The server will start with:
- **Server:** Hypercorn (ASGI)
- **Database:** SQLAlchemy with async SQLite
- **Port:** 8000 (configurable in .env)

### 5. Access API Documentation

Open browser: http://localhost:8000/docs

## 📚 API Endpoints

### Authentication

- `POST /api/v1/backend/auth/register` - Register new user (admin/operator)
- `POST /api/v1/backend/auth/login` - Login and get JWT tokens
- `POST /api/v1/backend/auth/refresh` - Refresh access token
- `POST /api/v1/backend/auth/logout` - Logout (revoke refresh token)

### Students

- `POST /api/v1/backend/students` - Create new student
- `POST /api/v1/backend/students/{id}/enroll` - Enroll student with 5 images
- `GET /api/v1/backend/students/{id}` - Get student details

### WebSocket

- `WS /api/v1/backend/ws/events` - Real-time recognition events

### Health

- `GET /api/v1/backend/health` - System health check
- `GET /api/v1/backend/` - Root endpoint

## 🔄 Complete Workflow

### 1. User Registration (One-time)

```bash
curl -X POST "http://localhost:8000/api/v1/backend/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123456",
    "full_name": "System Administrator",
    "role": "admin"
  }'
```

### 2. Login

```bash
curl -X POST "http://localhost:8000/api/v1/backend/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123456"
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### 3. Create Student

```bash
curl -X POST "http://localhost:8000/api/v1/backend/students" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "student_id": "202500568",
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com"
  }'
```

### 4. Enroll Student

```bash
curl -X POST "http://localhost:8000/api/v1/backend/students/202500568/enroll" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "images": {
      "front": "<base64-image-or-file-path>",
      "left": "<base64-image-or-file-path>",
      "right": "<base64-image-or-file-path>",
      "angled_left": "<base64-image-or-file-path>",
      "angled_right": "<base64-image-or-file-path>"
    }
  }'
```

**What happens:**
1. ✅ Backend validates images
2. ✅ Converts to base64 if needed
3. ✅ Saves images to disk (`storage/photos/2025/202500568/`)
4. ✅ Sends images to model server
5. ✅ Model server generates embeddings (ArcFace 512-D)
6. ✅ Model server stores embeddings in its DB
7. ✅ Backend stores photo paths in its DB
8. ✅ Returns enrollment confirmation

### 5. RTSP Stream Processing (Automatic)

When backend starts, it automatically:

1. ✅ Connects to configured RTSP streams
2. ✅ Uses FFmpeg to capture frames (efficient, no lag)
3. ✅ Applies BAFS motion detection
4. ✅ Extracts keyframes only when motion detected
5. ✅ Sends keyframes to model server for recognition
6. ✅ Model server matches faces against stored embeddings
7. ✅ Backend receives recognition results
8. ✅ Stores attendance events in database
9. ✅ Broadcasts events via WebSocket to frontend

### 6. Real-time Recognition (WebSocket)

Frontend connects to WebSocket:

```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/backend/ws/events');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.type === 'recognition_event') {
    console.log('Recognition:', data);
    // Update UI with detected students
  }
};
```

**Event format:**
```json
{
  "type": "recognition_event",
  "stream_url": "rtsp://192.168.1.100:554/stream1",
  "frame_time": "2025-11-09T12:30:00Z",
  "detections": [
    {
      "bbox": [120, 80, 350, 410],
      "matched": true,
      "student_id": "202500568",
      "student_name": "John Doe",
      "match_confidence": 0.92,
      "match_modality": "face",
      "models_used": {"face": "ArcFace"},
      "is_live": true
    }
  ]
}
```

## 🗄️ Database Schema

### users
- `id` (UUID) - Primary key
- `username` (TEXT) - Unique username
- `password_hash` (TEXT) - Bcrypt hashed password
- `full_name` (TEXT) - User's full name
- `role` (TEXT) - admin or operator
- `is_active` (BOOLEAN) - Account status

### students
- `student_id` (TEXT) - Primary key (e.g., 202500568)
- `first_name` (TEXT) - Student first name
- `last_name` (TEXT) - Student last name
- `email` (TEXT) - Student email
- `phone` (TEXT) - Contact number

### student_photos
- `id` (UUID) - Primary key
- `student_id` (TEXT) - Foreign key → students
- `front_path` (TEXT) - Path to front image
- `left_path` (TEXT) - Path to left image
- `right_path` (TEXT) - Path to right image
- `angled_left_path` (TEXT) - Path to angled left image
- `angled_right_path` (TEXT) - Path to angled right image
- `uploaded_by` (UUID) - Foreign key → users

### attendance_events
- `id` (UUID) - Primary key
- `student_id` (TEXT) - Foreign key → students
- `stream_url` (TEXT) - Camera stream URL
- `camera_frame_time` (TIMESTAMP) - Frame timestamp
- `match_confidence` (FLOAT) - Confidence score (0-1)
- `match_modality` (TEXT) - Recognition type (face, fused, etc.)
- `matcher_model_version` (TEXT) - Model version used
- `bbox` (TEXT) - Bounding box JSON
- `is_live` (BOOLEAN) - Liveness detection result

## 🔧 Configuration

### `.env` File

| Variable | Description | Default |
|----------|-------------|---------|
| `BACKEND_HOST` | Server host | 0.0.0.0 |
| `BACKEND_PORT` | Server port | 8000 |
| `DATABASE_URL` | SQLite database URL | sqlite+aiosqlite:///./storage/main_backend.db |
| `JWT_SECRET_KEY` | JWT signing key | (change in production!) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifetime | 60 |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token lifetime | 30 |
| `MODEL_SERVER_URL` | Model server URL | http://localhost:8001 |
| `MODEL_SERVER_USERNAME` | Model server username | backend_service |
| `MODEL_SERVER_PASSWORD` | Model server password | SecurePassword123! |
| `RTSP_STREAMS` | Comma-separated RTSP URLs | (empty) |
| `MOTION_DETECTION_THRESHOLD` | BAFS motion threshold | 500 |
| `KEYFRAME_INTERVAL` | Extract keyframe every N frames | 30 |
| `PROCESS_EVERY_N_FRAMES` | Process every Nth frame | 5 |
| `CORS_ORIGINS` | Allowed origins | http://localhost:3000 |

## 🔐 Security

- ✅ JWT authentication for all protected endpoints
- ✅ Password hashing with bcrypt
- ✅ Role-based access control (admin/operator)
- ✅ Token refresh mechanism
- ✅ Token revocation on logout
- ✅ CORS configuration
- ✅ Input validation with Pydantic

## 📊 Performance

### Stream Processing
- **FFmpeg** - Efficient RTSP frame capture (no OpenCV lag)
- **BAFS** - Motion detection to reduce processing load
- **Keyframe Extraction** - Process only important frames
- **Async Processing** - Non-blocking I/O for multiple streams

### Recognition Speed
- Frame processing: ~100-200ms per frame
- Motion detection: ~10ms per frame
- Recognition (model server): ~100ms per face
- WebSocket broadcast: <5ms

## 🧪 Testing

### Test Scripts

See `tests/` directory for:
- `test_auth.py` - Authentication flow tests
- `test_student.py` - Student management tests
- `test_enrollment.py` - Enrollment workflow tests
- `test_websocket.py` - WebSocket connection tests

### Run Tests

```bash
pytest tests/
```

## 📝 Logs

Logs are printed to console with format:
```
2025-11-09 12:30:00 - app.main - INFO - 🚀 Starting Face Recognition Backend...
2025-11-09 12:30:01 - app.services.model_server_service - INFO - ✅ Logged in to model server
2025-11-09 12:30:02 - app.services.stream_processor - INFO - 🎥 Stream processor started: rtsp://...
```

## 🐛 Troubleshooting

### Database Connection Error
- Check `DATABASE_URL` in `.env`
- Ensure `storage/` directory exists and is writable

### Model Server Connection Error
- Verify model server is running on port 8001
- Check `MODEL_SERVER_URL` in `.env`
- Check model server credentials

### RTSP Stream Error
- Verify RTSP URLs are accessible
- Check network connectivity
- Ensure FFmpeg is installed: `ffmpeg -version`

### WebSocket Not Receiving Events
- Check CORS configuration
- Verify WebSocket URL is correct
- Ensure RTSP streams are configured and have motion

## 🚀 Deployment

### Production Checklist

- [ ] Change `JWT_SECRET_KEY` to strong random key
- [ ] Set `DEBUG=false`
- [ ] Use PostgreSQL instead of SQLite
- [ ] Set up reverse proxy (nginx)
- [ ] Enable HTTPS/TLS
- [ ] Configure firewall rules
- [ ] Set up monitoring and logging
- [ ] Back up database regularly
- [ ] Use environment variables for secrets
- [ ] Set up CI/CD pipeline

### Docker Deployment (Optional)

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install FFmpeg
RUN apt-get update && apt-get install -y ffmpeg

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 📞 Support

For issues or questions:
1. Check logs for error messages
2. Verify configuration in `.env`
3. Test model server connection: `GET /api/v1/backend/health`
4. Check API documentation: http://localhost:8000/docs

## 📄 License

MIT License - See LICENSE file for details
