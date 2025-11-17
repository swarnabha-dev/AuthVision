"""
Quick verification script to check if architecture fix is ready.
Run this BEFORE migration to see current state.
"""
import sqlite3
from pathlib import Path
import sys

def check_file(filepath: str, should_exist: bool = True) -> bool:
    """Check if file exists."""
    path = Path(filepath)
    exists = path.exists()
    
    if should_exist:
        if exists:
            print(f"   ✅ {filepath} - Found")
            return True
        else:
            print(f"   ❌ {filepath} - NOT FOUND")
            return False
    else:
        if not exists:
            print(f"   ✅ {filepath} - Not present (correct)")
            return True
        else:
            print(f"   ⚠️  {filepath} - Still exists")
            return False


def check_table(db_path: str, table_name: str, should_exist: bool = True) -> bool:
    """Check if table exists in database."""
    if not Path(db_path).exists():
        print(f"   ⚠️  Database not found: {db_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name=?
    """, (table_name,))
    
    exists = cursor.fetchone() is not None
    conn.close()
    
    if should_exist:
        if exists:
            print(f"   ✅ Table '{table_name}' exists")
            return True
        else:
            print(f"   ❌ Table '{table_name}' NOT FOUND")
            return False
    else:
        if not exists:
            print(f"   ✅ Table '{table_name}' removed (correct)")
            return True
        else:
            print(f"   ⚠️  Table '{table_name}' still exists (will be removed)")
            return False


def check_student_exists(db_path: str, student_id: str) -> bool:
    """Check if student exists in database."""
    if not Path(db_path).exists():
        print(f"   ⚠️  Database not found: {db_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT student_id, first_name, last_name FROM students WHERE student_id = ?", (student_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        print(f"   ✅ Student {student_id} exists: {result[1]} {result[2] or ''}")
        return True
    else:
        print(f"   ❌ Student {student_id} NOT FOUND (will be added)")
        return False


def check_model_server_enrollments(db_path: str) -> int:
    """Check enrollments in model server."""
    if not Path(db_path).exists():
        print(f"   ⚠️  Database not found: {db_path}")
        return 0
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT DISTINCT student_id, COUNT(*) as views FROM enrollments GROUP BY student_id")
    enrollments = cursor.fetchall()
    conn.close()
    
    print(f"   📊 Model server enrollments: {len(enrollments)} students")
    for student_id, views in enrollments:
        print(f"      - {student_id}: {views} views")
    
    return len(enrollments)


def main():
    print("=" * 80)
    print("🔍 ARCHITECTURE FIX - PRE-MIGRATION VERIFICATION")
    print("=" * 80)
    
    all_good = True
    
    # Check files
    print("\n1️⃣  Checking Modified Code Files...")
    check_file("main_backend/app/models.py")
    check_file("main_backend/app/schemas.py")
    check_file("main_backend/app/routes/student_routes.py")
    check_file("main_backend/migrate_remove_enrollments.py")
    
    # Check databases
    print("\n2️⃣  Checking Main Backend Database...")
    main_db = "main_backend/storage/main_backend.db"
    check_file(main_db)
    
    if Path(main_db).exists():
        check_table(main_db, "students", should_exist=True)
        check_table(main_db, "student_photos", should_exist=True)
        check_table(main_db, "attendance_events", should_exist=True)
        
        # This should be removed after migration
        enrollments_exist = check_table(main_db, "enrollments", should_exist=False)
        if enrollments_exist:
            all_good = False
        
        # Check if student exists
        student_exists = check_student_exists(main_db, "202200248")
        if not student_exists:
            all_good = False
    
    print("\n3️⃣  Checking Model Server Database...")
    model_db = "model_server/storage/enrollments.db"
    check_file(model_db)
    
    if Path(model_db).exists():
        check_table(model_db, "enrollments", should_exist=True)
        check_table(model_db, "users", should_exist=True)
        enrollment_count = check_model_server_enrollments(model_db)
        if enrollment_count == 0:
            print("   ⚠️  No enrollments found in model server!")
            all_good = False
    
    # Summary
    print("\n" + "=" * 80)
    if all_good:
        print("✅ ALL CHECKS PASSED - Ready for migration!")
        print("=" * 80)
        print("\n📝 Next Steps:")
        print("   1. Run migration: python main_backend\\migrate_remove_enrollments.py")
        print("   2. Restart backend: python main.py")
        print("   3. Test recognition: python main_backend\\tests\\interactive_test.py")
    else:
        print("⚠️  ISSUES FOUND - Migration will fix them")
        print("=" * 80)
        print("\n📝 What Will Be Fixed:")
        print("   ✅ 'enrollments' table will be dropped from main_backend")
        print("   ✅ Student 202200248 will be added to students table")
        print("\n🚀 Ready to run migration!")
        print("   Command: python main_backend\\migrate_remove_enrollments.py")


if __name__ == "__main__":
    main()
