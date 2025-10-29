"""
Device registration routes.
"""

from fastapi import APIRouter, Depends

from app.deps import AttendanceService, get_attendance_service
from app.models.attendance_models import DeviceRegisterRequest, DeviceRegisterResponse

router = APIRouter(prefix="/devices", tags=["devices"])


@router.post("/register", response_model=DeviceRegisterResponse)
def register_device(
    request: DeviceRegisterRequest,
    attendance_service: AttendanceService = Depends(get_attendance_service),
) -> DeviceRegisterResponse:
    """Register an edge device.

    Args:
        request: Device registration request
        attendance_service: Attendance service (injected)

    Returns:
        DeviceRegisterResponse with registration details
    """
    device_id, status, registered_at = attendance_service.register_device(
        device_id=request.device_id, model=request.model, location=request.location
    )
    return DeviceRegisterResponse(
        device_id=device_id, status=status, registered_at=registered_at
    )
