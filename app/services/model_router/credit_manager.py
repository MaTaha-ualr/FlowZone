"""
Credit Manager
================
Tracks API spending in real-time and determines the current budget tier.

Budget Tiers:
    GREEN  (< 60% of daily cap)  — All models available
    YELLOW (60-85% of daily cap)  — Strategist downgrades to free
    RED    (> 85% of daily cap)   — Everything on free models only

Architecture Note:
    The Credit Manager is queried BEFORE every paid API call.
    It uses an in-memory cache (updated from DB) to avoid
    hitting Postgres on every single message.
    Cache is refreshed every 60 seconds or after every paid call.
"""

import time
from datetime import date, datetime, timezone
from enum import Enum
from dataclasses import dataclass
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.api_usage import ApiUsage
from app.core.config import settings


class BudgetTier(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


@dataclass
class BudgetSnapshot:
    """Current budget state — cached in memory."""
    daily_cap: float
    spent_today: float
    calls_today: int
    tier: BudgetTier
    last_refreshed: float  # timestamp

    @property
    def remaining(self) -> float:
        return max(0, self.daily_cap - self.spent_today)

    @property
    def utilization(self) -> float:
        return self.spent_today / self.daily_cap if self.daily_cap > 0 else 0


class CreditManager:
    """
    Manages API credit budget with tiered fallback behavior.

    Usage:
        credit_mgr = CreditManager()
        tier = await credit_mgr.get_budget_tier(db)
        if tier == BudgetTier.RED:
            # Use free models only
        
        # After a paid API call:
        await credit_mgr.log_usage(db, provider, model, tokens_in, tokens_out, cost)
    """

    CACHE_TTL_SECONDS = 60  # Refresh cache every 60 seconds

    def __init__(self):
        self._cache: Optional[BudgetSnapshot] = None

    async def get_budget_tier(self, db: AsyncSession) -> BudgetTier:
        """Get the current budget tier. Uses cache if fresh."""
        snapshot = await self._get_snapshot(db)
        return snapshot.tier

    async def get_snapshot(self, db: AsyncSession) -> BudgetSnapshot:
        """Get full budget snapshot (for admin dashboard)."""
        return await self._get_snapshot(db)

    async def can_use_paid_model(self, db: AsyncSession) -> bool:
        """Quick check: are paid models currently allowed?"""
        tier = await self.get_budget_tier(db)
        return tier != BudgetTier.RED

    async def _get_snapshot(self, db: AsyncSession) -> BudgetSnapshot:
        """Get or refresh the budget snapshot."""
        now = time.time()
        if self._cache and (now - self._cache.last_refreshed) < self.CACHE_TTL_SECONDS:
            return self._cache

        # Query today's spending from DB
        today = date.today()
        result = await db.execute(
            select(
                func.coalesce(func.sum(ApiUsage.estimated_cost_usd), 0),
                func.count(ApiUsage.id),
            ).where(
                func.date(ApiUsage.created_at) == today
            )
        )
        row = result.one()
        spent = float(row[0])
        calls = int(row[1])

        # Determine tier
        cap = settings.daily_budget_cap_usd
        ratio = spent / cap if cap > 0 else 0

        if ratio < settings.budget_tier_green:
            tier = BudgetTier.GREEN
        elif ratio < settings.budget_tier_yellow:
            tier = BudgetTier.YELLOW
        else:
            tier = BudgetTier.RED

        self._cache = BudgetSnapshot(
            daily_cap=cap,
            spent_today=spent,
            calls_today=calls,
            tier=tier,
            last_refreshed=now,
        )
        return self._cache

    async def log_usage(
        self,
        db: AsyncSession,
        provider: str,
        model: str,
        task_type: str,
        tokens_in: int,
        tokens_out: int,
        cost: float,
        user_id=None,
        session_id=None,
        response_time_ms: int = 0,
        success: bool = True,
        error_message: str = None,
    ):
        """
        Log an API call to the usage table and invalidate the cache.
        Called after every LLM request (even free ones, for tracking).
        """
        usage = ApiUsage(
            user_id=user_id,
            session_id=session_id,
            model_provider=provider,
            model_name=model,
            task_type=task_type,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            estimated_cost_usd=cost,
            response_time_ms=response_time_ms,
            success=success,
            error_message=error_message,
        )
        db.add(usage)

        # Invalidate cache so next check reflects new spending
        if cost > 0:
            self._cache = None

    def invalidate_cache(self):
        """Force cache refresh on next query."""
        self._cache = None


# Singleton
credit_manager = CreditManager()
