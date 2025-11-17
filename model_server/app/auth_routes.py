"""Authentication endpoints for login, registration, and API key management."""

from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth import (
    APIKeyCreateRequest,
    APIKeyResponse,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    Token,
    User,
    auth_service,
    get_current_active_user,
)
from app.auth_db import auth_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/auth", tags=["Authentication"])
security = HTTPBearer()


@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest):
    """
    Register a new user.
    
    - **username**: Unique username (3-50 characters)
    - **password**: Password (min 8 characters)
    - **email**: Valid email address
    """
    user = auth_service.register_user(
        username=request.username,
        password=request.password,
        email=request.email
    )
    
    return {
        "message": "User registered successfully",
        "user_id": user.id,
        "username": user.username,
        "email": user.email
    }


@router.post("/login", response_model=Token)
async def login(request: LoginRequest):
    """
    Login with username and password to receive JWT tokens.
    
    - **username**: Your username
    - **password**: Your password
    
    Returns:
    - **access_token**: JWT access token (expires in 30 minutes)
    - **refresh_token**: Refresh token (expires in 30 days)
    """
    user = auth_service.authenticate_user(request.username, request.password)
    tokens = auth_service.create_tokens(user)
    
    logger.info(f"User logged in: {user.username}")
    
    return tokens


@router.post("/refresh", response_model=Token)
async def refresh_token(request: RefreshTokenRequest):
    """
    Refresh access token using refresh token.
    
    - **refresh_token**: Your refresh token from login
    
    Returns new access_token and refresh_token.
    """
    tokens = auth_service.refresh_access_token(request.refresh_token)
    
    return tokens


@router.post("/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: User = Depends(get_current_active_user)
):
    """
    Logout user by revoking all refresh tokens and blacklisting access token.
    
    Requires: Bearer token (JWT access token)
    """
    access_token = credentials.credentials
    auth_service.logout_user(current_user.id, access_token)
    
    return {
        "message": "Logged out successfully",
        "username": current_user.username
    }


@router.get("/me")
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """
    Get current authenticated user information.
    
    Requires: Bearer token (JWT or API key)
    """
    return {
        "user_id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at,
        "last_login": current_user.last_login
    }


@router.post("/api-keys", response_model=APIKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    request: APIKeyCreateRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new API key for the authenticated user.
    
    - **name**: Descriptive name for the API key
    - **expires_days**: Optional expiration in days (1-365)
    
    Requires: Bearer token (JWT access token)
    
    Returns the API key - SAVE IT! It won't be shown again.
    """
    api_key = auth_db.create_api_key(
        user_id=current_user.id,
        name=request.name,
        expires_days=request.expires_days
    )
    
    # Get the created key details
    key_data = auth_db.get_api_key(api_key)
    
    if not key_data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create API key"
        )
    
    logger.info(f"API key created: user={current_user.username}, name={request.name}")
    
    return APIKeyResponse(
        id=key_data.id,
        name=key_data.name,
        key=api_key,  # Only returned on creation
        is_active=key_data.is_active,
        expires_at=key_data.expires_at,
        created_at=key_data.created_at,
        last_used=key_data.last_used
    )


@router.get("/api-keys", response_model=List[APIKeyResponse])
async def list_api_keys(current_user: User = Depends(get_current_active_user)):
    """
    List all API keys for the authenticated user.
    
    Requires: Bearer token (JWT access token)
    
    Note: The actual key values are not returned, only metadata.
    """
    keys = auth_db.get_user_api_keys(current_user.id)
    
    return [
        APIKeyResponse(
            id=key.id,
            name=key.name,
            key=None,  # Never return the actual key after creation
            is_active=key.is_active,
            expires_at=key.expires_at,
            created_at=key.created_at,
            last_used=key.last_used
        )
        for key in keys
    ]


# API key revocation is now AUTOMATIC based on expires_at timestamp
# When an expired key is used, auth.py will automatically reject it
# No manual revoke endpoint needed - keys expire automatically


@router.post("/cleanup-expired", response_model=dict)
async def cleanup_expired_tokens(current_user: User = Depends(get_current_active_user)):
    """
    Clean up expired tokens and API keys (admin operation).
    
    Requires: Bearer token (JWT access token)
    
    Removes:
    - Expired refresh tokens
    - Expired API keys (deactivates them)
    - Old blacklisted tokens (older than 30 days)
    """
    rows_affected = auth_db.cleanup_expired_tokens()
    
    logger.info(f"Token cleanup performed by {current_user.username}: {rows_affected} rows affected")
    
    return {
        "message": "Cleanup completed",
        "rows_affected": rows_affected
    }
