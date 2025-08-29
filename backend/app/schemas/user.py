from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from app.models.user import UserRole
from typing import Optional, List


class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: str
    is_active: bool = True
    role: UserRole = UserRole.OFFICE_STAFF


class UserCreate(UserBase):
    password: str

    @field_validator("password")
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("密碼長度必須至少8個字符")
        return v


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    role: Optional[UserRole] = None


class User(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    two_factor_enabled: bool = False
    password_changed_at: Optional[datetime] = None


class Token(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: Optional[int] = None
    requires_2fa: Optional[bool] = False


class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("密碼長度必須至少8個字符")
        return v


class TwoFactorSetup(BaseModel):
    secret: str
    qr_code: str
    backup_codes: List[str]


class TwoFactorVerify(BaseModel):
    code: str

    @field_validator("code")
    def validate_code(cls, v):
        if len(v) != 6 or not v.isdigit():
            raise ValueError("驗證碼必須是6位數字")
        return v


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("密碼長度必須至少8個字符")
        return v


class APIKeyCreate(BaseModel):
    name: str
    scopes: List[str]
    expires_in_days: Optional[int] = None


class APIKeyResponse(BaseModel):
    api_key: str
    key_id: str
    name: str
    scopes: List[str]
    created_at: datetime
    expires_at: Optional[datetime] = None
