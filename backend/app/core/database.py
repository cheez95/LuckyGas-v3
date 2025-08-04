from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# Create async engine with connection pooling
engine = create_async_engine(
    settings.DATABASE_URL.replace("postgresql+psycopg2://", "postgresql+asyncpg://"),
    echo=False,
    future=True,
    # Connection pool settings from config
    pool_size=settings.database.pool_size,
    max_overflow=settings.database.max_overflow,
    pool_timeout=settings.database.pool_timeout,
    pool_recycle=settings.database.pool_recycle,
    pool_pre_ping=settings.database.pool_pre_ping,
    # Performance settings
    connect_args={
        "server_settings": {
            "application_name": settings.PROJECT_NAME.lower().replace(" ", "_"),
            "jit": "off",
            "statement_timeout": str(settings.database.statement_timeout),
        },
        "command_timeout": settings.database.command_timeout,
        "timeout": 10,
        # Prepared statement cache
        "prepared_statement_cache_size": 0,  # Disable for better compatibility
        # Note: keepalives parameters are not supported by asyncpg
        # They are only for psycopg2/libpq connections
    },
)

# Create async session factory
async_session_maker = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


class Base(DeclarativeBase):
    pass


async def create_db_and_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session
