"""JWT and API Key authentication."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from app.auth_db import User, auth_db
from app.config import config

logger = logging.getLogger(__name__)

# Security
security = HTTPBearer()


class Token(BaseModel):
    """Token response model."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class TokenData(BaseModel):
    """Token payload data."""
    user_id: int
    username: str
    exp: datetime


class LoginRequest(BaseModel):
    """Login request model."""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=100)


class RegisterRequest(BaseModel):
    """Registration request model."""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=100)
    email: str = Field(..., pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


class RefreshTokenRequest(BaseModel):
    """Refresh token request model."""
    refresh_token: str


class APIKeyCreateRequest(BaseModel):
    """API key creation request."""
    name: str = Field(..., min_length=1, max_length=100)
    expires_days: Optional[int] = Field(None, ge=1, le=365)


class APIKeyResponse(BaseModel):
    """API key response model."""
    id: int
    name: str
    key: Optional[str] = None  # Only returned on creation
    is_active: bool
    expires_at: Optional[datetime]
    created_at: datetime
    last_used: Optional[datetime]


class AuthService:
    """Authentication service."""
    
    def __init__(self):
        self.secret_key = config.jwt_secret
        self.algorithm = config.jwt_algorithm
        self.access_token_expire_minutes = config.access_token_expire_minutes
        self.refresh_token_expire_days = config.refresh_token_expire_days
    
    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt."""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode(), salt).decode()
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify a password against a hash."""
        return bcrypt.checkpw(password.encode(), hashed.encode())
    
    def create_access_token(self, user_id: int, username: str) -> str:
        """Create JWT access token."""
        expires = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        payload = {
            "user_id": user_id,
            "username": username,
            "exp": expires,
            "type": "access"
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def decode_access_token(self, token: str) -> TokenData:
        """Decode and validate JWT access token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Check if token is blacklisted
            if auth_db.is_token_blacklisted(token):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has been revoked"
                )
            
            return TokenData(
                user_id=payload["user_id"],
                username=payload["username"],
                exp=datetime.fromtimestamp(payload["exp"])
            )
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}"
            )
    
    def register_user(self, username: str, password: str, email: str) -> User:
        """Register a new user."""
        # Check if user exists
        if auth_db.get_user_by_username(username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists"
            )
        
        # Hash password and create user
        password_hash = self.hash_password(password)
        user_id = auth_db.create_user(username, password_hash, email)
        
        user = auth_db.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user"
            )
        
        logger.info(f"User registered: {username}")
        return user
    
    def authenticate_user(self, username: str, password: str) -> User:
        """Authenticate user with username and password."""
        user = auth_db.get_user_by_username(username)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )
        
        if not self.verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )
        
        # Update last login
        auth_db.update_last_login(user.id)
        
        logger.info(f"User authenticated: {username}")
        return user
    
    def create_tokens(self, user: User) -> Token:
        """Create access and refresh tokens."""
        access_token = self.create_access_token(user.id, user.username)
        refresh_token = auth_db.create_refresh_token(user.id, self.refresh_token_expire_days)
        
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self.access_token_expire_minutes * 60
        )
    
    def refresh_access_token(self, refresh_token: str) -> Token:
        """Refresh access token using refresh token."""
        # Get refresh token from database
        token_data = auth_db.get_refresh_token(refresh_token)
        
        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        if token_data.is_revoked:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has been revoked"
            )
        
        if token_data.expires_at < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has expired"
            )
        
        # Get user
        user = auth_db.get_user_by_id(token_data.user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        # Create new tokens
        return self.create_tokens(user)
    
    def validate_api_key(self, api_key: str) -> User:
        """Validate API key and return user."""
        # Check if blacklisted
        if auth_db.is_token_blacklisted(api_key):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key has been revoked"
            )
        
        # Get API key from database
        key_data = auth_db.get_api_key(api_key)
        
        if not key_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )
        
        if not key_data.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key is inactive"
            )
        
        if key_data.expires_at and key_data.expires_at < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key has expired"
            )
        
        # Update last used
        auth_db.update_api_key_usage(api_key)
        
        # Get user
        user = auth_db.get_user_by_id(key_data.user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        return user
    
    def logout_user(self, user_id: int, access_token: str):
        """Logout user by revoking all refresh tokens and blacklisting access token."""
        # Revoke all refresh tokens
        auth_db.revoke_user_refresh_tokens(user_id)
        
        # Blacklist current access token
        auth_db.blacklist_token(access_token, "user_logout")
        
        logger.info(f"User logged out: user_id={user_id}")


# Global auth service
auth_service = AuthService()


# Dependency: Get current user from JWT or API key
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """Get current user from Bearer token (JWT or API key)."""
    token = credentials.credentials
    
    # Try JWT first
    if not token.startswith("sk_"):
        token_data = auth_service.decode_access_token(token)
        user = auth_db.get_user_by_id(token_data.user_id)
        
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        return user
    
    # Try API key
    return auth_service.validate_api_key(token)


# Dependency: Get current active user
async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Ensure user is active."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user
