"""
Quick verification script to test Hypercorn 0.18.0 and SQLAlchemy setup.
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


async def test_imports():
    """Test that all required modules can be imported."""
    print("🧪 Testing imports...")
    
    try:
        import hypercorn
        print(f"   ✅ Hypercorn version: {hypercorn.__version__}")
        assert hypercorn.__version__ == "0.18.0", f"Expected Hypercorn 0.18.0, got {hypercorn.__version__}"
        
        import sqlalchemy
        print(f"   ✅ SQLAlchemy version: {sqlalchemy.__version__}")
        
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
        print("   ✅ SQLAlchemy async imports successful")
        
        from fastapi import FastAPI
        print("   ✅ FastAPI imported")
        
        from app.database import engine, AsyncSessionLocal, get_db
        print("   ✅ Database module imported")
        
        from app.models import User, Student, StudentPhoto, AttendanceEvent
        print("   ✅ Models imported")
        
        print("\n✅ All imports successful!\n")
        return True
        
    except ImportError as e:
        print(f"\n❌ Import error: {e}\n")
        return False
    except AssertionError as e:
        print(f"\n❌ Version mismatch: {e}\n")
        return False


async def test_database():
    """Test database connection and SQLAlchemy operations."""
    print("🧪 Testing database operations...")
    
    try:
        from app.database import engine, AsyncSessionLocal
        from app.models import Base
        from sqlalchemy import select, text
        
        # Test engine creation
        print("   ✅ Database engine created")
        
        # Test table creation
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("   ✅ Tables created successfully")
        
        # Test session
        async with AsyncSessionLocal() as session:
            # Test query execution
            result = await session.execute(text("SELECT 1"))
            value = result.scalar()
            assert value == 1
            print("   ✅ Database query executed")
        
        print("\n✅ Database operations successful!\n")
        return True
        
    except Exception as e:
        print(f"\n❌ Database error: {e}\n")
        return False


async def test_hypercorn_config():
    """Test Hypercorn configuration."""
    print("🧪 Testing Hypercorn configuration...")
    
    try:
        from hypercorn.config import Config
        
        config = Config()
        config.bind = ["0.0.0.0:8000"]
        config.worker_class = "asyncio"
        config.alpn_protocols = ["h2", "http/1.1"]
        config.websocket_ping_interval = 20
        config.keep_alive_timeout = 5
        config.graceful_timeout = 10
        
        print(f"   ✅ Bind address: {config.bind}")
        print(f"   ✅ Worker class: {config.worker_class}")
        print(f"   ✅ ALPN protocols: {config.alpn_protocols}")
        print(f"   ✅ WebSocket ping: {config.websocket_ping_interval}s")
        print(f"   ✅ Keep-alive: {config.keep_alive_timeout}s")
        print(f"   ✅ Graceful timeout: {config.graceful_timeout}s")
        
        print("\n✅ Hypercorn configuration successful!\n")
        return True
        
    except Exception as e:
        print(f"\n❌ Hypercorn config error: {e}\n")
        return False


async def test_app_startup():
    """Test FastAPI app can be created."""
    print("🧪 Testing FastAPI app...")
    
    try:
        from main import app
        
        print(f"   ✅ App title: {app.title}")
        print(f"   ✅ App version: {app.version}")
        print(f"   ✅ Routes registered: {len(app.routes)}")
        
        # Check for key routes
        route_paths = [route.path for route in app.routes]
        
        assert "/api/v1/backend/health" in route_paths
        print("   ✅ Health route registered")
        
        assert "/api/v1/backend/auth/login" in route_paths
        print("   ✅ Auth routes registered")
        
        assert "/api/v1/backend/students" in route_paths
        print("   ✅ Student routes registered")
        
        assert "/api/v1/backend/ws/events" in route_paths
        print("   ✅ WebSocket route registered")
        
        print("\n✅ FastAPI app configuration successful!\n")
        return True
        
    except Exception as e:
        print(f"\n❌ App startup error: {e}\n")
        return False


async def main():
    """Run all tests."""
    print("=" * 60)
    print("🚀 Hypercorn 0.18.0 + SQLAlchemy Verification")
    print("=" * 60)
    print()
    
    results = []
    
    # Run tests
    results.append(await test_imports())
    results.append(await test_database())
    results.append(await test_hypercorn_config())
    results.append(await test_app_startup())
    
    # Summary
    print("=" * 60)
    print("📊 Test Summary")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"   Tests passed: {passed}/{total}")
    
    if passed == total:
        print("\n   ✅ ALL TESTS PASSED!")
        print("\n   🎉 Backend is ready to start!")
        print("\n   Run: python run.py")
        print()
        return 0
    else:
        print("\n   ❌ SOME TESTS FAILED!")
        print("\n   Please install missing dependencies:")
        print("   pip install -r requirements.txt")
        print()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
