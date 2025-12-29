from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from typing import List
from sqlalchemy.orm import Session
from ..services.db import get_db, engine, Base
from ..services import models as m
from .. import config
import httpx
import aiofiles
from ..services.auth import require_role, get_current_user
import logging

LOG = logging.getLogger("main_backend.students")
from fastapi import Security
from ..services import auth as auth_srv


router = APIRouter(prefix="/students")



@router.post("/create")
def create_student(reg_no: str = Form(...), name: str = Form(...), department: str = Form(...), semester: str = Form(...), section: str = Form('A'), roll_no: str | None = Form(None), password: str = Form(...), db: Session = Depends(get_db), user=Depends(require_role('admin'))):
    """Admin-only: create a Student profile and associated User record in one call.

    This will create a User (username=reg_no, password) with role 'student' and the Student profile.
    """
    # ensure user or student does not already exist
    LOG.info("admin %s creating student %s", getattr(user, 'username', None), reg_no)
    if db.query(m.Student).filter(m.Student.reg_no == reg_no).first():
        LOG.warning("student exists: %s", reg_no)
        raise HTTPException(status_code=400, detail="student exists")
    
    if db.query(auth_srv.User).filter(auth_srv.User.username == reg_no).first():
        raise HTTPException(status_code=400, detail='user exists')

    # create user (returns User object with username PK)
    try:
        new_user = auth_srv.create_user(db, reg_no, password, role='student')
        LOG.info("created user for student %s", reg_no)
    except Exception as e:
        LOG.exception("failed to create user for student %s: %s", reg_no, e)
        raise HTTPException(status_code=400, detail=str(e))


    # resolve department (accept name)
    def _resolve_dept(department_input: str):
        name = (department_input or '').strip()
        if name not in config.DEPARTMENTS:
            raise HTTPException(status_code=400, detail=f'invalid department. allowed: {config.DEPARTMENTS}')
        return name

    dept_name = _resolve_dept(department)
    try:
        sem = int(semester)
    except Exception:
        raise HTTPException(status_code=400, detail='invalid semester')

    # create student record
    s = m.Student(reg_no=reg_no, name=name, department=dept_name, semester=sem, section=section, roll_no=roll_no)
    db.add(s)
    db.commit()
    db.refresh(s)
    LOG.info("student profile created %s", reg_no)
    # return username implicitly as it matches reg_no
    return {"reg_no": s.reg_no, "name": s.name, "department": s.department, "semester": s.semester}


@router.get('/list', response_model=List[dict])
def list_students(department: str | None = None, semester: int | None = None, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """List student profiles.
    """
    LOG.info("user %s listing students (dept=%s, sem=%s)", getattr(user, 'username', None), department, semester)
    q = db.query(m.Student)
    if department:
        q = q.filter(m.Student.department == department)
    if semester:
        q = q.filter(m.Student.semester == semester)
    
    students = q.all()
    out = []
    for s in students:
        out.append({
            "reg_no": s.reg_no,
            "name": s.name,
            "department": s.department,
            "semester": s.semester,
            "section": s.section,
            "roll_no": s.roll_no
        })
    return out


@router.get("/{reg_no}")
def get_student(reg_no: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    s = db.query(m.Student).filter(m.Student.reg_no == reg_no).first()
    if not s:
        raise HTTPException(status_code=404, detail="not found")
    # students may only view their own record; faculty/admin may view any
    if getattr(user, 'role', None) == 'student' and getattr(user, 'username', None) != reg_no:
        LOG.warning("student %s attempted to view other profile %s", getattr(user, 'username', None), reg_no)
        raise HTTPException(status_code=403, detail='students may only view their own profile')
    LOG.info("user %s viewing student %s", getattr(user, 'username', None), reg_no)
    dept_name = s.department
    return {"reg_no": s.reg_no, "name": s.name, "semester": s.semester, "department": dept_name}


@router.post('/{reg_no}/enroll-photos')
async def enroll_photos(reg_no: str, files: List[UploadFile] = File(...), db: Session = Depends(get_db), user=Depends(require_role('faculty','admin'))):
    """Accept multiple photos from faculty/admin and forward to model layer /refresh-db endpoint.

    Only faculty or admin may enroll photos on behalf of students.
    """
    multipart = []
    try:
        # validate student exists
        student = db.query(m.Student).filter(m.Student.reg_no == reg_no).first()
        if not student:
            raise HTTPException(status_code=404, detail="student not found")

        LOG.info("user %s uploading %d files for enroll %s", getattr(user, 'username', None), len(files), reg_no)
        async with httpx.AsyncClient() as client:
            for f in files:
                content = await f.read()
                multipart.append(("files", (f.filename, content, f.content_type)))

            data = {"identity": reg_no}
            url = f"{config.MODEL_SERVICE_URL}/refresh-db"
            from ..services.model_client import get_headers_async
            headers = await get_headers_async()
            resp = await client.post(url, files=multipart, data=data, headers=headers, timeout=30.0)
            LOG.info("model service refresh-db status=%s detail=%s", resp.status_code, resp.text[:200])
            
            if resp.status_code != 200:
                # Forward the error status and detail
                raise HTTPException(status_code=resp.status_code, detail=resp.text)
            
            return {"status": resp.status_code, "detail": resp.text}
    except Exception as e:
        LOG.exception("enroll photos failed for %s: %s", reg_no, e)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        pass



@router.post('/modify')
def modify_student(target_reg: str = Form(...), name: str | None = Form(None), semester: str | None = Form(None), department: str | None = Form(None), section: str | None = Form(None), roll_no: str | None = Form(None), db: Session = Depends(get_db), user=Depends(require_role('admin'))):
    # target_reg is the PK to find
    s = db.query(m.Student).filter(m.Student.reg_no == target_reg).first()
    if not s:
        raise HTTPException(status_code=404, detail='student not found')
    LOG.info("user %s modifying student %s", getattr(user, 'username', None), target_reg)
    
    if name:
        s.name = name
    if semester:
        try:
            s.semester = int(semester)
        except Exception:
            raise HTTPException(status_code=400, detail='invalid semester')
    if department:
        # validate dept
        if department not in config.DEPARTMENTS:
            raise HTTPException(status_code=400, detail=f'invalid department')
        s.department = department
    if section:
        s.section = section
    if roll_no is not None:
        s.roll_no = roll_no
    
    db.commit()
    return {"reg_no": s.reg_no}


@router.post('/delete')
def delete_student(target_reg: str = Form(...), db: Session = Depends(get_db), user=Depends(require_role('admin'))):
    s = db.query(m.Student).filter(m.Student.reg_no == target_reg).first()
    if not s:
        raise HTTPException(status_code=404, detail='student not found')
    LOG.info("user %s deleting student %s", getattr(user, 'username', None), target_reg)
    
    # Also delete associated user
    u = db.query(auth_srv.User).filter(auth_srv.User.username == target_reg).first()
    if u:
        db.delete(u)
        LOG.info("deleted user account for %s", target_reg)
        
    db.delete(s)
    db.commit()
    return {"deleted": target_reg}


# NOTE: student self-registration is not allowed. Student profiles and user accounts
# must be created by an admin using /auth/register (to create User) and /students/create
# (to create Student profile).
