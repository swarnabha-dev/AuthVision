from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy.orm import Session
from ..services.db import get_db, engine, Base
from ..services import models as m
from ..services.auth import require_role, get_current_user
import logging

LOG = logging.getLogger("main_backend.subjects")


router = APIRouter(prefix="/subjects")

from .. import config

def _resolve_department(department_input: str):
    """Validate a department string against allowed list.
    """
    if department_input is None:
        return None
    name = department_input.strip()
    if name not in config.DEPARTMENTS:
         raise HTTPException(status_code=400, detail=f'invalid department. allowed: {config.DEPARTMENTS}')
    return name


@router.post('/create')
def create_subject(code: str = Form(...), name: str = Form(...), department: str = Form(...), semester: str = Form(...), db: Session = Depends(get_db), user=Depends(require_role('faculty','admin'))):
    # resolve department (accept name)
    dept_name = _resolve_department(department)
    try:
        sem = int(semester)
    except Exception:
        LOG.warning("invalid semester provided by user %s: %r", getattr(user, 'username', None), semester)
        raise HTTPException(status_code=400, detail='invalid semester')

    LOG.info("user %s creating subject code=%s name=%s dept=%s sem=%s", getattr(user, 'username', None), code, name, dept_name, sem)
    
    # check if code exists (PK)
    exists = db.query(m.Subject).filter(m.Subject.code == code).first()
    if exists:
        LOG.warning("subject duplicate code attempted by %s code=%s", getattr(user, 'username', None), code)
        raise HTTPException(status_code=400, detail='subject code already exists')

    s = m.Subject(code=code, name=name, department=dept_name, semester=sem)
    db.add(s)
    db.commit()
    db.refresh(s)
    
    return {"code": s.code, "name": s.name, "department": s.department}


@router.post('/modify')
def modify_subject(target_code: str = Form(...), name: str | None = Form(None), semester: str | None = Form(None), department: str | None = Form(None), db: Session = Depends(get_db), user=Depends(require_role('faculty','admin'))):
    # target_code is the PK to find
    s = db.query(m.Subject).filter(m.Subject.code == target_code).first()
    if not s:
        raise HTTPException(status_code=404, detail='not found')
    LOG.info("user %s modifying subject %s", getattr(user, 'username', None), target_code)
    
    if name:
        s.name = name
    if semester:
        try:
            s.semester = int(semester)
        except Exception:
            raise HTTPException(status_code=400, detail='invalid semester')
    if department:
        s.department = _resolve_department(department)
    
    db.commit()
    return {"code": s.code}


@router.post('/delete')
def delete_subject(target_code: str = Form(...), db: Session = Depends(get_db), user=Depends(require_role('faculty','admin'))):
    s = db.query(m.Subject).filter(m.Subject.code == target_code).first()
    if not s:
        raise HTTPException(status_code=404, detail='not found')
    LOG.info("user %s deleting subject %s", getattr(user, 'username', None), target_code)
    db.delete(s)
    db.commit()
    return {"deleted": target_code}


@router.get('/list')
def list_subjects(department: str | None = None, semester: int | None = None, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """List subjects. department filter is by name.
    """
    q = db.query(m.Subject)
    if department:
        if department not in config.DEPARTMENTS:
            return []
        q = q.filter(m.Subject.department == department)

    if semester:
        q = q.filter(m.Subject.semester == semester)
    subs = q.all()
    out = []
    for s in subs:
        out.append({"code": s.code, "name": s.name, "department": s.department, "semester": s.semester})
    return out



