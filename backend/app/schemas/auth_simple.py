"""
Simplified authentication schemas
"""
from typing import Optional
from pydantic import BaseModel, EmailStr
from datetime import datetime


class Token(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str = "bearer"
    user: Optional[dict] = None


class TokenData(BaseModel):
    """Token payload data"""
    email: Optional[str] = None
    role: Optional[str] = None


class UserLogin(BaseModel):
    """User login request"""
    username: EmailStr  # Using email as username
    password: str


class UserResponse(BaseModel):
    """User response model"""
    id: int
    email: EmailStr
    username: Optional[str]
    full_name: Optional[str]
    role: str
    is_active: bool
    created_at: datetime
    
    class Config:
        orm_mode = True


class UserCreate(BaseModel):
    """Create new user"""
    email: EmailStr
    username: Optional[str]
    full_name: Optional[str]
    password: str
    role: str = "customer"


class UserUpdate(BaseModel):
    """Update user"""
    email: Optional[EmailStr]
    username: Optional[str]
    full_name: Optional[str]
    password: Optional[str]
    role: Optional[str]
    is_active: Optional[bool]