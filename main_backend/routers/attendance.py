
from fastapi import APIRouter, Depends, HTTPException, Form, WebSocket, WebSocketDisconnect
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from ..services.db import get_db, engine, Base
from ..services import models as m
from ..services.attendance import AttendanceManager
from .. import config
from ..services.auth import require_role, get_current_user
from ..services.ws_manager import manager as ws_manager
import logging

LOG = logging.getLogger("main_backend.attendance")

# Base.metadata.create_all(bind=engine) # moved to main startup or handled by migrations

router = APIRouter(prefix="/attendance")


@router.post('/start')
def start_attendance_session(
    subject: str = Form(...), 
    department: str = Form(...), 
    semester: str = Form(...), 
    section: str = Form('A'), 
    stream_name: str = Form(...), 
    session_id: int = Form(None),
    db: Session = Depends(get_db), 
    user=Depends(require_role('faculty','admin'))
):
    """Start a stateful attendance session backed by a background worker."""
    mgr = AttendanceManager.get_instance()
    
    # 1. Resolve Subject
    # subject input is likely the Code now (since we use code as PK).
    # Try looking up by code.
    subject_code = None
    subj = db.query(m.Subject).filter(m.Subject.code == subject).first()
    if subj:
        subject_code = subj.code
    
    # Fallback: maybe they sent Name? 
    if not subject_code:
        subj = db.query(m.Subject).filter(m.Subject.name == subject).first()
        if subj:
            subject_code = subj.code

    if not subject_code:
        raise HTTPException(status_code=400, detail=f'subject code or name "{subject}" not found')

    # 2. Resolve Department (validate against config)
    department = department.strip()
    if department not in config.DEPARTMENTS:
        raise HTTPException(status_code=400, detail=f'invalid department. allowed: {config.DEPARTMENTS}')

    try:
        sem = int(semester)
    except ValueError:
         raise HTTPException(status_code=400, detail='invalid semester')
    
    username = getattr(user, 'username', 'system')
    
    try:
        new_session_id = mgr.start_session(stream_name, subject_code, department, sem, section, username, session_id=session_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        LOG.exception("error starting session")
        raise HTTPException(status_code=500, detail=str(e))

    return {"started": True, "subject_code": subject_code, "stream_name": stream_name, "session_id": new_session_id}


@router.post('/stop')
def stop_attendance(user=Depends(require_role('faculty','admin'))):
    """Stop the current attendance session."""
    mgr = AttendanceManager.get_instance()
    if mgr.stop_session():
        return {"stopped": True, "message": "Session stopped"}
    else:
        return {"stopped": False, "message": "No session running"}


@router.get('/status')
def get_session_status(user=Depends(require_role('faculty','admin'))):
    mgr = AttendanceManager.get_instance()
    if mgr.current_session:
        return {"active": True, "session": mgr.current_session}
    return {"active": False}


@router.websocket("/live")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            # wait for messages (keep connection alive, maybe handle client pings)
            data = await websocket.receive_text()
            # currently we don't expect client commands, just listening
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)


@router.get('/recent')
async def get_recent_attendance(db: Session = Depends(get_db), user=Depends(require_role('faculty', 'admin'))):
    """Returns the latest 10 attendance records across all sessions."""
    try:
        records = db.query(m.AttendanceRecord).join(m.AttendanceSession).order_by(m.AttendanceRecord.id.desc()).limit(10).all()
        out = []
        for r in records:
            out.append({
                "student_name": r.student.name,
                "student_reg": r.student_reg,
                "subject_code": r.session.subject_code,
                "timestamp": r.recorded_at.strftime("%I:%M %p"),
                "status": r.status
            })
        return out
    except Exception as e:
        LOG.exception("Error fetching recent attendance")
        raise HTTPException(status_code=500, detail=str(e))
