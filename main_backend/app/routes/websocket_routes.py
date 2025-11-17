"""
WebSocket routes for real-time recognition events.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])


class ConnectionManager:
    """Manage WebSocket connections."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        """Accept and store a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"✅ WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"🔌 WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def broadcast(self, message: dict):
        """
        Broadcast a message to all connected clients.
        
        Args:
            message: Message dictionary to send
        """
        if not self.active_connections:
            return
        
        disconnected = []
        
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"❌ Error sending to WebSocket: {e}")
                disconnected.append(connection)
        
        # Remove disconnected clients
        for connection in disconnected:
            self.disconnect(connection)
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """
        Send a message to a specific client.
        
        Args:
            message: Message dictionary to send
            websocket: Target WebSocket connection
        """
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"❌ Error sending to WebSocket: {e}")
            self.disconnect(websocket)


# Global connection manager
manager = ConnectionManager()


@router.websocket("/ws/events")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time recognition events.
    
    Clients connect to this endpoint to receive:
    - Recognition events (when faces are detected and matched)
    - System status updates
    - Attendance events
    
    Message format:
    ```json
    {
        "type": "recognition_event",
        "stream_url": "rtsp://...",
        "frame_time": "2025-11-09T12:30:00Z",
        "detections": [
            {
                "bbox": [x1, y1, x2, y2],
                "matched": true,
                "student_id": "202500568",
                "student_name": "John Doe",
                "match_confidence": 0.92,
                "match_modality": "face",
                "thumbnail_url": "/cache/frames/frame_abc.jpg"
            }
        ]
    }
    ```
    """
    await manager.connect(websocket)
    
    try:
        # Send initial connection message
        await manager.send_personal_message({
            "type": "connection",
            "status": "connected",
            "timestamp": datetime.utcnow().isoformat()
        }, websocket)
        
        # Keep connection alive and handle incoming messages
        while True:
            # Receive messages from client (heartbeat, subscriptions, etc.)
            data = await websocket.receive_text()
            
            # Echo back or handle client commands
            message = json.loads(data)
            
            if message.get("type") == "ping":
                await manager.send_personal_message({
                    "type": "pong",
                    "timestamp": datetime.utcnow().isoformat()
                }, websocket)
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("🔌 Client disconnected")
    
    except Exception as e:
        logger.error(f"❌ WebSocket error: {e}")
        manager.disconnect(websocket)


async def broadcast_recognition_event(event: dict):
    """
    Broadcast a recognition event to all connected WebSocket clients.
    
    Args:
        event: Recognition event dictionary
    """
    await manager.broadcast(event)
