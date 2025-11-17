import sqlite3

# Check Model Server DB (enrollments)
print("=" * 70)
print("MODEL SERVER DATABASE (enrollments.db)")
print("=" * 70)
conn = sqlite3.connect('model_server/storage/enrollments.db')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print(f"Tables: {[t[0] for t in tables]}")
cursor.execute("SELECT COUNT(*) FROM enrollments")
enrollments_count = cursor.fetchone()[0]
print(f"Enrolled students (with embeddings): {enrollments_count}")
if enrollments_count > 0:
    cursor.execute("SELECT student_id FROM enrollments LIMIT 5")
    for row in cursor.fetchall():
        print(f"  - {row[0]}")
conn.close()

print()

# Check Main Backend DB (student info)
print("=" * 70)
print("MAIN BACKEND DATABASE (main_backend.db)")
print("=" * 70)
conn = sqlite3.connect('main_backend/storage/main_backend.db')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print(f"Tables: {[t[0] for t in tables]}")
cursor.execute("SELECT COUNT(*) FROM students")
students_count = cursor.fetchone()[0]
print(f"Students (basic info): {students_count}")
if students_count > 0:
    cursor.execute("SELECT student_id, first_name, last_name FROM students LIMIT 5")
    for row in cursor.fetchall():
        print(f"  - {row[0]}: {row[1]} {row[2]}")
cursor.execute("SELECT COUNT(*) FROM attendance_events")
attendance_count = cursor.fetchone()[0]
print(f"Attendance events: {attendance_count}")
conn.close()

print()
print("=" * 70)
print("ARCHITECTURE:")
print("=" * 70)
print("✅ Model Server DB: Stores face embeddings (enrollments)")
print("✅ Main Backend DB: Stores student info + attendance events")
print("✅ Recognition flow: Backend → Model Server (match) → Backend (save attendance)")
