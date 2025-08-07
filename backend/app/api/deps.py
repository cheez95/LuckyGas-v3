from typing import AsyncGenerator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker
from app.core.security import decode_access_token
from app.models.user import User as UserModel
from app.schemas.user import TokenData

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api / v1 / auth / login")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


async def get_current_user(
    db: AsyncSession = Depends(get_db), token: str = Depends(oauth2_scheme)
) -> UserModel:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="無法驗證憑據",
        headers={"WWW - Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username, role=role)
    except (JWTError, ValueError):
        raise credentials_exception

    result = await db.execute(
        select(UserModel).where(UserModel.username == token_data.username)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=400, detail="用戶已停用")

    return user


async def get_current_active_user(
    current_user: UserModel = Depends(get_current_user),
) -> UserModel:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="用戶已停用")
    return current_user


def check_permission(required_permission: str):
    async def permission_checker(
        current_user: UserModel = Depends(get_current_active_user),
    ) -> UserModel:
        # For now, just return the user - implement permission checking later
        return current_user

    return permission_checker


async def get_current_active_superuser(
    current_user: UserModel = Depends(get_current_user),
) -> UserModel:
    if current_user.role != "super_admin":
        raise HTTPException(status_code=400, detail="權限不足")
    return current_user
