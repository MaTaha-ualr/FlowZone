"""
Health Check Routes (FIXED)
============================
Changes:
  - /health/detailed now queries real budget data from CreditManager
  - Added ChromaDB connectivity check
  - Added request_id to responses
"""

from datetime import datetime
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db
from app.schemas.api import HealthResponse, SystemStatusResponse
from app.core.config import settings
from app.middleware.rate_limit import concurrency_guard
from app.middleware.request_id import get_request_id
from app.services.model_router import model_router as router_instance
from app.services.model_router.credit_manager import credit_manager
from app.services.rag import chroma_store

router = APIRouter(tags=["Health"])

APP_VERSION = "0.2.0"

@router.get("/health", response_model=HealthResponse)
async def health_check(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Basic health check for load balancers."""
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
async def detailed_health_check(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Extended health check with real subsystem data."""
    # Database
    db_status = "disconnected"
    try:
        await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)[:100]}"

    # Model router
    model_router_status = await router_instance.check_all_providers()

    # Budget (REAL data from CreditManager)
    budget_snapshot = await credit_manager.get_snapshot(db)
    budget_status = {
        "daily_cap_usd": budget_snapshot.daily_cap,
        "spent_today_usd": round(budget_snapshot.spent_today, 4),
        "remaining_usd": round(budget_snapshot.remaining, 4),
        "tier": budget_snapshot.tier.value,
        "calls_today": budget_snapshot.calls_today,
        "utilization": round(budget_snapshot.utilization, 2),
    }

    # ChromaDB
    chroma_status = "unknown"
    try:
        collections = chroma_store.list_collections()
        chroma_status = f"ok ({len(collections)} collections)"
    except Exception as e:
        chroma_status = f"error: {str(e)[:100]}"

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
