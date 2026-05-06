"""Frontend profile/dashboard routes."""

from fastapi import APIRouter, Depends
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    TRUST_TIER_DISPLAY,
    TRUST_TIER_THRESHOLDS,
    VOUCH_CONFIG,
    VOUCH_DISPLAY,
    TrustTier,
)
from app.core.security import get_current_user
from app.database import get_db
from app.models.trust_score import TrustScore
from app.models.user import User
from app.models.vouch import Vouch
from app.schemas.api import (
    RainbowCircleResponse,
    RainbowTierResponse,
    RewardItemResponse,
    RewardsResponse,
    UserProfileResponse,
)
from app.services.profile_projection import (
    auth_user_payload,
    calculate_display_score,
    user_tier,
)

router = APIRouter(prefix="/api/v1/profile", tags=["Profile"])


def _score(value: float | None) -> float:
    return float(value or 0.0)


def _tier_for_score(score: float) -> TrustTier:
    current = TrustTier.THE_WATCH
    for tier, threshold in sorted(TRUST_TIER_THRESHOLDS.items(), key=lambda item: item[1]):
        if score >= threshold:
            current = tier
    return current


def _tier_name(tier: TrustTier) -> str:
    return TRUST_TIER_DISPLAY[tier]["name"]


@router.get("/me", response_model=UserProfileResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
):
    """Return dashboard/profile data for the logged-in user."""
    payload = auth_user_payload(current_user)
    return UserProfileResponse(
        **payload,
        age=current_user.age,
        school_name=current_user.school_name,
        city=current_user.city,
        state=current_user.state,
        user_type=current_user.user_type,
        has_probation=current_user.has_probation,
        has_case_worker=current_user.has_case_worker,
        created_at=current_user.created_at,
    )


@router.get("/rainbow-circle", response_model=RainbowCircleResponse)
async def get_rainbow_circle(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return trust tier visualization data for the frontend."""
    score = _score(current_user.current_trust_score)
    current_tier = _tier_for_score(score)
    thresholds = sorted(TRUST_TIER_THRESHOLDS.items(), key=lambda item: item[1])
    tier_keys = [tier for tier, _ in thresholds]
    tier_index = tier_keys.index(current_tier)
    min_score = float(TRUST_TIER_THRESHOLDS[current_tier])
    next_threshold = (
        float(thresholds[tier_index + 1][1])
        if tier_index + 1 < len(thresholds)
        else None
    )
    if next_threshold is None:
        progress_percent = 100.0
    else:
        span = max(1.0, next_threshold - min_score)
        progress_percent = round(max(0.0, min(100.0, ((score - min_score) / span) * 100)), 1)

    all_tiers = [
        RainbowTierResponse(
            key=tier.value,
            name=TRUST_TIER_DISPLAY[tier]["name"],
            threshold=float(threshold),
            color=TRUST_TIER_DISPLAY[tier]["color"],
            emoji=TRUST_TIER_DISPLAY[tier]["emoji"],
            unlocked=score >= threshold,
        )
        for tier, threshold in thresholds
    ]

    result = await db.execute(
        select(TrustScore)
        .where(TrustScore.user_id == current_user.id)
        .order_by(desc(TrustScore.score_date))
        .limit(7)
    )
    snapshots = result.scalars().all()
    recent_deltas = []
    previous_score = None
    for snapshot in sorted(snapshots, key=lambda item: item.score_date):
        total = _score(snapshot.total_score)
        delta = total if previous_score is None else total - previous_score
        previous_score = total
        recent_deltas.append({
            "date": snapshot.score_date.isoformat(),
            "delta": round(delta, 1),
            "tier": _tier_for_score(total).value,
        })

    return RainbowCircleResponse(
        current_tier=current_tier.value,
        current_tier_name=TRUST_TIER_DISPLAY[current_tier]["name"],
        current_tier_color=TRUST_TIER_DISPLAY[current_tier]["color"],
        current_tier_emoji=TRUST_TIER_DISPLAY[current_tier]["emoji"],
        score=score,
        display_score=calculate_display_score(current_user),
        min_score_in_tier=min_score,
        max_score_in_tier=next_threshold,
        progress_percent=progress_percent,
        total_tiers=len(thresholds),
        tier_index=tier_index,
        all_tiers=all_tiers,
        recent_deltas=list(reversed(recent_deltas)),
    )


@router.get("/rewards", response_model=RewardsResponse)
async def get_rewards(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return available vouches and recent redeemed vouches for the menu drawer."""
    score = _score(current_user.current_trust_score)
    can_redeem = user_tier(current_user) != TrustTier.THE_WATCH
    cost_map = {
        "curfew_extension": VOUCH_CONFIG["curfew_extension_cost"],
        "social_pass": VOUCH_CONFIG["social_pass_cost"],
        "reduced_monitoring": VOUCH_CONFIG["reduced_monitoring_cost"],
    }
    available_vouches = [
        RewardItemResponse(
            key=key,
            name=VOUCH_DISPLAY[key]["name"],
            icon=VOUCH_DISPLAY[key]["icon"],
            cost=float(cost),
            can_afford=can_redeem and score >= cost,
            locked=not can_redeem,
        )
        for key, cost in cost_map.items()
    ]

    result = await db.execute(
        select(Vouch)
        .where(Vouch.user_id == current_user.id)
        .order_by(desc(Vouch.created_at))
        .limit(20)
    )
    redeemed_vouches = [
        {
            "id": str(vouch.id),
            "type": vouch.vouch_type,
            "name": VOUCH_DISPLAY.get(vouch.vouch_type, {}).get("name", vouch.vouch_type),
            "credits_spent": vouch.credits_spent,
            "status": vouch.status,
            "created_at": vouch.created_at.isoformat() if vouch.created_at else None,
            "expires_at": vouch.expires_at.isoformat() if vouch.expires_at else None,
        }
        for vouch in result.scalars().all()
    ]

    next_unlock_tier = None
    next_unlock_score = None
    if not can_redeem:
        next_unlock_tier = _tier_name(TrustTier.THE_FLEX)
        next_unlock_score = float(TRUST_TIER_THRESHOLDS[TrustTier.THE_FLEX])

    return RewardsResponse(
        current_score=score,
        available_vouches=available_vouches,
        redeemed_vouches=redeemed_vouches,
        can_redeem=can_redeem,
        next_unlock_tier=next_unlock_tier,
        next_unlock_score=next_unlock_score,
    )
