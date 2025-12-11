from fastapi import APIRouter, Depends, HTTPException, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime

from ..services.db import Base, engine, get_db
from ..services.auth import (
    create_user,
    authenticate_user,
    create_access_token,
    create_refresh_token,
    create_api_key,
    revoke_token,
    decode_token,
    prune_revoked_tokens,
)
from .. import config

Base.metadata.create_all(bind=engine)

router = APIRouter()


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str


@router.post("/register")
def register(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    # Lightweight: use service create_user and let unique constraint raise if needed
    try:
        user = create_user(db, username, password)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"id": user.id, "username": user.username}


@router.post("/login", response_model=TokenResponse)
def login(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = authenticate_user(db, username, password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access = create_access_token(user)
    refresh = create_refresh_token(user)
    return {"access_token": access, "refresh_token": refresh}


@router.post("/refresh", response_model=TokenResponse)
def refresh(refresh_token: str = Form(...), db: Session = Depends(get_db)):
    try:
        payload = decode_token(refresh_token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    user_id = int(payload.get("sub"))
    # Create tokens for the subject
    access = create_access_token(type("U", (), {"id": user_id}))
    refresh = create_refresh_token(type("U", (), {"id": user_id}))
    return {"access_token": access, "refresh_token": refresh}


@router.post("/revoke")
def revoke(token: str = Form(...), db: Session = Depends(get_db)):
    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid token")
    jti = payload.get("jti")
    exp = payload.get("exp")
    expires_at = None
    if exp:
        expires_at = datetime.utcfromtimestamp(exp)
    revoke_token(db, jti, expires_at)
    prune_revoked_tokens(db)
    return {"revoked": True}


@router.post("/apikey/create")
def apikey_create(db: Session = Depends(get_db), username: str = Form(...), password: str = Form(...)):
    user = authenticate_user(db, username, password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    ak = create_api_key(db, user)
    return {"api_key": ak.key, "expires_at": ak.expires_at}
