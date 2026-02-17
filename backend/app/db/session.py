"""
Database session management
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from typing import Generator, AsyncGenerator
from ..core.config import settings

# Create sync engine (for migrations and scripts)
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DB_ECHO,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

# Create async engine (for FastAPI)
async_database_url = settings.DATABASE_URL.replace(
    "postgresql://",
    "postgresql+asyncpg://"
)

async_engine = create_async_engine(
    async_database_url,
    echo=settings.DB_ECHO,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

# Session factories
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for getting sync database session
    Used in background tasks and scripts
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting async database session
    Used in FastAPI endpoints
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
