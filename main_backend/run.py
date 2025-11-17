"""
Run script for Face Recognition Backend using Hypercorn 0.18.0 with asyncio.
Reverted from Trio due to aiosqlite compatibility issues.
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from hypercorn.config import Config
from hypercorn.asyncio import serve
import asyncio
from main import app, logger
from app.config import settings


def main():
    """Start the Hypercorn server with asyncio."""
    config = Config()
    
    # Bind configuration (Hypercorn 0.18.0 supports multiple binds)
    config.bind = [f"{settings.backend_host}:{settings.backend_port}"]
    
    # Logging configuration
    config.accesslog = "-"  # Log to stdout
    config.errorlog = "-"   # Log to stdout
    config.loglevel = "INFO"  # Always use INFO level
    
    # Worker configuration - asyncio worker
    config.worker_class = "asyncio"
    config.workers = 1  # Single worker for development (increase for production)
    
    # WebSocket configuration (improved in 0.18.0)
    config.websocket_ping_interval = 20  # Send ping every 20 seconds
    config.websocket_max_message_size = 16 * 1024 * 1024  # 16MB max message size
    
    # HTTP/2 support (0.18.0 has better HTTP/2 support)
    config.alpn_protocols = ["h2", "http/1.1"]  # Enable HTTP/2
    
    # Keep-alive settings
    config.keep_alive_timeout = 5
    
    # Graceful shutdown settings
    config.graceful_timeout = 10
    config.shutdown_timeout = 60
    
    # Performance tuning
    config.backlog = 100  # Connection backlog
    
    # Development mode settings
    if settings.debug:
        config.use_reloader = True  # Auto-reload on file changes
        config.reload_includes = ["*.py", ".env"]
    
    logger.info(f"🚀 Starting Hypercorn v0.18.0 server with asyncio")
    logger.info(f"🌐 Server running on: http://{settings.backend_host}:{settings.backend_port}")
    logger.info(f"📚 API Documentation: http://{settings.backend_host}:{settings.backend_port}/docs")
    logger.info(f"🔧 Debug mode: {'enabled' if settings.debug else 'disabled'}")
    logger.info(f"⚡ HTTP/2 support: enabled")
    logger.info(f"🔌 WebSocket ping interval: {config.websocket_ping_interval}s")
    
    # Run the server with asyncio
    asyncio.run(serve(app, config))


if __name__ == "__main__":
    main()
