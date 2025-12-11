import uuid
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import Session
from passlib.context import CryptContext
import jwt

from .db import Base, get_db
from .. import config

pwd_ctx = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")



class User(Base):
    __tablename__ = "users"
    # id = Column(Integer, primary_key=True, index=True)
    username = Column(String, primary_key=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="student")  # 'student' | 'faculty' | 'admin'
    created_at = Column(DateTime, default=datetime.utcnow)


def create_user(db: Session, username: str, password: str, role: str = "student") -> User:
    import logging
    LOG = logging.getLogger("main_backend.auth")
    pw_hash = pwd_ctx.hash(password)
    user = User(username=username, password_hash=pw_hash, role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    LOG.info("created user %s role=%s", username, role)
    return user


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return None
    if not pwd_ctx.verify(password, user.password_hash):
        return None
    return user


def _new_jti() -> str:
    return str(uuid.uuid4())


def create_access_token(user, expires_delta: Optional[timedelta] = None) -> str:
    now = datetime.utcnow()
    exp = now + (expires_delta or timedelta(seconds=config.ACCESS_TOKEN_EXPIRES_SECONDS))
    payload = {"sub": user.username, "role": user.role, "jti": _new_jti(), "iat": int(now.timestamp()), "exp": int(exp.timestamp())}
    return jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)


def create_refresh_token(user, expires_delta: Optional[timedelta] = None) -> str:
    now = datetime.utcnow()
    exp = now + (expires_delta or timedelta(seconds=config.REFRESH_TOKEN_EXPIRES_SECONDS))
    payload = {"sub": user.username, "jti": _new_jti(), "iat": int(now.timestamp()), "exp": int(exp.timestamp())}
    return jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    # decode without verifying exp to raise controlled errors upstream
    payload = jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM], options={"verify_exp": False})
    # manual exp check
    exp = payload.get("exp")
    if exp and int(exp) < int(datetime.utcnow().timestamp()):
        raise jwt.ExpiredSignatureError("token expired")
    return payload


from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .db import SessionLocal
from fastapi import Security

security = HTTPBearer(auto_error=False)


def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security), db: Session = Depends(get_db)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Authorization required")
    token = credentials.credentials
    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    username = payload.get("sub")
    if not username:
         raise HTTPException(status_code=401, detail="Invalid token subject")
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def require_role(*roles):
    def _dep(user = Depends(get_current_user)):
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient role")
        return user
    return _dep
