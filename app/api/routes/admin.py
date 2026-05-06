"""
Admin Routes (FIXED)
=====================
Changes:
  - Auth required (any authenticated user for demo; tighten for prod)
  - Real budget data from CreditManager
  - Added request_id logging
"""

from datetime import date
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models.api_usage import ApiUsage
from app.schemas.api import BudgetStatusResponse
from app.core.config import settings
from app.core.constants import MODEL_COSTS, PROVIDER_RATE_LIMITS
from app.core.security import get_current_user, require_admin
from app.services.model_router.credit_manager import credit_manager
from app.middleware.request_id import get_request_id

router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])

@router.get("/budget", response_model=BudgetStatusResponse)
async def get_budget_status(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin),
):
    """Current budget status with real data from CreditManager."""
    snapshot = await credit_manager.get_snapshot(db)

    # Spend by provider (today)
    today = date.today()
    provider_result = await db.execute(
        select(
            ApiUsage.model_provider,
            func.sum(ApiUsage.estimated_cost_usd),
        ).where(
            func.date(ApiUsage.created_at) == today
        ).group_by(ApiUsage.model_provider)
    )
    cost_by_provider = {row[0]: round(row[1], 4) for row in provider_result.all()}

    return BudgetStatusResponse(
        daily_cap_usd=snapshot.daily_cap,
        spent_today_usd=round(snapshot.spent_today, 4),
        remaining_usd=round(snapshot.remaining, 4),
        budget_tier=snapshot.tier.value,
        calls_today=snapshot.calls_today,
        cost_by_provider=cost_by_provider,
    )

@router.get("/models")
async def get_model_status(
    request: Request,
    current_user = Depends(require_admin),
):
    """Model availability and rate limits."""
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
    key_map = {
        "anthropic": settings.anthropic_api_key,
        "openai": settings.openai_api_key,
        "google": settings.google_ai_api_key,
        "groq": settings.groq_api_key,
    }
    key = key_map.get(provider)
    return bool(key and len(key) > 0)
