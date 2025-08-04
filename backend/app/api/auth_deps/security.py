"""
Security-related dependencies for FastAPI routes.
"""

from typing import Annotated, Optional

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import (APIKeyHeader, HTTPAuthorizationCredentials,
                              HTTPBearer)
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.cache import cache
from app.core.security import (AccountLockout, APIKeyManager, SessionManager,
                               decode_access_token)
from app.core.security_config import get_2fa_config
from app.middleware.security import CSRFProtection, SecurityValidation
from app.models.user import User
from app.utils.security_utils import RequestValidator, SecurityAudit

# Security schemes
bearer_scheme = HTTPBearer()
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(
    api_key: Annotated[Optional[str], Depends(api_key_header)],
) -> Optional[dict]:
    """Verify API key for B2B access."""
    if not api_key:
        return None

    key_data = await APIKeyManager.validate_api_key(api_key)
    if not key_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="無效的 API 金鑰"
        )

    return key_data


async def get_current_user_or_api_key(
    user: Annotated[Optional[User], Depends(get_current_user)],
    api_key_data: Annotated[Optional[dict], Depends(verify_api_key)],
) -> dict:
    """Get current user or API key authentication."""
    if user:
        return {"type": "user", "data": user}
    elif api_key_data:
        return {"type": "api_key", "data": api_key_data}
    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="需要認證")


def require_scopes(*required_scopes: str):
    """Dependency to require specific API scopes."""

    async def check_scopes(auth: Annotated[dict, Depends(get_current_user_or_api_key)]):
        if auth["type"] == "user":
            # Users have all scopes by default (can be refined based on roles)
            return auth

        # Check API key scopes
        api_scopes = auth["data"].get("scopes", [])
        for scope in required_scopes:
            if scope not in api_scopes:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"權限不足: 需要 {scope} 權限",
                )

        return auth

    return check_scopes


async def verify_2fa(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    totp_code: Optional[str] = Header(None, alias="X-TOTP-Code"),
    backup_code: Optional[str] = Header(None, alias="X-Backup-Code"),
):
    """Verify 2FA for sensitive operations."""
    config = get_2fa_config()

    if not config.enabled:
        return current_user

    # Check if user has 2FA enabled
    if not current_user.two_factor_enabled:
        return current_user

    # Check trusted device
    client_ip = RequestValidator.get_client_ip(request)
    trusted_key = f"2fa:trusted:{current_user.id}:{client_ip}"

    if await cache.get(trusted_key):
        return current_user

    # Verify TOTP code
    if totp_code:
        from app.core.security import TwoFactorAuth

        if TwoFactorAuth.verify_totp(current_user.two_factor_secret, totp_code):
            # Mark device as trusted if requested
            if request.headers.get("X-Trust-Device") == "true":
                await cache.set(
                    trusted_key, "1", expire=config.trusted_device_days * 86400
                )
            return current_user

    # Verify backup code
    if backup_code:
        # TODO: Implement backup code verification
        pass

    raise HTTPException(
        status_code=status.HTTP_428_PRECONDITION_REQUIRED,
        detail="需要雙因素認證",
        headers={"X-2FA-Required": "true"},
    )


async def verify_csrf_token(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    csrf_token: str = Header(None, alias="X-CSRF-Token"),
):
    """Verify CSRF token for state-changing operations."""
    if request.method in ["GET", "HEAD", "OPTIONS"]:
        return current_user

    if not csrf_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="缺少 CSRF 令牌"
        )

    # Verify token
    is_valid = await CSRFProtection.validate_csrf_token(request, csrf_token)

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="無效的 CSRF 令牌"
        )

    return current_user


async def check_account_lockout(
    request: Request, db: Annotated[AsyncSession, Depends(get_db)]
):
    """Check if account or IP is locked out."""
    client_ip = RequestValidator.get_client_ip(request)

    # Check IP lockout
    if await AccountLockout.is_locked(client_ip, is_ip=True):
        await SecurityAudit.log_security_event(
            "blocked_access",
            ip_address=client_ip,
            details={"reason": "ip_lockout"},
            severity="WARNING",
        )

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="您的 IP 已被暫時封鎖，請稍後再試",
        )


def validate_input(validator: SecurityValidation = SecurityValidation()):
    """Dependency for input validation."""

    def validate(data: dict):
        # Check all string values for injection attempts
        for key, value in data.items():
            if isinstance(value, str):
                if validator.is_sql_injection_attempt(value):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"偵測到無效的輸入: {key}",
                    )

                if validator.is_xss_attempt(value):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"偵測到不安全的內容: {key}",
                    )

        return data

    return validate


async def rate_limit_by_user(
    current_user: Annotated[User, Depends(get_current_user)], request: Request
):
    """Apply rate limiting per user for specific endpoints."""
    # This is handled by middleware, but we can add extra checks here
    endpoint = request.url.path
    user_id = current_user.id

    # Example: Limit password changes
    if endpoint.endswith("/change-password"):
        key = f"rate_limit:password_change:{user_id}"
        count = await cache.get(key)

        if count and int(count) >= 3:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="密碼變更次數過多，請稍後再試",
            )

        # Increment counter
        await cache.set(key, str(int(count) + 1 if count else 1), expire=3600)

    return current_user


# Composite dependencies for different security levels
async def require_basic_auth(
    current_user: Annotated[User, Depends(get_current_user)],
    _: Annotated[None, Depends(check_account_lockout)],
) -> User:
    """Basic authentication with lockout check."""
    return current_user


async def require_secure_auth(
    current_user: Annotated[User, Depends(verify_2fa)],
    _: Annotated[None, Depends(check_account_lockout)],
) -> User:
    """Secure authentication with 2FA."""
    return current_user


async def require_admin_auth(
    current_user: Annotated[User, Depends(require_secure_auth)],
) -> User:
    """Admin authentication with enhanced security."""
    if current_user.role not in ["admin", "super_admin"]:
        await SecurityAudit.log_security_event(
            "permission_denied",
            user_id=current_user.id,
            details={"required_role": "admin", "user_role": current_user.role},
            severity="WARNING",
        )

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="需要管理員權限"
        )

    return current_user


# Export dependencies
__all__ = [
    "verify_api_key",
    "get_current_user_or_api_key",
    "require_scopes",
    "verify_2fa",
    "verify_csrf_token",
    "check_account_lockout",
    "validate_input",
    "rate_limit_by_user",
    "require_basic_auth",
    "require_secure_auth",
    "require_admin_auth",
]
