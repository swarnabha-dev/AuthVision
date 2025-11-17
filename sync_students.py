"""
Quick fix script to add missing student record to main backend database.
This syncs the student that exists in model_server but not in main_backend.
"""
import sqlite3
from datetime import datetime
import json

# Get student ID from model server
print("Checking model server enrollments...")
conn_model = sqlite3.connect('model_server/storage/enrollments.db')
cursor_model = conn_model.cursor()
cursor_model.execute('SELECT DISTINCT student_id FROM enrollments')
enrolled_students = [row[0] for row in cursor_model.fetchall()]
conn_model.close()

print(f"Students enrolled in model server: {enrolled_students}")

if not enrolled_students:
    print("❌ No students found in model server. Nothing to sync.")
    exit(0)

# Check which students are missing from main backend
print("\nChecking main backend students...")
conn_backend = sqlite3.connect('main_backend/storage/main_backend.db')
cursor_backend = conn_backend.cursor()
cursor_backend.execute('SELECT student_id FROM students')
backend_students = [row[0] for row in cursor_backend.fetchall()]

print(f"Students in main backend: {backend_students if backend_students else 'None'}")

# Find missing students
missing_students = [s for s in enrolled_students if s not in backend_students]

if not missing_students:
    print("\n✅ All students are synced between databases!")
    conn_backend.close()
    exit(0)

print(f"\n⚠️ Found {len(missing_students)} student(s) missing from main backend:")
for sid in missing_students:
    print(f"  - {sid}")

# Add missing students
print("\n" + "="*70)
print("ADDING MISSING STUDENTS TO MAIN BACKEND")
print("="*70)

for student_id in missing_students:
    print(f"\nProcessing student: {student_id}")
    
    # Extract info from student ID
    # Format: 202200248 (year: 2022, student: 00248)
    year = student_id[:4] if len(student_id) >= 4 else "2025"
    
    # Ask for student details
    print(f"\nEnter details for student {student_id}:")
    first_name = input(f"  First name (default: Student): ").strip() or "Student"
    last_name = input(f"  Last name (default: {student_id}): ").strip() or student_id
    email = input(f"  Email (default: {student_id}@school.edu): ").strip() or f"{student_id}@school.edu"
    phone = input(f"  Phone (default: blank): ").strip() or None
    department = input(f"  Department (default: CS): ").strip() or "CS"
    
    # Create metadata
    metadata = {
        "department": department,
        "year": year,
        "synced_from_model_server": True,
        "sync_date": datetime.now().isoformat()
    }
    
    # Insert into database
    try:
        cursor_backend.execute("""
            INSERT INTO students (
                student_id, first_name, last_name, email, phone, 
                student_metadata, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            student_id,
            first_name,
            last_name,
            email,
            phone,
            json.dumps(metadata),
            datetime.now().isoformat()
        ))
        
        conn_backend.commit()
        print(f"  ✅ Added: {student_id} - {first_name} {last_name}")
    
    except sqlite3.IntegrityError as e:
        print(f"  ❌ Error: {e}")
        continue

conn_backend.close()

print("\n" + "="*70)
print("VERIFICATION")
print("="*70)

# Verify
conn_backend = sqlite3.connect('main_backend/storage/main_backend.db')
cursor_backend = conn_backend.cursor()
cursor_backend.execute('SELECT student_id, first_name, last_name FROM students')
all_students = cursor_backend.fetchall()
conn_backend.close()

print(f"\nTotal students in main backend: {len(all_students)}")
for sid, fname, lname in all_students:
    print(f"  ✅ {sid}: {fname} {lname}")

print("\n" + "="*70)
print("✅ SYNC COMPLETE!")
print("="*70)
print("\nNext steps:")
print("1. Restart the recognition monitor (Option 11)")
print("2. Stand in front of camera")
print("3. Recognition events should now show with student names!")
