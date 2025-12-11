from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Any
from ..services.db import get_db
from ..services import models as m
from ..services.auth import require_role, get_current_user
import logging

LOG = logging.getLogger("main_backend.reports")

router = APIRouter(prefix="/reports")

@router.get("/subject/{subject_identifier}/summary")
def subject_attendance_summary(subject_identifier: str, db: Session = Depends(get_db), user = Depends(require_role('faculty', 'admin'))):
    """
    Get attendance summary for a specific subject.
    Identifier can be Subject Code (str) directly.
    """
    # New schema uses code as PK.
    subject = db.query(m.Subject).filter(m.Subject.code == subject_identifier).first()

    if not subject:
        raise HTTPException(status_code=404, detail=f"Subject not found with code '{subject_identifier}'")

    # 1. Calculate total sessions for this subject
    total_classes = db.query(m.AttendanceSession).filter(
        m.AttendanceSession.subject_code == subject.code
    ).count()

    # 2. Get eligible students
    students_query = db.query(m.Student).filter(
        m.Student.department == subject.department,
        m.Student.semester == subject.semester
    )
    all_students = students_query.all()
    
    report = []
    
    for s in all_students:
        # Count sessions where student was present
        # Join Record -> Session
        present_count = db.query(m.AttendanceRecord).join(m.AttendanceSession).filter(
            m.AttendanceSession.subject_code == subject.code,
            m.AttendanceRecord.student_reg == s.reg_no,
            m.AttendanceRecord.status == m.AttendanceStatus.PRESENT
        ).count()
        
        percentage = 0.0
        if total_classes > 0:
            percentage = (present_count / total_classes) * 100.0
            
        report.append({
            "reg_no": s.reg_no,
            "name": s.name,
            "section": s.section,
            "present_count": present_count,
            "total_classes": total_classes,
            "percentage": round(percentage, 2)
        })
        
    return {
        "subject": {
            "name": subject.name,
            "code": subject.code,
            "department": subject.department,
            "semester": subject.semester
        },
        "total_classes": total_classes,
        "student_stats": report
    }


@router.get("/student/{reg_no}/attendance")
def student_attendance_report(reg_no: str, db: Session = Depends(get_db), user = Depends(get_current_user)):
    """
    Get attendance report for a specific student across all their subjects.
    """
    if getattr(user, 'role', '') == 'student' and getattr(user, 'username', '') != reg_no:
        raise HTTPException(status_code=403, detail="Cannot view other student's attendance")
        
    student = db.query(m.Student).filter(m.Student.reg_no == reg_no).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Find subjects applicable to this student (Dept + Semester)
    subjects = db.query(m.Subject).filter(
        m.Subject.department == student.department,
        m.Subject.semester == student.semester
    ).all()
    
    stats = []
    
    for sub in subjects:
        # Total classes for subject
        total_classes = db.query(m.AttendanceSession).filter(
            m.AttendanceSession.subject_code == sub.code
        ).count()
        
        # Present count
        present_count = db.query(m.AttendanceRecord).join(m.AttendanceSession).filter(
            m.AttendanceSession.subject_code == sub.code,
            m.AttendanceRecord.student_reg == reg_no,
            m.AttendanceRecord.status == m.AttendanceStatus.PRESENT
        ).count()
        
        percentage = 0.0
        if total_classes > 0:
            percentage = (present_count / total_classes) * 100.0
            
        stats.append({
            "subject_code": sub.code,
            "subject_name": sub.name,
            "present_classes": present_count,
            "total_classes": total_classes,
            "percentage": round(percentage, 2)
        })

    return {
        "student": {
            "reg_no": student.reg_no,
            "name": student.name,
            "department": student.department,
            "semester": student.semester,
            "section": student.section
        },
        "attendance": stats
    }
