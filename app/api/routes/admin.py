"""
Admin Routes
==============
GET /api/v1/admin/budget    — Current budget status and spend breakdown
GET /api/v1/admin/models    — Model availability and rate limit status

These are for your team to monitor the system during demos and pilot.
In production, these would be behind authentication.
"""

from datetime import datetime, timezone, date
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models.api_usage import ApiUsage
from app.schemas.api import BudgetStatusResponse
from app.core.config import settings
from app.core.constants import MODEL_COSTS, PROVIDER_RATE_LIMITS

router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])


@router.get("/budget", response_model=BudgetStatusResponse)
async def get_budget_status(db: AsyncSession = Depends(get_db)):
    """
    Get current day's API spending vs budget cap.
    Determines which budget tier we're in (green/yellow/red).
    """
    today = date.today()

    # Total spend today
    result = await db.execute(
        select(
            func.sum(ApiUsage.estimated_cost_usd),
            func.count(ApiUsage.id),
        ).where(
            func.date(ApiUsage.created_at) == today
        )
    )
    row = result.one()
    spent_today = row[0] or 0.0
    calls_today = row[1] or 0

    # Spend by provider
    provider_result = await db.execute(
        select(
            ApiUsage.model_provider,
            func.sum(ApiUsage.estimated_cost_usd),
        ).where(
            func.date(ApiUsage.created_at) == today
        ).group_by(ApiUsage.model_provider)
    )
    cost_by_provider = {row[0]: round(row[1], 4) for row in provider_result.all()}

    # Determine budget tier
    cap = settings.daily_budget_cap_usd
    ratio = spent_today / cap if cap > 0 else 0
    if ratio < settings.budget_tier_green:
        tier = "green"
    elif ratio < settings.budget_tier_yellow:
        tier = "yellow"
    else:
        tier = "red"

    return BudgetStatusResponse(
        daily_cap_usd=cap,
        spent_today_usd=round(spent_today, 4),
        remaining_usd=round(max(0, cap - spent_today), 4),
        budget_tier=tier,
        calls_today=calls_today,
        cost_by_provider=cost_by_provider,
    )


@router.get("/models")
async def get_model_status():
    """
    Show which models are configured, their costs, and rate limits.
    Helps your team understand what's available.
    """
    models = []
    for model_id, costs in MODEL_COSTS.items():
        models.append({
            "model": model_id.value,
            "cost_per_1m_input": costs["input"],
            "cost_per_1m_output": costs["output"],
            "is_free": costs["input"] == 0 and costs["output"] == 0,
        })

    providers = []
    for provider, limits in PROVIDER_RATE_LIMITS.items():
        providers.append({
            "provider": provider.value,
            "requests_per_minute": limits["rpm"],
            "requests_per_day": limits["rpd"],
            "api_key_configured": _is_provider_configured(provider.value),
        })

    return {
        "models": models,
        "providers": providers,
        "budget_cap_usd": settings.daily_budget_cap_usd,
    }


def _is_provider_configured(provider: str) -> bool:
    """Check if a provider's API key is set."""
    key_map = {
        "anthropic": settings.anthropic_api_key,
        "openai": settings.openai_api_key,
        "google": settings.google_ai_api_key,
        "groq": settings.groq_api_key,
    }
    key = key_map.get(provider)
    return bool(key and len(key) > 0)
