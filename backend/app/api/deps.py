"""
Simplified API dependencies - Direct and simple!
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError, jwt

from app.core.database import get_db
from app.models import User
from app.core.config import settings

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# JWT settings
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current user from JWT token
    SYNC version - no async complications!
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="無法驗證憑證",  # "Could not validate credentials"
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode JWT token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # Get user from database - SYNC query!
    user = db.query(User).filter(User.email == email).first()
    
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="帳號已被停用"  # "Account has been deactivated"
        )
    
    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current active user
    Just an alias for get_current_user since we already check is_active
    """
    return current_user


def require_role(allowed_roles: list):
    """
    Dependency to check user role
    
    Usage:
        @router.get("/admin-only")
        def admin_endpoint(
            current_user = Depends(require_role(["admin"]))
        ):
            return {"message": "Admin access granted"}
    """
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="權限不足"  # "Insufficient permissions"
            )
        return current_user
    return role_checker


def get_optional_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get current user if token is provided, otherwise return None
    Useful for endpoints that work with or without authentication
    """
    if not token:
        return None
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return None
    except JWTError:
        return None
    
    user = db.query(User).filter(User.email == email).first()
    
    if user and user.is_active:
        return user
    
    return None


# Commonly used role checkers
def require_admin(current_user: User = Depends(require_role(["admin"]))):
    """Require admin role"""
    return current_user


def require_manager(current_user: User = Depends(require_role(["admin", "manager"]))):
    """Require admin or manager role"""
    return current_user


def require_staff(current_user: User = Depends(require_role(["admin", "manager", "staff"]))):
    """Require admin, manager, or staff role"""
    return current_user


def require_driver(current_user: User = Depends(require_role(["admin", "manager", "driver"]))):
    """Require admin, manager, or driver role"""
    return current_user