"""
Database Configuration
=======================
Async PostgreSQL connection using SQLAlchemy 2.0 + asyncpg.

Architecture Note:
    We use async everywhere because:
    1. FastAPI is async-native — blocking DB calls would kill concurrency
    2. With 5 concurrent users, async lets us handle them efficiently
       on a single process (no need for multiple workers yet)
    3. All LLM API calls are also async — the whole request pipeline
       stays non-blocking

    For the MVP on Railway, a single Postgres instance handles everything.
    On AWS production, this would point to RDS.
"""

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings


# Create the async engine
# pool_size=5 matches our max concurrent users
# max_overflow=5 gives headroom for background tasks (trust score calc, etc.)
engine = create_async_engine(
    settings.database_url,
    echo=settings.app_debug,  # Log SQL in development
    pool_size=5,
    max_overflow=5,
    pool_timeout=30,
    pool_recycle=1800,  # Recycle connections every 30 min (Railway/cloud compat)
)

# Session factory — each request gets its own session
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Prevents lazy-load issues in async context
)


# Base class for all models
class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    """
    Dependency injection for FastAPI routes.
    Usage:
        @router.get("/something")
        async def get_something(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Create all tables. Used on startup for MVP. Alembic for production."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Graceful shutdown."""
    await engine.dispose()
