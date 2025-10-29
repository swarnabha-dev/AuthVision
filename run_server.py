"""
Server launcher script that properly sets up the Python path.
This ensures imports work correctly when running hypercorn.
"""
import sys
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# Now import and run hypercorn
if __name__ == "__main__":
    from hypercorn.config import Config
    from hypercorn.asyncio import serve
    import asyncio
    from app.main import app
    
    config = Config()
    config.bind = ["0.0.0.0:8000"]
    config.loglevel = "info"
    
    print("=" * 60)
    print("Smart Attendance API Server")
    print("=" * 60)
    print(f"Server running at: http://localhost:8000")
    print(f"API Documentation: http://localhost:8000/docs")
    print(f"Python path: {src_path}")
    print("Press Ctrl+C to stop")
    print("=" * 60)
    print()
    
    asyncio.run(serve(app, config))
