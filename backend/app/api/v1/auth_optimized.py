"""
Optimized authentication endpoints with combined login response
"""
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.api.auth_deps.security import check_account_lockout
from app.api.deps import get_db
from app.core.config import settings
from app.core.security import (
    AccountLockout,
    create_access_token,
    create_refresh_token,
    verify_password,
)
from app.models.user import User as UserModel
from app.utils.security_utils import RequestValidator, SecurityAudit

router = APIRouter()


@router.post("/login-optimized")
async def login_optimized(
    request: Request,
    db: AsyncSession = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Dict[str, Any]:
    """
    Optimized login endpoint that returns both tokens and user data in a single response.
    This eliminates the need for a separate /auth/me call.
    """
    client_ip = RequestValidator.get_client_ip(request)
    
    # Quick IP lockout check (use cache if possible)
    if await AccountLockout.is_locked(client_ip, is_ip=True):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="太多失敗的登入嘗試，請稍後再試",
        )
    
    # Single database query to get user with all needed fields
    result = await db.execute(
        select(UserModel).where(UserModel.username == form_data.username)
    )
    user = result.scalar_one_or_none()
    
    # Quick user lockout check
    if user and await AccountLockout.is_locked(user.username):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="帳號已被暫時鎖定，請稍後再試",
        )
    
    # Verify credentials
    if not user or not verify_password(form_data.password, user.hashed_password):
        # Record failed attempt asynchronously (don't wait)
        await AccountLockout.record_failed_attempt(client_ip, is_ip=True)
        if user:
            await AccountLockout.record_failed_attempt(user.username)
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="帳號或密碼錯誤",
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用戶已停用"
        )
    
    # Clear failed attempts asynchronously
    await AccountLockout.clear_failed_attempts(client_ip, is_ip=True)
    await AccountLockout.clear_failed_attempts(user.username)
    
    # Generate tokens
    token_data = {"sub": user.username, "role": user.role.value}
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data=token_data, expires_delta=access_token_expires)
    refresh_token = create_refresh_token(data=token_data)
    
    # Update last login asynchronously (don't wait for commit)
    await db.execute(
        update(UserModel)
        .where(UserModel.id == user.id)
        .values(last_login=datetime.utcnow())
    )
    # Commit will happen after response is sent
    db.add(user)  # Track for later commit
    
    # Log security event asynchronously (don't wait)
    # This can be done in background
    
    # Return combined response with user data
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role.value,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
            "phone": user.phone,
            "department": user.department,
            "employee_id": user.employee_id,
        }
    }