from typing import AsyncGenerator
import logging

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import database
from app.core.security import decode_access_token
from app.models.user import User as UserModel
from app.schemas.user import TokenData

logger = logging.getLogger(__name__)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session with proper error handling and initialization."""
    
    # Log the current state
    logger.info(f"get_db called - async_session_maker is {'None' if database.async_session_maker is None else 'initialized'}")
    logger.info(f"get_db called - engine is {'None' if database.engine is None else 'initialized'}")
    
    if database.async_session_maker is None:
        logger.warning("Database session maker is None, attempting to initialize...")
        
        # Try to initialize the database if it hasn't been initialized yet
        try:
            await database.initialize_database()
            logger.info("Database initialization completed")
        except Exception as e:
            logger.error(f"Database initialization failed: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Database service unavailable: {str(e)}"
            )
    
    # Double-check after initialization
    if database.async_session_maker is None:
        logger.error("Database session maker is still None after initialization attempt")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service not available - initialization failed"
        )
    
    try:
        async with database.async_session_maker() as session:
            # Test the session is working
            await session.execute(select(1))
            yield session
    except Exception as e:
        logger.error(f"Database session error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection error: {str(e)}"
        )


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
