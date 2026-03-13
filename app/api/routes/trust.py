"""
Trust Score & Vouch Routes
============================
GET  /api/v1/trust/{user_id}            — Get current score + components
GET  /api/v1/trust/{user_id}/history    — Score history (for charts)
POST /api/v1/trust/{user_id}/vouch      — Redeem a vouch (spend credits)
GET  /api/v1/trust/{user_id}/vouches    — List active/expired vouches
POST /api/v1/trust/decay                — Admin: trigger credit decay manually
"""

import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database import get_db
from app.models.user import User
from app.models.vouch import Vouch
from app.services.trust_engine.calculator import (
    get_score_history, redeem_vouch, apply_credit_decay, expire_vouches,
)
from app.core.constants import TRUST_TIER_THRESHOLDS, VOUCH_CONFIG

router = APIRouter(prefix="/api/v1/trust", tags=["Trust Score"])


@router.get("/{user_id}")
async def get_trust_score(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get current trust score with breakdown and tier info."""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Calculate distance to next tier
    next_tier = None
    points_needed = None
    for tier, threshold in sorted(TRUST_TIER_THRESHOLDS.items(), key=lambda x: x[1]):
        if threshold > user.current_trust_score:
            next_tier = tier.value
            points_needed = threshold - user.current_trust_score
            break

    return {
        "user_id": str(user.id),
        "name": user.name,
        "current_score": user.current_trust_score,
        "current_tier": user.current_tier,
        "check_in_streak": user.check_in_streak,
        "last_check_in": user.last_check_in.isoformat() if user.last_check_in else None,
        "baseline_score": user.baseline_trust_score,
        "next_tier": next_tier,
        "points_to_next_tier": points_needed,
        "vouch_costs": VOUCH_CONFIG,
    }


@router.get("/{user_id}/history")
async def get_trust_history(
    user_id: uuid.UUID,
    days: int = 30,
    db: AsyncSession = Depends(get_db),
):
    """Get trust score history for dashboard charts."""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    history = await get_score_history(user_id, db, days)
    return {
        "user_id": str(user_id),
        "days_requested": days,
        "history": history,
    }


@router.post("/{user_id}/vouch")
async def create_vouch(
    user_id: uuid.UUID,
    vouch_type: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Redeem a vouch by spending trust credits.
    Requires The Flex tier or higher.

    vouch_type: "curfew_extension" | "social_pass" | "reduced_monitoring"
    """
    valid_types = ["curfew_extension", "social_pass", "reduced_monitoring"]
    if vouch_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid vouch type. Must be one of: {valid_types}"
        )

    result = await redeem_vouch(user_id, vouch_type, db)

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.get("/{user_id}/vouches")
async def list_vouches(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """List all vouches for a user (active + expired)."""
    result = await db.execute(
        select(Vouch)
        .where(Vouch.user_id == user_id)
        .order_by(desc(Vouch.created_at))
        .limit(20)
    )
    vouches = result.scalars().all()

    return {
        "user_id": str(user_id),
        "vouches": [
            {
                "id": str(v.id),
                "type": v.vouch_type,
                "credits_spent": v.credits_spent,
                "status": v.status,
                "created_at": v.created_at.isoformat() if v.created_at else None,
                "expires_at": v.expires_at.isoformat() if v.expires_at else None,
            }
            for v in vouches
        ]
    }


@router.post("/decay")
async def trigger_decay(db: AsyncSession = Depends(get_db)):
    """Admin endpoint: manually trigger credit decay for silent users."""
    # Also expire old vouches
    expired_count = await expire_vouches(db)
    affected = await apply_credit_decay(db)

    return {
        "vouches_expired": expired_count,
        "users_decayed": len(affected),
        "details": affected,
    }

