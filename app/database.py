"""
Database Configuration (FIXED)
===============================
Changes:
  - get_db NO LONGER auto-commits. Routes manage their own transactions.
  - This prevents partial commits when background tasks fail.
"""

from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

engine_kwargs = {"echo": settings.app_debug}
if not settings.database_url.startswith("sqlite"):
    engine_kwargs.update({
        "pool_size": 5,
        "max_overflow": 5,
        "pool_timeout": 30,
        "pool_recycle": 1800,
    })

engine = create_async_engine(settings.database_url, **engine_kwargs)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

class Base(DeclarativeBase):
    pass

async def get_db() -> AsyncSession:
    """
    Dependency injection for FastAPI routes.
    IMPORTANT: The route must call await db.commit() explicitly.
    The session is rolled back on unhandled exceptions.
    """
    async with async_session() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

@asynccontextmanager
async def get_db_for_background() -> AsyncSession:
    """
    For BackgroundTasks or cron jobs that need a standalone session.
    Usage:
        async with get_db_for_background() as db:
            ...
    """
    session = async_session()
    try:
        yield session
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()

async def init_db():
    """Create all tables. Used on startup for MVP."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def close_db():
    """Graceful shutdown."""
    await engine.dispose()
