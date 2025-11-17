"""
Migration script to:
1. Drop the enrollments table (embeddings stored in model_server only)
2. Add missing student 202200248 from model_server to main_backend
"""
import sqlite3
import asyncio
from pathlib import Path
from datetime import datetime
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from app.database import AsyncSessionLocal
from app.models import Student
from app.config import settings
from sqlalchemy import select, text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def drop_enrollments_table():
    """Drop the enrollments table from main_backend database."""
    # Get DB path from config
    db_path = settings.db_path
    
    if not db_path.exists():
        logger.error(f"❌ Database not found: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='enrollments'
        """)
        
        if cursor.fetchone():
            logger.info("📋 Dropping 'enrollments' table...")
            cursor.execute("DROP TABLE enrollments")
            conn.commit()
            logger.info("✅ 'enrollments' table dropped successfully")
        else:
            logger.info("ℹ️  'enrollments' table does not exist (already removed)")
        
        conn.close()
        return True
    
    except Exception as e:
        logger.error(f"❌ Error dropping enrollments table: {e}")
        return False


async def add_missing_student():
    """Add student 202200248 from model_server to main_backend."""
    async with AsyncSessionLocal() as db:
        try:
            # Check if student already exists
            result = await db.execute(
                select(Student).where(Student.student_id == "202200248")
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                logger.info(f"ℹ️  Student 202200248 already exists: {existing.first_name}")
                return True
            
            # Add student
            student = Student(
                student_id="202200248",
                first_name="Student",  # Update with actual name if known
                last_name="202200248",
                email=None,
                phone=None,
                student_metadata=None,
                created_at=datetime.now()
            )
            
            db.add(student)
            await db.commit()
            await db.refresh(student)
            
            logger.info(f"✅ Student 202200248 added successfully")
            return True
        
        except Exception as e:
            logger.error(f"❌ Error adding student: {e}")
            return False


async def verify_students():
    """Verify students in main_backend database."""
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(select(Student))
            students = result.scalars().all()
            
            logger.info(f"\n📊 Total students in main_backend: {len(students)}")
            for student in students:
                logger.info(f"   - {student.student_id}: {student.first_name} {student.last_name or ''}")
            
            return True
        
        except Exception as e:
            logger.error(f"❌ Error verifying students: {e}")
            return False


def check_model_server_enrollments():
    """Check enrollments in model_server database."""
    db_path = Path("model_server/storage/enrollments.db")
    
    if not db_path.exists():
        logger.warning(f"⚠️  Model server database not found: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT DISTINCT student_id, COUNT(*) as views 
            FROM enrollments 
            GROUP BY student_id
        """)
        
        enrollments = cursor.fetchall()
        
        logger.info(f"\n📊 Model server enrollments: {len(enrollments)} students")
        for student_id, views in enrollments:
            logger.info(f"   - {student_id}: {views} views enrolled")
        
        conn.close()
    
    except Exception as e:
        logger.error(f"❌ Error checking model server enrollments: {e}")


async def main():
    """Run migration."""
    logger.info("=" * 80)
    logger.info("🔧 MIGRATION: Remove Enrollments Table & Add Missing Student")
    logger.info("=" * 80)
    
    # Step 1: Check model server enrollments
    logger.info("\n1️⃣  Checking model server enrollments...")
    check_model_server_enrollments()
    
    # Step 2: Drop enrollments table
    logger.info("\n2️⃣  Dropping enrollments table from main_backend...")
    if not drop_enrollments_table():
        logger.error("❌ Failed to drop enrollments table")
        return
    
    # Step 3: Add missing student
    logger.info("\n3️⃣  Adding missing student 202200248...")
    if not await add_missing_student():
        logger.error("❌ Failed to add student")
        return
    
    # Step 4: Verify students
    logger.info("\n4️⃣  Verifying students in main_backend...")
    await verify_students()
    
    logger.info("\n" + "=" * 80)
    logger.info("✅ MIGRATION COMPLETED SUCCESSFULLY")
    logger.info("=" * 80)
    logger.info("\n📝 Summary:")
    logger.info("   - Embeddings are now ONLY stored in model_server DB")
    logger.info("   - Main backend only stores student info + attendance")
    logger.info("   - Student 202200248 is now in main_backend")
    logger.info("   - Recognition should now work end-to-end!")
    logger.info("\n🚀 Next steps:")
    logger.info("   1. Restart main backend")
    logger.info("   2. Test recognition with interactive_test.py")
    logger.info("   3. Verify WebSocket events show student name")


if __name__ == "__main__":
    asyncio.run(main())
