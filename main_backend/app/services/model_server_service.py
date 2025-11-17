"""
Service to interact with the Model Server for face recognition.
"""
import httpx
import base64
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class ModelServerService:
    """Service to communicate with the Model Server."""
    
    def __init__(self):
        self.base_url = settings.model_server_url
        self.username = settings.model_server_username
        self.password = settings.model_server_password
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None
        self._client: Optional[httpx.AsyncClient] = None
        self._registered = False
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client
    
    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def _register(self) -> bool:
        """Register backend service with model server (one-time)."""
        try:
            client = await self._get_client()
            response = await client.post(
                f"{self.base_url}/v1/auth/register",
                json={
                    "username": self.username,
                    "password": self.password,
                    "email": f"{self.username}@backend.local"
                }
            )
            
            if response.status_code == 201:
                logger.info("✅ Backend service registered with model server")
                self._registered = True
                return True
            elif response.status_code == 409:
                # Already registered
                logger.info("✅ Backend service already registered")
                self._registered = True
                return True
            else:
                logger.error(f"❌ Registration failed: {response.text}")
                return False
        except Exception as e:
            logger.error(f"❌ Registration error: {e}")
            return False
    
    async def _login(self) -> bool:
        """Login and get JWT tokens."""
        try:
            # Register first if not done
            if not self._registered:
                await self._register()
            
            client = await self._get_client()
            response = await client.post(
                f"{self.base_url}/v1/auth/login",
                json={
                    "username": self.username,
                    "password": self.password
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data["access_token"]
                self.refresh_token = data["refresh_token"]
                expires_in = data.get("expires_in", 1800)
                self.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                logger.info("✅ Logged in to model server")
                return True
            else:
                logger.error(f"❌ Login failed: {response.text}")
                return False
        except Exception as e:
            logger.error(f"❌ Login error: {e}")
            return False
    
    async def _ensure_token_valid(self):
        """Ensure access token is valid, refresh if needed."""
        # Check if token exists and is not expired
        if not self.access_token or not self.token_expires_at:
            await self._login()
            return
        
        # Refresh if token expires in less than 5 minutes
        if datetime.utcnow() >= self.token_expires_at - timedelta(minutes=5):
            await self._refresh_token()
    
    async def _refresh_token(self) -> bool:
        """Refresh access token using refresh token."""
        try:
            client = await self._get_client()
            response = await client.post(
                f"{self.base_url}/v1/auth/refresh",
                json={"refresh_token": self.refresh_token}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data["access_token"]
                self.refresh_token = data["refresh_token"]
                expires_in = data.get("expires_in", 1800)
                self.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                logger.info("✅ Token refreshed")
                return True
            else:
                logger.warning("❌ Token refresh failed, re-logging in")
                return await self._login()
        except Exception as e:
            logger.error(f"❌ Token refresh error: {e}")
            return await self._login()
    
    def _headers(self) -> Dict[str, str]:
        """Get headers with authorization token."""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    async def enroll_student(
        self,
        student_id: str,
        images: Dict[str, bytes]
    ) -> Dict[str, Any]:
        """
        Enroll a student with multiple face views in model server.
        
        Args:
            student_id: Student ID
            images: Dict of {view_name: image_bytes}
        
        Returns:
            Enrollment result from model server
        
        Raises:
            Exception: If enrollment fails
        """
        await self._ensure_token_valid()
        
        # Convert images to base64
        images_b64 = {}
        for view_name, img_bytes in images.items():
            images_b64[view_name] = base64.b64encode(img_bytes).decode('utf-8')
        
        try:
            client = await self._get_client()
            response = await client.post(
                f"{self.base_url}/v1/enroll_embeddings",
                headers=self._headers(),
                json={
                    "student_id": student_id,
                    "images": images_b64
                },
                timeout=60.0  # Enrollment can take longer
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                error_msg = response.text
                logger.error(f"❌ Enrollment failed: {error_msg}")
                raise Exception(f"Enrollment failed: {error_msg}")
        
        except Exception as e:
            logger.error(f"❌ Enrollment error: {e}")
            raise
    
    async def recognize_frame(
        self,
        stream_url: str,
        frame: bytes
    ) -> Dict[str, Any]:
        """
        Recognize faces in a frame.
        
        Args:
            stream_url: RTSP stream URL
            frame: Frame image bytes
        
        Returns:
            Recognition result with detections
        
        Raises:
            Exception: If recognition fails
        """
        await self._ensure_token_valid()
        
        frame_b64 = base64.b64encode(frame).decode('utf-8')
        
        try:
            client = await self._get_client()
            response = await client.post(
                f"{self.base_url}/v1/recognize_frame",
                headers=self._headers(),
                json={
                    "stream_url": stream_url,
                    "frame_base64": frame_b64
                },
                timeout=10.0
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                error_msg = response.text
                logger.error(f"❌ Recognition failed: {error_msg}")
                raise Exception(f"Recognition failed: {error_msg}")
        
        except httpx.TimeoutException:
            logger.warning("⏱️ Recognition timeout")
            return {
                "frame_id": None,
                "timestamp": datetime.utcnow().isoformat(),
                "stream_url": stream_url,
                "detections": []
            }
        except Exception as e:
            logger.error(f"❌ Recognition error: {e}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check model server health.
        
        Returns:
            Health status
        """
        await self._ensure_token_valid()
        
        try:
            client = await self._get_client()
            response = await client.get(
                f"{self.base_url}/v1/health",
                headers=self._headers(),
                timeout=5.0
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"status": "unhealthy", "error": response.text}
        except Exception as e:
            logger.error(f"❌ Health check error: {e}")
            return {"status": "unreachable", "error": str(e)}


# Global model server service instance
model_server_service = ModelServerService()
