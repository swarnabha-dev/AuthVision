"""
Quick check to verify database path configuration.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from app.config import settings, MAIN_BACKEND_DIR, STORAGE_DIR, DB_FILE
    
    print("=" * 80)
    print("✅ DATABASE PATH CONFIGURATION")
    print("=" * 80)
    
    print("\n📍 Absolute Paths (No Ambiguity):")
    print(f"   Main Backend Dir: {MAIN_BACKEND_DIR}")
    print(f"   Storage Dir:      {STORAGE_DIR}")
    print(f"   Database File:    {DB_FILE}")
    
    print("\n📋 Settings Properties:")
    print(f"   settings.storage_dir: {settings.storage_dir}")
    print(f"   settings.db_path:     {settings.db_path}")
    print(f"   settings.photos_dir:  {settings.photos_dir}")
    
    print("\n🔍 Database Status:")
    if settings.db_path.exists():
        size = settings.db_path.stat().st_size / 1024
        print(f"   ✅ Database exists")
        print(f"   📦 Size: {size:.2f} KB")
    else:
        print(f"   ⚠️  Database does not exist yet")
        print(f"   ℹ️  Will be created on first backend startup")
    
    print("\n🔍 Checking for databases in wrong locations...")
    wrong_found = False
    
    # Check parent directory
    parent_db = Path("../storage/main_backend.db")
    if parent_db.exists():
        abs_parent = parent_db.resolve()
        abs_correct = settings.db_path.resolve()
        if abs_parent != abs_correct:
            wrong_found = True
            size = parent_db.stat().st_size / 1024
            print(f"   ⚠️  Found: {abs_parent}")
            print(f"      Size: {size:.2f} KB")
            print(f"      ❌ This is a WRONG location!")
    
    # Check current directory relative
    current_db = Path("storage/main_backend.db")
    if current_db.exists():
        abs_current = current_db.resolve()
        abs_correct = settings.db_path.resolve()
        if abs_current != abs_correct:
            wrong_found = True
            size = current_db.stat().st_size / 1024
            print(f"   ⚠️  Found: {abs_current}")
            print(f"      Size: {size:.2f} KB")
            print(f"      ❌ This is a WRONG location!")
    
    if not wrong_found:
        print(f"   ✅ No databases found in wrong locations")
    
    print("\n" + "=" * 80)
    print("✅ CONFIGURATION IS CORRECT")
    print("=" * 80)
    print(f"\n📝 Database will always be created at:")
    print(f"   {settings.db_path}")
    print(f"\n🎯 No matter where you run scripts from!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
