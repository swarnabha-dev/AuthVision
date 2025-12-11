from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy.orm import Session
from ..services.db import get_db
from ..services import models as m
from ..services.auth import require_role
from ..services import auth as auth_srv
from .. import config
import logging

LOG = logging.getLogger("main_backend.faculty")

router = APIRouter(prefix="/faculty")

def _resolve_dept(department_input: str):
    name = (department_input or '').strip()
    if name not in config.DEPARTMENTS:
        raise HTTPException(status_code=400, detail=f'invalid department. allowed: {config.DEPARTMENTS}')
    return name

@router.post("/create")
def create_faculty(username: str = Form(...), name: str = Form(...), department: str = Form(...), password: str = Form(...), db: Session = Depends(get_db), user=Depends(require_role('admin'))):
    """Admin-only: create a Faculty profile and associated User record.
    """
    LOG.info("admin %s creating faculty %s", getattr(user, 'username', None), username)
    
    # Check existence
    if db.query(m.Faculty).filter(m.Faculty.username == username).first():
        raise HTTPException(status_code=400, detail="Faculty profile exists")
    if db.query(auth_srv.User).filter(auth_srv.User.username == username).first():
        raise HTTPException(status_code=400, detail="User exists")

    # Validate Dept
    dept_name = _resolve_dept(department)

    # Create User
    try:
        new_user = auth_srv.create_user(db, username, password, role='faculty')
    except Exception as e:
        LOG.exception("failed to create user for faculty %s: %s", username, e)
        raise HTTPException(status_code=400, detail=str(e))

    # Create Profile
    f = m.Faculty(username=username, name=name, department=dept_name)
    db.add(f)
    db.commit()
    db.refresh(f)
    LOG.info("faculty profile created %s", username)

    return {"username": f.username, "name": f.name, "department": f.department}
