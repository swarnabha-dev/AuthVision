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
    access_exp: int
    refresh_exp: int


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
    
    # helper to create token and get exp
    jti_acc = config.ACCESS_TOKEN_EXPIRES_SECONDS
    jti_ref = config.REFRESH_TOKEN_EXPIRES_SECONDS
    
    access = create_access_token(user)
    refresh = create_refresh_token(user)

    # Decode simply to get exp, or calculate it. 
    # Since create_access_token logic is opaque here (uses seconds from config), we can decode to be sure.
    # Or import decode_token.
    try:
        acc_payload = decode_token(access)
        ref_payload = decode_token(refresh)
    except:
        raise HTTPException(500, "Token generation failed")

    return {
        "access_token": access,
        "refresh_token": refresh,
        "access_exp": acc_payload.get("exp"),
        "refresh_exp": ref_payload.get("exp")
    }


@router.post("/refresh", response_model=TokenResponse)
def refresh(refresh_token: str = Form(...), db: Session = Depends(get_db)):
    try:
        payload = decode_token(refresh_token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    user_id = int(payload.get("sub"))
    
    # Create tokens for the subject
    # Dummy user object for signature compatibility if create_*_token expects obj with .id
    UserObj = type("U", (), {"id": user_id})
    
    access = create_access_token(UserObj)
    refresh = create_refresh_token(UserObj)

    try:
        acc_payload = decode_token(access)
        ref_payload = decode_token(refresh)
    except:
        raise HTTPException(500, "Token generation failed")
    
    return {
        "access_token": access,
        "refresh_token": refresh,
        "access_exp": acc_payload.get("exp"),
        "refresh_exp": ref_payload.get("exp")
    }


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
