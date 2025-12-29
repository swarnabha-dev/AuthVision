from fastapi import APIRouter, Depends, Form, HTTPException, Header
import jwt
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..services.db import engine, Base, get_db
from ..services import auth as auth_srv
from ..services.auth import require_role
from ..services import auth as auth_srv
import logging

LOG = logging.getLogger("main_backend.auth")


router = APIRouter(prefix="/auth", tags=["auth"])


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str


class UserResponse(BaseModel):
    username: str
    role: str


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
    access = auth_srv.create_access_token(user)
    refresh_token, refresh_jti, refresh_exp = auth_srv.create_refresh_token(user)
    # store refresh jti for rotation/revocation checks
    try:
        auth_srv.store_refresh_jti(db, refresh_jti, user.username, refresh_exp)
    except Exception:
        LOG.exception("failed to store refresh jti for %s", user.username)
    return {"access_token": access, "refresh_token": refresh_token}


@router.post("/refresh", response_model=TokenResponse)
def refresh(refresh_token: str = Form(...), db: Session = Depends(get_db)):
    """Exchange a valid refresh token for a new access token (and new refresh token)."""
    try:
        payload = auth_srv.decode_token(refresh_token)
    except Exception as e:
        LOG.warning("refresh token decode failed: %s", e)
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    # enforce refresh-only usage
    if payload.get('type') != 'refresh':
        raise HTTPException(status_code=401, detail='Invalid refresh token')

    jti = payload.get('jti')
    if not jti or not auth_srv.is_refresh_token_valid(db, jti):
        LOG.warning("refresh token jti invalid or revoked: %s", jti)
        raise HTTPException(status_code=401, detail='Invalid refresh token')

    username = payload.get('sub')
    if not username:
        raise HTTPException(status_code=401, detail='Invalid token subject')

    user = db.query(auth_srv.User).filter(auth_srv.User.username == username).first()
    if not user:
        raise HTTPException(status_code=401, detail='User not found')

    # rotation: revoke the old refresh jti and issue a new one
    try:
        auth_srv.revoke_refresh_jti(db, jti)
    except Exception:
        LOG.exception("failed to revoke old refresh jti %s", jti)

    access = auth_srv.create_access_token(user)
    new_refresh_token, new_jti, new_exp = auth_srv.create_refresh_token(user)
    try:
        auth_srv.store_refresh_jti(db, new_jti, user.username, new_exp)
    except Exception:
        LOG.exception("failed to store new refresh jti for %s", user.username)

    LOG.info("refresh token rotated for username=%s", username)
    return {"access_token": access, "refresh_token": new_refresh_token}


@router.post("/logout")
def logout(refresh_token: str = Form(...), db: Session = Depends(get_db)):
    """Logout user by revoking their refresh token."""
    try:
        payload = auth_srv.decode_token(refresh_token)
        jti = payload.get('jti')
        username = payload.get('sub')
        
        if jti:
            # Revoke this specific refresh token
            auth_srv.revoke_refresh_jti(db, jti)
            LOG.info("logout: revoked refresh token jti=%s for username=%s", jti, username)
        
        return {"message": "Logged out successfully"}
    except Exception as e:
        LOG.warning("logout failed: %s", e)
        # Even if token is invalid, return success (already logged out)
        return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
def me(user = Depends(auth_srv.get_current_user)):
    """Return basic information about the authenticated user."""
    return {"username": user.username, "role": user.role}
