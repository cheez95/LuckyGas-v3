from datetime import timedelta, datetime
from typing import Any, List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.api.deps import get_db, get_current_user
from app.api.auth_deps.security import (
    check_account_lockout,
    require_secure_auth,
    require_admin_auth,
    rate_limit_by_user,
)
from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_password,
    get_password_hash,
    decode_refresh_token,
    PasswordValidator,
    AccountLockout,
    TwoFactorAuth,
    SessionManager,
)
from app.middleware.security import CSRFProtection
from app.core.security_config import get_session_config
from app.models.user import User as UserModel, UserRole
from app.schemas.user import (
    User,
    Token,
    UserCreate,
    RefreshTokenRequest,
    ChangePasswordRequest,
    TwoFactorSetup,
    TwoFactorVerify,
    PasswordResetRequest,
)
from app.utils.security_utils import (
    SecurityAudit,
    RequestValidator,
    SecureTokenGenerator,
)
from app.core.cache import cache

router = APIRouter()


@router.post("/login", response_model=Token)
async def login_access_token(
    request: Request,
    db: AsyncSession = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
    _: Any = Depends(check_account_lockout),
) -> Any:
    """
    OAuth2 compatible token login with enhanced security
    """
    client_ip = RequestValidator.get_client_ip(request)

    # Check IP lockout first
    if await AccountLockout.is_locked(client_ip, is_ip=True):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="太多失敗的登入嘗試，請稍後再試",
        )

    result = await db.execute(
        select(UserModel).where(UserModel.username == form_data.username)
    )
    user = result.scalar_one_or_none()

    # Check user lockout
    if user and await AccountLockout.is_locked(user.username):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="帳號已被暫時鎖定，請稍後再試",
        )

    if not user or not verify_password(form_data.password, user.hashed_password):
        # Record failed attempt
        await AccountLockout.record_failed_attempt(client_ip, is_ip=True)
        if user:
            await AccountLockout.record_failed_attempt(user.username)

        # Log security event
        await SecurityAudit.log_security_event(
            "failed_login",
            user_id=user.id if user else None,
            ip_address=client_ip,
            details={"username": form_data.username},
            severity="WARNING",
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="帳號或密碼錯誤",
            headers={"WWW-Authenticate": "Bearer"},
        )
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="用戶已停用")

    # Clear failed attempts on successful login
    await AccountLockout.clear_failed_attempts(client_ip, is_ip=True)
    await AccountLockout.clear_failed_attempts(user.username)

    # Create session with proper token data
    remember_me = form_data.scopes and "remember_me" in form_data.scopes

    # Create tokens directly with correct data
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role.value},
        expires_delta=access_token_expires,
    )

    refresh_token = create_refresh_token(
        data={"sub": user.username, "role": user.role.value}
    )

    # Update last login
    await db.execute(
        update(UserModel)
        .where(UserModel.id == user.id)
        .values(last_login=datetime.utcnow())
    )
    await db.commit()

    # Log successful login
    await SecurityAudit.log_security_event(
        "successful_login", user_id=user.id, ip_address=client_ip, severity="INFO"
    )

    # Check if 2FA is required
    needs_2fa = user.two_factor_enabled

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "requires_2fa": needs_2fa,
    }


@router.post("/register", response_model=User)
async def register(
    request: Request,
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db),
    _: Any = Depends(check_account_lockout),
) -> Any:
    """
    Register new user with password policy enforcement
    """
    # Validate password against policy
    is_valid, errors = PasswordValidator.validate_password(
        user_in.password, user_in.username
    )

    if not is_valid:
        raise HTTPException(
            status_code=400, detail=f"密碼不符合要求: {'; '.join(errors)}"
        )

    # Check if user exists
    result = await db.execute(
        select(UserModel).where(
            (UserModel.email == user_in.email)
            | (UserModel.username == user_in.username)
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="該電子郵件或用戶名已被註冊")

    # Create new user
    hashed_password = get_password_hash(user_in.password)
    db_user = UserModel(
        email=user_in.email,
        username=user_in.username,
        full_name=user_in.full_name,
        hashed_password=hashed_password,
        role=user_in.role,
        is_active=user_in.is_active,
        password_changed_at=datetime.utcnow(),
    )

    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)

    # Update password history
    await PasswordValidator.update_password_history(db_user.id, hashed_password)

    # Log registration
    client_ip = RequestValidator.get_client_ip(request)
    await SecurityAudit.log_security_event(
        "user_registration",
        user_id=db_user.id,
        ip_address=client_ip,
        details={"username": db_user.username, "email": db_user.email},
        severity="INFO",
    )

    return db_user


