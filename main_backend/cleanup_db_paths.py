"""
Database Path Cleanup Script
Remove any databases created in wrong locations and verify correct path.
"""
import sys
from pathlib import Path
import shutil

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.config import settings, STORAGE_DIR, DB_FILE

def main():
    """Check and clean up database paths."""
    print("=" * 80)
    print("🧹 DATABASE PATH CLEANUP")
    print("=" * 80)
    
    print("\n1️⃣  Configuration:")
    print(f"   Main Backend Dir: {settings.storage_dir.parent}")
    print(f"   Storage Dir: {settings.storage_dir}")
    print(f"   Database File: {settings.db_path}")
    print(f"   Photos Dir: {settings.photos_dir}")
    print(f"   Frames Cache: {settings.frames_cache_dir}")
    
    # Correct path (should exist)
    correct_db = settings.db_path
    print(f"\n2️⃣  Correct Database Location:")
    print(f"   ✅ {correct_db}")
    if correct_db.exists():
        size = correct_db.stat().st_size / 1024
        print(f"   📦 Size: {size:.2f} KB")
        print(f"   ✅ File exists")
    else:
        print(f"   ⚠️  File does not exist (will be created on startup)")
    
    # Wrong paths to check and remove
    wrong_paths = [
        Path("storage/main_backend.db"),  # Parent directory
        Path("../storage/main_backend.db"),  # Relative parent
        Path("./storage/main_backend.db"),  # Relative current
    ]
    
    print(f"\n3️⃣  Checking for databases in wrong locations...")
    found_wrong = False
    
    for wrong_path in wrong_paths:
        if wrong_path.exists() and wrong_path.resolve() != correct_db.resolve():
            found_wrong = True
            size = wrong_path.stat().st_size / 1024
            print(f"\n   ⚠️  Found database in wrong location:")
            print(f"      Path: {wrong_path.resolve()}")
            print(f"      Size: {size:.2f} KB")
            
            # Ask to delete
            response = input(f"\n   ❓ Delete this file? (y/n): ").strip().lower()
            if response == 'y':
                try:
                    wrong_path.unlink()
                    print(f"   ✅ Deleted: {wrong_path.resolve()}")
                except Exception as e:
                    print(f"   ❌ Error deleting: {e}")
            else:
                print(f"   ⏭️  Skipped")
    
    if not found_wrong:
        print("   ✅ No databases found in wrong locations")
    
    # Check parent storage directory
    parent_storage = Path("storage")
    if parent_storage.exists() and parent_storage.resolve() != STORAGE_DIR.resolve():
        print(f"\n4️⃣  Found storage directory in wrong location:")
        print(f"   Path: {parent_storage.resolve()}")
        
        # List contents
        contents = list(parent_storage.iterdir())
        if contents:
            print(f"   Contents:")
            for item in contents:
                print(f"      - {item.name}")
            
            response = input(f"\n   ❓ Delete entire directory? (y/n): ").strip().lower()
            if response == 'y':
                try:
                    shutil.rmtree(parent_storage)
                    print(f"   ✅ Deleted: {parent_storage.resolve()}")
                except Exception as e:
                    print(f"   ❌ Error deleting: {e}")
            else:
                print(f"   ⏭️  Skipped")
        else:
            print("   📂 Directory is empty")
            try:
                parent_storage.rmdir()
                print(f"   ✅ Removed empty directory")
            except Exception as e:
                print(f"   ⚠️  Could not remove: {e}")
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    print(f"\n✅ Correct database path: {correct_db}")
    print(f"\n📝 All database operations will use this path")
    print(f"\n🔧 Configuration is centralized in: main_backend/app/config.py")
    print(f"\n📍 Paths are now absolute (no ambiguity)")
    
    print("\n" + "=" * 80)
    print("✅ CLEANUP COMPLETED")
    print("=" * 80)
    
    print("\n🚀 Next steps:")
    print("   1. Start backend: python main.py")
    print("   2. Database will be created at correct location")
    print("   3. Run migration: python migrate_remove_enrollments.py")
    print("   4. Test with: python tests/interactive_test.py")


if __name__ == "__main__":
    main()
