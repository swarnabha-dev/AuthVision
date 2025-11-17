"""Check Model Server Database Path and Content"""
import sqlite3
from pathlib import Path

# Model server default path
db_path = Path("model_server/storage/enrollments.db")

print("=" * 70)
print("MODEL SERVER DATABASE CHECK")
print("=" * 70)

print(f"\n📍 Database Path: {db_path.resolve()}")
print(f"   Exists: {db_path.exists()}")

if not db_path.exists():
    print("❌ Database file not found!")
    exit(1)

# Connect and check
conn = sqlite3.connect(str(db_path))

print("\n" + "=" * 70)
print("ENROLLMENTS TABLE")
print("=" * 70)

# Get all enrollments
cursor = conn.execute("""
    SELECT student_id, view, embedding_dim, created_at 
    FROM enrollments 
    ORDER BY student_id, view
""")
enrollments = cursor.fetchall()

print(f"\nTotal enrollments: {len(enrollments)}")
print("-" * 70)

if enrollments:
    print(f"{'Student ID':<15} {'View':<15} {'Dim':<10} {'Created':<30}")
    print("-" * 70)
    for e in enrollments:
        print(f"{e[0]:<15} {e[1]:<15} {e[2]:<10} {e[3]:<30}")

# Get unique students
cursor = conn.execute("SELECT DISTINCT student_id FROM enrollments")
students = cursor.fetchall()

print("\n" + "=" * 70)
print(f"UNIQUE STUDENTS: {len(students)}")
print("=" * 70)

for s in students:
    student_id = s[0]
    
    # Count enrollments per student
    cursor = conn.execute(
        "SELECT COUNT(*) FROM enrollments WHERE student_id = ?", 
        (student_id,)
    )
    count = cursor.fetchone()[0]
    
    print(f"  ✅ {student_id} ({count} face embeddings)")

# Check table schema
print("\n" + "=" * 70)
print("TABLE SCHEMA")
print("=" * 70)

cursor = conn.execute("PRAGMA table_info(enrollments)")
columns = cursor.fetchall()

print(f"\n{'Column':<20} {'Type':<15} {'Not Null':<10} {'PK':<5}")
print("-" * 70)
for col in columns:
    print(f"{col[1]:<20} {col[2]:<15} {col[3]:<10} {col[5]:<5}")

conn.close()

print("\n" + "=" * 70)
print("✅ Model Server using: model_server/storage/enrollments.db")
print("=" * 70)
