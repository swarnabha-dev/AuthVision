from fastapi import APIRouter, Depends, Form, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..services.db import engine, Base, get_db
from ..services import auth as auth_srv
from ..services.auth import require_role
from ..services import auth as auth_srv
import logging

LOG = logging.getLogger("main_backend.auth")

Base.metadata.create_all(bind=engine)

router = APIRouter(prefix="/auth")


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str


@router.post("/register")
def register(username: str = Form(...), password: str = Form(...), role: str = Form('admin'), db: Session = Depends(get_db), authorization: str | None = Header(None)):
    """Create a new Admin user.

    - Only allows creating 'admin' role.
    - If no admins exist in DB, allows creation without auth (Bootstrap).
    - If admins exist, requires Admin authorization.
    
    For 'student' creation use `/students/create`.
    For 'faculty' creation use `/faculty/create`.
    """
    if role != 'admin':
        raise HTTPException(status_code=400, detail="Use specific endpoints for non-admin roles")

    # Check if any admin exists
    admin_exists = db.query(auth_srv.User).filter(auth_srv.User.role == 'admin').first()
    
    if admin_exists:
        if not authorization:
             raise HTTPException(status_code=401, detail='admin authorization required')
        try:
            token = authorization.split()[-1]
            payload = auth_srv.decode_token(token)
            caller_username = payload.get('sub')
            caller = db.query(auth_srv.User).filter(auth_srv.User.username == caller_username).first()
            if not caller or getattr(caller, 'role', None) != 'admin':
                raise HTTPException(status_code=403, detail='admin required')
        except Exception:
            raise HTTPException(status_code=401, detail='invalid or missing token')

    LOG.info("register attempt: username=%s role=admin", username)
    
    if db.query(auth_srv.User).filter(auth_srv.User.username == username).first():
        raise HTTPException(status_code=400, detail="User already exists")

    try:
        user = auth_srv.create_user(db, username, password, role='admin')
    except Exception as e:
        LOG.exception("user create failed: %s", e)
        raise HTTPException(status_code=400, detail=str(e))

    return {"username": user.username, "role": user.role}


@router.post("/login", response_model=TokenResponse)
def login(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = auth_srv.authenticate_user(db, username, password)
    if not user:
        LOG.warning("login failed for username=%s", username)
        raise HTTPException(status_code=401, detail="Invalid credentials")
    LOG.info("login success for username=%s role=%s", username, user.role)
    return {"access_token": auth_srv.create_access_token(user), "refresh_token": auth_srv.create_refresh_token(user)}
