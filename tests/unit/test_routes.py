"""
Unit tests for FastAPI routes (Module 1).

Tests all API endpoints with strict type validation.
"""

import io
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestHealthRoutes:
    """Test health check endpoints."""

    def test_health_check_success(self) -> None:
        """Test GET /api/v1/health returns correct response."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "uptime_seconds" in data

        assert isinstance(data["status"], str)
        assert isinstance(data["timestamp"], str)
        assert isinstance(data["uptime_seconds"], (int, float))
        assert data["uptime_seconds"] >= 0.0

        # Validate timestamp format (ISO 8601)
        datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))


class TestDeviceRoutes:
    """Test device registration endpoints."""

    def test_register_device_success(self) -> None:
        """Test POST /api/v1/devices/register with valid data."""
        payload = {
            "device_id": "edge-001",
            "model": "jetson-nano",
            "location": "lab-entrance",
        }
        response = client.post("/api/v1/devices/register", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["device_id"] == "edge-001"
        assert data["status"] == "registered"
        assert "registered_at" in data
        assert isinstance(data["registered_at"], str)

        # Validate timestamp
        datetime.fromisoformat(data["registered_at"].replace("Z", "+00:00"))

    def test_register_device_missing_fields(self) -> None:
        """Test POST /api/v1/devices/register with missing fields."""
        payload = {"device_id": "edge-001"}
        response = client.post("/api/v1/devices/register", json=payload)
        assert response.status_code == 422  # Validation error


class TestStreamRoutes:
    """Test stream management endpoints."""

    def test_start_stream_success(self) -> None:
        """Test POST /api/v1/stream/start with valid data."""
        payload = {
            "camera_id": "cam-001",
            "rtsp_url": "rtsp://192.168.1.100:554/stream",
            "config_name": "default",
        }
        response = client.post("/api/v1/stream/start", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["camera_id"] == "cam-001"
        assert isinstance(data["started"], bool)
        assert data["started"] is True
        assert isinstance(data["message"], str)

    def test_stop_stream_success(self) -> None:
        """Test POST /api/v1/stream/stop with valid data."""
        # First start a stream
        start_payload = {
            "camera_id": "cam-002",
            "rtsp_url": "rtsp://192.168.1.101:554/stream",
            "config_name": "default",
        }
        client.post("/api/v1/stream/start", json=start_payload)

        # Then stop it
        stop_payload = {"camera_id": "cam-002"}
        response = client.post("/api/v1/stream/stop", json=stop_payload)
        assert response.status_code == 200

        data = response.json()
        assert data["camera_id"] == "cam-002"
        assert isinstance(data["stopped"], bool)


class TestModelRoutes:
    """Test model management endpoints."""

    def test_list_models_success(self) -> None:
        """Test GET /api/v1/models returns model list."""
        response = client.get("/api/v1/models")
        assert response.status_code == 200

        data = response.json()
        assert "models" in data
        assert isinstance(data["models"], list)

        # Check stub data structure
        if len(data["models"]) > 0:
            model = data["models"][0]
            assert "name" in model
            assert "version" in model
            assert "stage" in model
            assert "checksum" in model
            assert isinstance(model["name"], str)
            assert isinstance(model["version"], str)
            assert isinstance(model["stage"], str)
            assert isinstance(model["checksum"], str)
            assert len(model["checksum"]) == 64  # SHA256

    def test_activate_model_success(self) -> None:
        """Test POST /api/v1/models/activate with valid data."""
        payload = {"name": "yolov10-tiny", "version": "1.0.0"}
        response = client.post("/api/v1/models/activate", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data["success"], bool)
        assert isinstance(data["message"], str)


class TestAttendanceRoutes:
    """Test attendance management endpoints."""

    def test_enroll_student_success(self) -> None:
        """Test POST /api/v1/attendance/enroll with multipart data."""
        # Create fake image file
        image_content = b"fake-image-data"
        files = {"image": ("test.jpg", io.BytesIO(image_content), "image/jpeg")}
        data = {"camera_id": "cam-001", "student_id": "student-001"}

        response = client.post("/api/v1/attendance/enroll", data=data, files=files)
        assert response.status_code == 200

        result = response.json()
        assert result["student_id"] == "student-001"
        assert isinstance(result["enrolled"], bool)
        assert isinstance(result["embedding_id"], str)

    def test_query_attendance_success(self) -> None:
        """Test GET /api/v1/attendance with query params."""
        params = {"camera_id": "cam-001", "date": "2025-10-27"}
        response = client.get("/api/v1/attendance", params=params)
        assert response.status_code == 200

        data = response.json()
        assert data["camera_id"] == "cam-001"
        assert data["date"] == "2025-10-27"
        assert "records" in data
        assert isinstance(data["records"], list)

        # Check record structure
        if len(data["records"]) > 0:
            record = data["records"][0]
            assert "student_id" in record
            assert "start_time" in record
            assert "end_time" in record or record.get("end_time") is None
            assert "confidence" in record
            assert "camera_id" in record
            assert isinstance(record["confidence"], (int, float))
            assert 0.0 <= record["confidence"] <= 1.0


class TestRootEndpoint:
    """Test root endpoint."""

    def test_root_endpoint(self) -> None:
        """Test GET / returns welcome message."""
        response = client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert "message" in data
        assert isinstance(data["message"], str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
