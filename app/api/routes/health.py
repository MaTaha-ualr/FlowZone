"""
Health Check Routes
====================
GET /health          — Simple health check (for Railway/load balancers)
GET /health/detailed — Extended status with subsystem checks

This is the FIRST endpoint to get live. If this works, your
deployment pipeline works.
"""

from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db
from app.schemas.api import HealthResponse, SystemStatusResponse
from app.core.config import settings
from app.middleware.rate_limit import concurrency_guard
from app.services.model_router import model_router as router_instance

router = APIRouter(tags=["Health"])

APP_VERSION = "0.1.0"


@router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Basic health check. Returns 200 if the app and database are reachable.
    Railway uses this to know your service is alive.
    """
    # Test database connection
    db_status = "disconnected"
    try:
        await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "error"

    return HealthResponse(
        status="healthy" if db_status == "connected" else "degraded",
        version=APP_VERSION,
        environment=settings.app_env.value,
        database=db_status,
        timestamp=datetime.utcnow(),
    )


@router.get("/health/detailed", response_model=SystemStatusResponse)
async def detailed_health_check(db: AsyncSession = Depends(get_db)):
    """
    Extended health check with all subsystem statuses.
    Used by your team to monitor the system — not for load balancers.
    """
    # Database check
    db_status = "disconnected"
    try:
        await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)[:100]}"

    # Model router status — check actual provider availability
    model_router_status = await router_instance.check_all_providers()

    # Budget status placeholder (will be real once Credit Manager is built)
    budget_status = {
        "daily_cap_usd": settings.daily_budget_cap_usd,
        "spent_today_usd": 0.0,  # TODO: query api_usage table
        "tier": "green",
    }

    return SystemStatusResponse(
        status="healthy" if db_status == "connected" else "degraded",
        version=APP_VERSION,
        environment=settings.app_env.value,
        database=db_status,
        model_router=model_router_status,
        budget=budget_status,
        active_sessions=concurrency_guard.active_count,
        timestamp=datetime.utcnow(),
    )
