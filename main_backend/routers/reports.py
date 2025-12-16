from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Any
from ..services.db import get_db
from ..services import models as m
from ..services.auth import require_role, get_current_user
import logging
import csv
import io
import os
import datetime
from jinja2 import Environment, FileSystemLoader
import pdfkit

LOG = logging.getLogger("main_backend.reports")

router = APIRouter(prefix="/reports")

# Setup Jinja2
TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
try:
    jinja_env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
except Exception as e:
    LOG.error("Failed to load templates dir: %s", e)
    jinja_env = None

# Helper to find wkhtmltopdf
def get_wkhtmltopdf_config():
    """Try to find wkhtmltopdf binary and return configuration."""
    possible_paths = [
        r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe",
        r"C:\Program Files (x86)\wkhtmltopdf\bin\wkhtmltopdf.exe",
        "/usr/bin/wkhtmltopdf",
        "/usr/local/bin/wkhtmltopdf"
    ]
    path = None
    # Check if on path
    try:
        import shutil
        if shutil.which("wkhtmltopdf"):
            return None # pdfkit finds it automatically if in PATH
    except:
        pass
        
    for p in possible_paths:
        if os.path.exists(p):
            path = p
            break
            
    if path:
        return pdfkit.configuration(wkhtmltopdf=path)
    return None # Hope it's in PATH or let pdfkit raise error if not found


def _fetch_subject_data(subject_code: str, db: Session):
    subject = db.query(m.Subject).filter(m.Subject.code == subject_code).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    total_classes = db.query(m.AttendanceSession).filter(
        m.AttendanceSession.subject_code == subject.code
    ).count()

    students = db.query(m.Student).filter(
        m.Student.department == subject.department,
        m.Student.semester == subject.semester
    ).all()
    
    student_list = []
    for s in students:
        present = db.query(m.AttendanceRecord).join(m.AttendanceSession).filter(
            m.AttendanceSession.subject_code == subject.code,
            m.AttendanceRecord.student_reg == s.reg_no,
            m.AttendanceRecord.status == m.AttendanceStatus.PRESENT
        ).count()
        
        pct = (present / total_classes * 100.0) if total_classes > 0 else 0.0
        student_list.append({
            "reg_no": s.reg_no,
            "name": s.name,
            "section": s.section,
            "present_count": present,
            "total_classes": total_classes,
            "percentage": round(pct, 2)
        })
        
    return {
        "subject": {
            "name": subject.name,
            "code": subject.code,
            "department": subject.department,
            "semester": subject.semester
        },
        "total_classes": total_classes,
        "student_stats": student_list,
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

def _fetch_student_data(reg_no: str, db: Session):
    student = db.query(m.Student).filter(m.Student.reg_no == reg_no).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    subjects = db.query(m.Subject).filter(
        m.Subject.department == student.department,
        m.Subject.semester == student.semester
    ).all()
    
    stats = []
    for sub in subjects:
        total = db.query(m.AttendanceSession).filter(m.AttendanceSession.subject_code == sub.code).count()
        present = db.query(m.AttendanceRecord).join(m.AttendanceSession).filter(
            m.AttendanceSession.subject_code == sub.code,
            m.AttendanceRecord.student_reg == reg_no,
            m.AttendanceRecord.status == m.AttendanceStatus.PRESENT
        ).count()
        
        pct = (present / total * 100.0) if total > 0 else 0.0
        stats.append({
            "subject_code": sub.code,
            "subject_name": sub.name,
            "present_classes": present,
            "total_classes": total,
            "percentage": round(pct, 2)
        })
        
    return {
        "student": {
            "reg_no": student.reg_no,
            "name": student.name,
            "department": student.department,
            "semester": student.semester,
            "section": student.section
        },
        "attendance": stats,
         "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


@router.get("/subject/{subject_identifier}/summary")
def subject_attendance_summary(subject_identifier: str, db: Session = Depends(get_db), user = Depends(require_role('faculty', 'admin'))):
    return _fetch_subject_data(subject_identifier, db)


@router.get("/subject/{subject_identifier}/download/csv")
def download_subject_csv(subject_identifier: str, db: Session = Depends(get_db), user = Depends(require_role('faculty', 'admin'))):
    data = _fetch_subject_data(subject_identifier, db)
    
    # Generate CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Registration No", "Name", "Section", "Present Sessions", "Percentage"])
    
    for s in data['student_stats']:
        writer.writerow([s['reg_no'], s['name'], s['section'], s['present_count'], f"{s['percentage']}%"])
        
    output.seek(0)
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=attendance_{subject_identifier}.csv"}
    )

@router.get("/subject/{subject_identifier}/download/pdf")
def download_subject_pdf(subject_identifier: str, db: Session = Depends(get_db), user = Depends(require_role('faculty', 'admin'))):
    data = _fetch_subject_data(subject_identifier, db)
    if not jinja_env:
        raise HTTPException(500, "Template environment not configured")
        
    template = jinja_env.get_template("report_subject.html")
    html_content = template.render(
        subject=data['subject'],
        total_classes=data['total_classes'],
        students=data['student_stats'],
        generated_at=data['generated_at']
    )
    
    config = get_wkhtmltopdf_config()
    try:
        pdf = pdfkit.from_string(html_content, False, configuration=config)
    except OSError:
        url = "https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6-1/wkhtmltox-0.12.6-1.msvc2015-win64.exe"
        raise HTTPException(500, f"wkhtmltopdf not found. Please install it from: {url}")
        
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=attendance_{subject_identifier}.pdf"}
    )


@router.get("/student/{reg_no}/attendance")
def student_attendance_report(reg_no: str, db: Session = Depends(get_db), user = Depends(get_current_user)):
    if getattr(user, 'role', '') == 'student' and getattr(user, 'username', '') != reg_no:
        raise HTTPException(status_code=403, detail="Forbidden")
    return _fetch_student_data(reg_no, db)


@router.get("/student/{reg_no}/download/csv")
def download_student_csv(reg_no: str, db: Session = Depends(get_db), user = Depends(get_current_user)):
    if getattr(user, 'role', '') == 'student' and getattr(user, 'username', '') != reg_no:
        raise HTTPException(status_code=403, detail="Forbidden")
        
    data = _fetch_student_data(reg_no, db)
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Subject Code", "Subject Name", "Total Classes", "Present Classes", "Percentage"])
    
    for row in data['attendance']:
        writer.writerow([row['subject_code'], row['subject_name'], row['total_classes'], row['present_classes'], f"{row['percentage']}%"])
        
    output.seek(0)
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=report_{reg_no}.csv"}
    )

@router.get("/student/{reg_no}/download/pdf")
def download_student_pdf(reg_no: str, db: Session = Depends(get_db), user = Depends(get_current_user)):
    if getattr(user, 'role', '') == 'student' and getattr(user, 'username', '') != reg_no:
        raise HTTPException(status_code=403, detail="Forbidden")
        
    data = _fetch_student_data(reg_no, db)
    if not jinja_env:
        raise HTTPException(500, "Templates not loaded")
        
    template = jinja_env.get_template("report_student.html")
    html_content = template.render(
        student=data['student'],
        subjects=data['attendance'],
        generated_at=data['generated_at']
    )
    
    config = get_wkhtmltopdf_config()
    try:
        pdf = pdfkit.from_string(html_content, False, configuration=config)
    except OSError:
         url = "https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6-1/wkhtmltox-0.12.6-1.msvc2015-win64.exe"
         raise HTTPException(500, f"wkhtmltopdf not found. Please install it from: {url}")
         
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=report_{reg_no}.pdf"}
    )
