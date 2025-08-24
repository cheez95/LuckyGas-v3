"""
Simplified authentication endpoints - SYNC version, no async complications!
This fixes the MissingGreenlet errors
"""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from jose import JWTError, jwt

from app.core.database import get_db
from app.models import User, UserRole
from app.schemas.auth import Token, TokenData, UserLogin, UserResponse
from app.core.config import settings
from app.core.cache import auth_cache, cache_result
from app.core.security import verify_password, get_password_hash  # Import from security module
from pydantic import BaseModel
from fastapi import Response

router = APIRouter()

# Simple JSON login model for quick testing
class LoginRequest(BaseModel):
    username: str
    password: str

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# JWT settings
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# TEMPORARY SIMPLIFIED JSON LOGIN - NO BCRYPT FOR IMMEDIATE TESTING
@router.post("/login/json")
def login_json_simple(request: LoginRequest):
    """
    Simplified JSON login endpoint for immediate testing
    Bypasses bcrypt to eliminate performance issues
    """
    print(f"Login attempt for: {request.username}")
    
    # Hardcoded admin credentials for immediate testing
    if request.username == "admin@luckygas.com" and request.password == "admin-password-2025":
        # Create token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": request.username, "role": "admin"},
            expires_delta=access_token_expires
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": 1,
                "email": request.username,
                "full_name": "System Administrator",
                "role": "admin"
            }
        }
    
    # Return 401 for invalid credentials
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials"
    )

# Add OPTIONS handler for CORS preflight
@router.options("/login/json")
def login_json_options():
    """Handle CORS preflight for JSON login"""
    return Response(
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization"
        }
    )

# Add OPTIONS handler for main login endpoint
@router.options("/login")
def login_options():
    """Handle CORS preflight for main login"""
    return Response(
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization"
        }
    )

@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)  # SYNC SESSION - NO ASYNC!
):
    """
    Login endpoint - Authenticate against database
    """
    print(f"Form login attempt for: {form_data.username}")
    
    # Check user in database
    user = db.query(User).filter(User.email == form_data.username).first()
    
    if not user:
        print(f"User not found: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Verify password using passlib
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    if not pwd_context.verify(form_data.password, user.hashed_password):
        print(f"Invalid password for user: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "role": user.role.value},
        expires_delta=access_token_expires
    )
    
    # Return token and user info
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role.value
        }
    }


@router.post("/login/form", response_model=Token)
def login_form(
    username: str,
    password: str,
    db: Session = Depends(get_db)
):
    """
    Alternative login endpoint for form data
    Same logic, different input format
    """
    # Simple, direct query
    user = db.query(User).filter(
        User.email == username
    ).first()
    
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="帳號或密碼錯誤"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="帳號已被停用"
        )
    
    # Create token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "role": user.role},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role
        }
    }


# Dependency functions (moved before usage)
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current user from JWT token
    Used as dependency in protected endpoints
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="無法驗證憑證",  # "Could not validate credentials" in Chinese
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
            detail="帳號已被停用"
        )
    
    return user


def require_role(allowed_roles: list):
    """
    Dependency to check user role
    Usage: current_user = Depends(require_role(["admin", "manager"]))
    """
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="權限不足"  # "Insufficient permissions" in Chinese
            )
        return current_user
    return role_checker


# Protected routes that use get_current_user
@router.get("/me", response_model=UserResponse)
def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current user information"""
    return current_user


@router.post("/refresh", response_model=Token)
def refresh_token(
    current_user: User = Depends(get_current_user)
):
    """
    Refresh access token
    Creates a new token for the current user
    """
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": current_user.email, "role": current_user.role},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "role": current_user.role
        }
    }


@router.post("/logout")
def logout():
    """
    Logout endpoint
    Client should remove token from storage
    """
    return {"message": "登出成功"}  # "Logout successful" in Chinese


# Create initial admin user if not exists
def create_initial_admin(db: Session):
    """
    Create initial admin user for testing
    Run this once when setting up the system
    """
    # Check if admin exists
    admin = db.query(User).filter(
        User.email == settings.FIRST_SUPERUSER
    ).first()
    
    if not admin:
        # Create admin user
        admin = User(
            email=settings.FIRST_SUPERUSER,
            username="admin",
            full_name="System Administrator",
            hashed_password=get_password_hash(settings.FIRST_SUPERUSER_PASSWORD),
            role=UserRole.SUPER_ADMIN,
            is_active=True
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        print(f"✅ Admin user created: {settings.FIRST_SUPERUSER}")
    else:
        print("✓ Admin user already exists")
    
    return admin