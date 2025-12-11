import uuid
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship, Session

from passlib.context import CryptContext
import jwt

from .db import Base, get_db
from .. import config

pwd_ctx = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class ApiKey(Base):
    __tablename__ = "api_keys"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    revoked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)

    user = relationship("User")


class RevokedToken(Base):
    __tablename__ = "revoked_tokens"
    id = Column(Integer, primary_key=True)
    jti = Column(String, unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, index=True)


Index("ix_revoked_tokens_expires_at", RevokedToken.expires_at)


def create_user(db: Session, username: str, password: str) -> User:
    pw_hash = pwd_ctx.hash(password)
    user = User(username=username, password_hash=pw_hash)
    db.add(user)
    db.commit()
    db.refresh(user)
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


from datetime import datetime, timedelta, timezone

def create_access_token(user: User, expires_delta: Optional[timedelta] = None) -> str:
    jti = _new_jti()
    now = datetime.now(timezone.utc)
    exp = now + (expires_delta or timedelta(seconds=config.ACCESS_TOKEN_EXPIRES_SECONDS))
    payload = {"sub": str(user.id), "jti": jti, "iat": int(now.timestamp()), "exp": int(exp.timestamp())}
    token = jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)
    return token


def create_refresh_token(user: User, expires_delta: Optional[timedelta] = None) -> str:
    jti = _new_jti()
    now = datetime.now(timezone.utc)
    exp = now + (expires_delta or timedelta(seconds=config.REFRESH_TOKEN_EXPIRES_SECONDS))
    payload = {"sub": str(user.id), "jti": jti, "iat": int(now.timestamp()), "exp": int(exp.timestamp())}
    token = jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)
    return token


def decode_token(token: str) -> dict:
    # Decode without letting PyJWT raise ExpiredSignatureError here; validate manually
    try:
        payload = jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM], options={"verify_exp": False})
    except Exception:
        # re-raise for consistent behavior
        raise

    # manual expiration check
    exp = payload.get("exp")
    if exp is not None:
        try:
            if int(exp) < int(datetime.utcnow().timestamp()):
                raise jwt.ExpiredSignatureError("Signature has expired")
        except ValueError:
            # non-integer exp, let PyJWT handle it upstream
            pass

    return payload


def revoke_token(db: Session, jti: str, expires_at: datetime):
    rt = RevokedToken(jti=jti, expires_at=expires_at)
    db.add(rt)
    db.commit()


def is_token_revoked(db: Session, jti: str) -> bool:
    return db.query(RevokedToken).filter(RevokedToken.jti == jti).first() is not None


def prune_revoked_tokens(db: Session):
    # Remove expired entries to keep table small
    now = datetime.utcnow()
    db.query(RevokedToken).filter(RevokedToken.expires_at < now).delete()
    db.commit()


def create_api_key(db: Session, user: User, expires_seconds: Optional[int] = None) -> ApiKey:
    raw = uuid.uuid4().hex + uuid.uuid4().hex
    key = raw[: config.API_KEY_BYTES * 2]
    expires_at = None
    if expires_seconds:
        expires_at = datetime.utcnow() + timedelta(seconds=expires_seconds)
    ak = ApiKey(key=key, user_id=user.id, expires_at=expires_at)
    db.add(ak)
    db.commit()
    db.refresh(ak)
    return ak


def get_api_key(db: Session, key: str) -> Optional[ApiKey]:
    ak = db.query(ApiKey).filter(ApiKey.key == key, ApiKey.revoked == False).first()
    if not ak:
        return None
    if ak.expires_at and ak.expires_at < datetime.utcnow():
        return None
    return ak


# FastAPI dependency factory for combined auth
from fastapi import HTTPException, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Security, Depends

security = HTTPBearer(auto_error=False)


def require_auth(require_api_key: bool = False, require_jwt: bool = False):
    def _dep(authorization: HTTPAuthorizationCredentials = Security(security), x_api_key: str | None = Header(None), db: Session = Depends(get_db)):
        # API key check
        if require_api_key:
            if not x_api_key:
                raise HTTPException(status_code=401, detail="API key required")
            ak = get_api_key(db, x_api_key)
            if not ak:
                raise HTTPException(status_code=401, detail="Invalid API key")

        # JWT check
        if require_jwt:
            if not authorization:
                raise HTTPException(status_code=401, detail="Authorization required")
            token = authorization.credentials
            try:
                payload = decode_token(token)
            except Exception:
                raise HTTPException(status_code=401, detail="Invalid token")
            jti = payload.get("jti")
            if is_token_revoked(db, jti):
                raise HTTPException(status_code=401, detail="Token revoked")

        return True

    return _dep