@router.post("/refresh", response_model=Token)
async def refresh_token(
    token_request: RefreshTokenRequest, db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Refresh access token using refresh token
    """
    try:
        payload = decode_refresh_token(token_request.refresh_token)
        username = payload.get("sub")
        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="無效的重新整理令牌"
            )

        # Get user from database
        result = await db.execute(
            select(UserModel).where(UserModel.username == username)
        )
        user = result.scalar_one_or_none()

        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="用戶不存在或已停用"
            )

        # Create new tokens
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        new_access_token = create_access_token(
            data={"sub": user.username, "role": user.role.value},
            expires_delta=access_token_expires,
        )

        new_refresh_token = create_refresh_token(
            data={"sub": user.username, "role": user.role.value}
        )

        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
        }

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.get("/me", response_model=User)
async def read_users_me(current_user: UserModel = Depends(get_current_user)) -> Any:
    """
    Get current user
    """
    return current_user


@router.get("/users", response_model=List[User])
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    List all users (admin only)
    """
    if (
        current_user.role != UserRole.SUPER_ADMIN
        and current_user.role != UserRole.MANAGER
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="權限不足")

    result = await db.execute(select(UserModel).offset(skip).limit(limit))
    users = result.scalars().all()
    return users


@router.post("/users", response_model=User)
async def create_user(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """
    Create new user (admin only)
    """
    if (
        current_user.role != UserRole.SUPER_ADMIN
        and current_user.role != UserRole.MANAGER
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="權限不足")

    # Check if user exists
    result = await db.execute(
        select(UserModel).where(
            (UserModel.email == user_in.email)
            | (UserModel.username == user_in.username)
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="該電子郵件或用戶名已被註冊")

    # Create new user
    db_user = UserModel(
        email=user_in.email,
        username=user_in.username,
        full_name=user_in.full_name,
        hashed_password=get_password_hash(user_in.password),
        role=user_in.role,
        is_active=user_in.is_active,
    )

    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)

    return db_user


@router.put("/users/{user_id}", response_model=User)
async def update_user(
    user_id: int,
    user_update: dict,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """
    Update user (admin only)
    """
    if (
        current_user.role != UserRole.SUPER_ADMIN
        and current_user.role != UserRole.MANAGER
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="權限不足")

    result = await db.execute(select(UserModel).where(UserModel.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="用戶不存在")

    # Update user fields
    for field, value in user_update.items():
        if hasattr(user, field) and field != "id" and field != "hashed_password":
            setattr(user, field, value)

    await db.commit()
    await db.refresh(user)

    return user


@router.post("/forgot-password")
async def forgot_password(
    request: Request, data: Dict[str, str], db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Request password reset token
    """
    email = data.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="電子郵件是必需的")

    # Find user by email
    result = await db.execute(select(UserModel).where(UserModel.email == email))
    user = result.scalar_one_or_none()

    if not user:
        # Don't reveal if email exists
        return {"message": "如果電子郵件存在，密碼重設連結已發送"}

    # Generate reset token
    reset_token = SecureTokenGenerator.generate_token()
    expiry = datetime.utcnow() + timedelta(hours=1)

    # Store reset token in cache
    await cache.set(
        f"password_reset:{reset_token}",
        {"user_id": user.id, "email": email},
        expire=3600,  # 1 hour
    )

    # TODO: Send email with reset link
    # For now, just return success

    # Log password reset request
    await SecurityAudit.log_security_event(
        "password_reset_requested",
        user_id=user.id,
        ip_address=RequestValidator.get_client_ip(request),
        severity="INFO",
    )

    return {"message": "如果電子郵件存在，密碼重設連結已發送"}


@router.post("/reset-password")
async def reset_password(
    request: Request, data: Dict[str, str], db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Reset password with token
    """
    token = data.get("token")
    new_password = data.get("new_password")

    if not token or not new_password:
        raise HTTPException(status_code=400, detail="Token和新密碼是必需的")

    # Get reset data from cache
    reset_data = await cache.get(f"password_reset:{token}")

    if not reset_data:
        raise HTTPException(status_code=400, detail="無效或過期的重設連結")

    # Validate new password
    result = await db.execute(
        select(UserModel).where(UserModel.id == reset_data["user_id"])
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="用戶不存在")

    # Validate password against policy
    is_valid, errors = PasswordValidator.validate_password(new_password, user.username)

    if not is_valid:
        raise HTTPException(
            status_code=400, detail=f"密碼不符合要求: {'; '.join(errors)}"
        )

    # Update password
    user.hashed_password = get_password_hash(new_password)
    user.password_changed_at = datetime.utcnow()

    # Delete reset token
    await cache.delete(f"password_reset:{token}")

    await db.commit()

    # Log password reset
    await SecurityAudit.log_security_event(
        "password_reset_completed",
        user_id=user.id,
        ip_address=RequestValidator.get_client_ip(request),
        severity="INFO",
    )

    return {"message": "密碼已成功重設"}


@router.patch("/users/{user_id}/toggle-status", response_model=User)
async def toggle_user_status(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """
    Toggle user active status (admin only)
    """
    if (
        current_user.role != UserRole.SUPER_ADMIN
        and current_user.role != UserRole.MANAGER
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="權限不足")

    result = await db.execute(select(UserModel).where(UserModel.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="用戶不存在")

    user.is_active = not user.is_active
    await db.commit()
    await db.refresh(user)

    return user


@router.post("/change-password")
async def change_password(
    request: Request,
    password_data: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(rate_limit_by_user),
) -> Any:
    """
    Change current user's password with policy enforcement
    """
    if not verify_password(
        password_data.current_password, current_user.hashed_password
    ):
        # Record failed attempt
        client_ip = RequestValidator.get_client_ip(request)
        await SecurityAudit.log_security_event(
            "failed_password_change",
            user_id=current_user.id,
            ip_address=client_ip,
            severity="WARNING",
        )

        raise HTTPException(status_code=400, detail="目前密碼錯誤")

    # Validate new password against policy
    is_valid, errors = PasswordValidator.validate_password(
        password_data.new_password, current_user.username
    )

    if not is_valid:
        raise HTTPException(
            status_code=400, detail=f"新密碼不符合要求: {'; '.join(errors)}"
        )

    # Check password history
    new_hash = get_password_hash(password_data.new_password)
    if not await PasswordValidator.check_password_history(current_user.id, new_hash):
        raise HTTPException(status_code=400, detail="不能使用最近使用過的密碼")

    # Update password
    current_user.hashed_password = new_hash
    current_user.password_changed_at = datetime.utcnow()
    await db.commit()

    # Update password history
    await PasswordValidator.update_password_history(current_user.id, new_hash)

    # Revoke all existing sessions
    await SessionManager.revoke_all_sessions(current_user.id)

    # Log password change
    client_ip = RequestValidator.get_client_ip(request)
    await SecurityAudit.log_security_event(
        "password_changed",
        user_id=current_user.id,
        ip_address=client_ip,
        severity="INFO",
    )

    return {"message": "密碼已成功更改，請重新登入"}


@router.post("/2fa/setup", response_model=TwoFactorSetup)
async def setup_two_factor(
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(require_secure_auth),
) -> Any:
    """
    Setup two-factor authentication for current user
    """
    if current_user.two_factor_enabled:
        raise HTTPException(status_code=400, detail="雙因素認證已啟用")

    # Generate secret
    secret = TwoFactorAuth.generate_secret()

    # Generate QR code
    qr_code = TwoFactorAuth.generate_qr_code(current_user.username, secret)

    # Generate backup codes
    backup_codes = TwoFactorAuth.generate_backup_codes()

    # Store temporarily (not enabled yet)
    key = f"2fa:setup:{current_user.id}"
    await cache.set(
        key,
        {"secret": secret, "backup_codes": backup_codes},
        expire=600,  # 10 minutes to complete setup
    )

    return {"secret": secret, "qr_code": qr_code, "backup_codes": backup_codes}


@router.post("/2fa/verify")
async def verify_two_factor_setup(
    verify_data: TwoFactorVerify,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """
    Verify and enable two-factor authentication
    """
    # Get setup data
    key = f"2fa:setup:{current_user.id}"
    setup_data = await cache.get(key)

    if not setup_data:
        raise HTTPException(status_code=400, detail="請先開始雙因素認證設定")

    setup_data = eval(setup_data)  # Safe since we control the data

    # Verify TOTP code
    if not TwoFactorAuth.verify_totp(setup_data["secret"], verify_data.code):
        raise HTTPException(status_code=400, detail="驗證碼無效")

    # Enable 2FA
    current_user.two_factor_secret = setup_data["secret"]
    current_user.two_factor_enabled = True

    # Store backup codes (should be encrypted in production)
    backup_key = f"2fa:backup:{current_user.id}"
    await cache.set(backup_key, str(setup_data["backup_codes"]))

    await db.commit()

    # Clean up setup data
    await cache.delete(key)

    # Log 2FA enablement
    await SecurityAudit.log_security_event(
        "2fa_enabled", user_id=current_user.id, severity="INFO"
    )

    return {"message": "雙因素認證已成功啟用"}


@router.post("/2fa/disable")
async def disable_two_factor(
    password: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(require_secure_auth),
) -> Any:
    """
    Disable two-factor authentication
    """
    if not current_user.two_factor_enabled:
        raise HTTPException(status_code=400, detail="雙因素認證未啟用")

    # Verify password
    if not verify_password(password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="密碼錯誤")

    # Disable 2FA
    current_user.two_factor_enabled = False
    current_user.two_factor_secret = None

    await db.commit()

    # Clean up backup codes
    backup_key = f"2fa:backup:{current_user.id}"
    await cache.delete(backup_key)

    # Log 2FA disablement
    await SecurityAudit.log_security_event(
        "2fa_disabled", user_id=current_user.id, severity="WARNING"
    )

    return {"message": "雙因素認證已停用"}


@router.post("/logout")
async def logout(
    request: Request, current_user: UserModel = Depends(get_current_user)
) -> Any:
    """
    Logout current session
    """
    # Get session ID from token
    token = request.headers.get("Authorization", "").replace("Bearer ", "")

    try:
        payload = decode_access_token(token)
        session_id = payload.get("session_id")

        if session_id:
            await SessionManager.revoke_session(session_id)
    except:
        pass

    # Log logout
    client_ip = RequestValidator.get_client_ip(request)
    await SecurityAudit.log_security_event(
        "logout", user_id=current_user.id, ip_address=client_ip, severity="INFO"
    )

    return {"message": "已成功登出"}


@router.post("/logout-all")
async def logout_all_sessions(
    current_user: UserModel = Depends(require_secure_auth),
) -> Any:
    """
    Logout all sessions for current user
    """
    await SessionManager.revoke_all_sessions(current_user.id)

    # Log logout all
    await SecurityAudit.log_security_event(
        "logout_all_sessions", user_id=current_user.id, severity="WARNING"
    )

    return {"message": "所有裝置已登出"}


@router.get("/sessions")
async def get_active_sessions(
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """
    Get all active sessions for current user
    """
    sessions_key = f"sessions:user:{current_user.id}"
    sessions = await cache.get(sessions_key)

    if sessions:
        sessions_list = eval(sessions)
        return {"sessions": sessions_list}

    return {"sessions": []}
