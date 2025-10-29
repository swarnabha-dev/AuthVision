"""
Attendance management routes.
"""

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.deps import AttendanceService, get_attendance_service
from app.models.attendance_models import (
    AttendanceQueryResponse,
    AttendanceRecord,
    EnrollResponse,
)

router = APIRouter(prefix="/attendance", tags=["attendance"])


@router.post("/enroll", response_model=EnrollResponse)
async def enroll_student(
    camera_id: str = Form(...),
    student_id: str = Form(...),
    image: UploadFile = File(...),
    attendance_service: AttendanceService = Depends(get_attendance_service),
) -> EnrollResponse:
    """Enroll a student with face image.

    Args:
        camera_id: Camera identifier (form field)
        student_id: Student identifier (form field)
        image: Face image file (multipart)
        attendance_service: Attendance service (injected)

    Returns:
        EnrollResponse with enrollment status
    """
    image_bytes = await image.read()
    student_id_result, enrolled, embedding_id = attendance_service.enroll_student(
        camera_id=camera_id, student_id=student_id, image_bytes=image_bytes
    )
    return EnrollResponse(student_id=student_id_result, enrolled=enrolled, embedding_id=embedding_id)


@router.get("", response_model=AttendanceQueryResponse)
def query_attendance(
    camera_id: str,
    date: str,
    attendance_service: AttendanceService = Depends(get_attendance_service),
) -> AttendanceQueryResponse:
    """Query attendance records.

    Args:
        camera_id: Camera identifier (query param)
        date: Query date in YYYY-MM-DD format (query param)
        attendance_service: Attendance service (injected)

    Returns:
        AttendanceQueryResponse with records
    """
    records_raw = attendance_service.query_attendance(camera_id=camera_id, date=date)
    records = [
        AttendanceRecord(
            student_id=r["student_id"],
            start_time=r["start_time"],
            end_time=r.get("end_time"),
            confidence=r["confidence"],
            camera_id=r["camera_id"],
        )
        for r in records_raw
    ]
    return AttendanceQueryResponse(camera_id=camera_id, date=date, records=records)
