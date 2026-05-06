"""
Trust Score Calculator (FIXED)
===============================
Changes from original:
  - Removed T (days_active) from daily contribution denominator.
    The time factor was incorrectly penalizing loyal users.
  - Added normalized_display_score for soft tenure-based dampening
    (cosmetic only — tier thresholds use raw cumulative score).
  - Fixed streak logic to handle timezone-aware datetimes correctly.
  - Added explicit transaction safety (db.flush() only, caller commits).
"""

import logging
from datetime import datetime, date, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.models.user import User
from app.models.session import Session
from app.models.trust_score import TrustScore
from app.models.mentor_note import MentorNote
from app.models.vouch import Vouch
from app.core.constants import (
    Vibe, TRUST_SCORE_WEIGHTS, TrustTier, TRUST_TIER_THRESHOLDS,
    VOUCH_CONFIG, SafeHarborLevel,
)

logger = logging.getLogger(__name__)


def _as_naive_utc(value: datetime) -> datetime:
    """Normalize any aware datetimes before comparing with DB-naive UTC values."""
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)

# ------------------------------------------------------------------
# MAIN: Recalculate after a session
# ------------------------------------------------------------------

async def recalculate_after_session(
    user_id: UUID,
    session: Session,
    db: AsyncSession,
) -> dict:
    """
    Recalculate the trust score after a FlowQuest session.

    FIXED FORMULA:
      daily_contribution = (C × W) + H + R + M - P
      user.current_trust_score += daily_contribution

    The old formula divided by T (days_active), which incorrectly
    shrunk daily contributions for long-tenure users.
    T is now stored as metadata only.

    A soft display normalization is available for UI cosmetics:
      display_score = raw_score / (1 + 0.002 * days_active)
    """
    user = await db.get(User, user_id)
    if not user:
        return {"error": "User not found"}

    previous_score = user.current_trust_score
    today = date.today()
    weights = TRUST_SCORE_WEIGHTS

    # 1. Consistency (C): Update check-in streak
    streak = await _update_streak(user, db)

    # 2. Weight (W): Hard day multiplier
    vibe = session.vibe_selected
    if vibe in (Vibe.ANGRY, Vibe.STORM):
        weight = weights["weight_hard_day"]  # 1.5x
    else:
        weight = weights["weight_normal_day"]  # 1.0x

    # 3. Honesty Bonus (H)
    honesty_points = (session.honesty_disclosures or 0) * weights["honesty_bonus"]

    # 4. Regulation Bonus (R)
    completed = session.interventions_completed or []
    regulation_count = sum(
        1 for i in completed
        if "breathing" in i.lower() or "grounding" in i.lower() or "reset" in i.lower()
    )
    regulation_points = regulation_count * weights["regulation_bonus"]

    # 5. Mentor Vouch (M): Sum of today's vouch points
    vouch_result = await db.execute(
        select(func.coalesce(func.sum(MentorNote.vouch_points), 0))
        .where(and_(
            MentorNote.user_id == user_id,
            MentorNote.note_type == "vouch",
            func.date(MentorNote.created_at) == today,
        ))
    )
    mentor_points = float(vouch_result.scalar())

    # 6. Penalty (P)
    penalty = 0.0
    if session.mask_detected:
        penalty = abs(weights["mask_penalty"])  # -10

    # 7. Time (T): Days since first check-in — METADATA ONLY
    first_session_result = await db.execute(
        select(func.min(Session.started_at))
        .where(Session.user_id == user_id)
    )
    first_session_date = first_session_result.scalar()
    if first_session_date:
        days_active = max(1, (datetime.utcnow() - _as_naive_utc(first_session_date)).days)
    else:
        days_active = 1

    # ---- Calculate daily contribution (FIXED: no division by T) ----
    daily_contribution = (streak * weight) + honesty_points + regulation_points + mentor_points - penalty

    # ---- Update or create today's trust score snapshot ----
    existing = await db.execute(
        select(TrustScore).where(and_(
            TrustScore.user_id == user_id,
            TrustScore.score_date == today,
        ))
    )
    score_record = existing.scalar_one_or_none()

    if score_record:
        score_record.consistency_c = streak
        score_record.weight_w = weight
        score_record.honesty_bonus_h += honesty_points
        score_record.regulation_bonus_r += regulation_points
        score_record.mentor_vouch_m = mentor_points
        score_record.penalty_p += penalty
        score_record.time_t = days_active
        score_record.calculate()
    else:
        score_record = TrustScore(
            user_id=user_id,
            score_date=today,
            consistency_c=streak,
            weight_w=weight,
            honesty_bonus_h=honesty_points,
            regulation_bonus_r=regulation_points,
            mentor_vouch_m=mentor_points,
            penalty_p=penalty,
            time_t=days_active,
        )
        score_record.calculate()
        db.add(score_record)

    # ---- Update user's running total (cumulative, never divided by T) ----
    user.current_trust_score = previous_score + daily_contribution
    user.current_trust_score = max(0.0, user.current_trust_score)

    # Soft display normalization (cosmetic — does NOT affect tiers)
    display_score = user.current_trust_score / (1.0 + 0.002 * days_active)

    # ---- Check for tier promotion ----
    old_tier = user.current_tier
    new_tier = _calculate_tier(user.current_trust_score)
    tier_changed = old_tier != new_tier
    user.current_tier = new_tier

    # ---- Update session delta ----
    session.trust_score_delta = daily_contribution

    await db.flush()

    result = {
        "previous_score": previous_score,
        "new_score": user.current_trust_score,
        "display_score": round(display_score, 1),
        "delta": daily_contribution,
        "components": {
            "consistency": streak,
            "weight": weight,
            "honesty_bonus": honesty_points,
            "regulation_bonus": regulation_points,
            "mentor_vouch": mentor_points,
            "penalty": penalty,
            "days_active": days_active,
        },
        "tier_change": tier_changed,
        "old_tier": old_tier,
        "new_tier": new_tier,
    }

    if tier_changed:
        logger.info(f"TIER PROMOTION: User {user.name} moved from {old_tier} to {new_tier}!")

    logger.info(
        f"Trust score updated for {user.name}: "
        f"{previous_score:.1f} → {user.current_trust_score:.1f} "
        f"(delta: {daily_contribution:+.1f}, display: {display_score:.1f})"
    )

    return result

# ------------------------------------------------------------------
# STREAK MANAGEMENT (FIXED timezone handling)
# ------------------------------------------------------------------

async def _update_streak(user: User, db: AsyncSession) -> int:
    """
    Update the user's consecutive check-in streak.
    """
    today = date.today()
    last_checkin = user.last_check_in

    if last_checkin is None:
        user.check_in_streak = 1
        user.last_check_in = datetime.utcnow()
        return 1

    last_date = _as_naive_utc(last_checkin).date()
    days_gap = (today - last_date).days

    if days_gap == 0:
        pass  # Already checked in today
    elif days_gap == 1:
        user.check_in_streak += 1
    else:
        user.check_in_streak = 1

    user.last_check_in = datetime.utcnow()
    return user.check_in_streak

# ------------------------------------------------------------------
# TIER CALCULATION
# ------------------------------------------------------------------

def _calculate_tier(total_score: float) -> TrustTier:
    """Determine trust tier based on cumulative score."""
    current_tier = TrustTier.THE_WATCH
    for tier, threshold in sorted(TRUST_TIER_THRESHOLDS.items(), key=lambda x: x[1]):
        if total_score >= threshold:
            current_tier = tier
    return current_tier

# ------------------------------------------------------------------
# CREDIT DECAY (for silent users)
# ------------------------------------------------------------------

async def apply_credit_decay(db: AsyncSession) -> list[dict]:
    """
    Apply credit decay for users who haven't checked in for 72+ hours.
    Should be called daily via cron or background task.
    """
    threshold = datetime.utcnow() - timedelta(
        hours=TRUST_SCORE_WEIGHTS["decay_threshold_hours"]
    )
    decay_rate = TRUST_SCORE_WEIGHTS["credit_decay_rate"]

    result = await db.execute(
        select(User).where(and_(
            User.is_active == True,
            User.last_check_in < threshold,
            User.current_trust_score > 0,
        ))
    )
    silent_users = result.scalars().all()

    affected = []
    for user in silent_users:
        old_score = user.current_trust_score
        decay_amount = old_score * decay_rate
        user.current_trust_score = max(0.0, old_score - decay_amount)
        user.current_tier = _calculate_tier(user.current_trust_score)

        days_silent = (datetime.utcnow() - _as_naive_utc(user.last_check_in)).days

        affected.append({
            "user_id": str(user.id),
            "name": user.name,
            "days_silent": days_silent,
            "old_score": old_score,
            "new_score": user.current_trust_score,
            "decayed": decay_amount,
        })

        logger.info(
            f"Credit decay: {user.name} silent {days_silent} days, "
            f"{old_score:.1f} → {user.current_trust_score:.1f} (-{decay_amount:.1f})"
        )

    await db.flush()
    return affected

# ------------------------------------------------------------------
# VOUCH ECONOMY
# ------------------------------------------------------------------

async def redeem_vouch(
    user_id: UUID,
    vouch_type: str,
    db: AsyncSession,
) -> dict:
    """Redeem a vouch by spending trust credits."""
    user = await db.get(User, user_id)
    if not user:
        return {"success": False, "error": "User not found"}

    if user.current_tier == TrustTier.THE_WATCH:
        return {
            "success": False,
            "error": "You need to reach The Flex tier to redeem vouches. "
            f"Current score: {user.current_trust_score:.0f}, "
            f"needed: {TRUST_TIER_THRESHOLDS[TrustTier.THE_FLEX]}"
        }

    cost_map = {
        "curfew_extension": VOUCH_CONFIG["curfew_extension_cost"],
        "social_pass": VOUCH_CONFIG["social_pass_cost"],
        "reduced_monitoring": VOUCH_CONFIG["reduced_monitoring_cost"],
    }
    cost = cost_map.get(vouch_type)
    if cost is None:
        return {"success": False, "error": f"Unknown vouch type: {vouch_type}"}

    if user.current_trust_score < cost:
        return {
            "success": False,
            "error": f"Not enough credits. Need {cost}, have {user.current_trust_score:.0f}"
        }

    expires_at = datetime.utcnow() + timedelta(hours=VOUCH_CONFIG["expiry_hours"])
    vouch = Vouch(
        user_id=user_id,
        vouch_type=vouch_type,
        credits_spent=cost,
        expires_at=expires_at,
    )
    db.add(vouch)

    user.current_trust_score -= cost
    user.current_tier = _calculate_tier(user.current_trust_score)

    await db.flush()
    await db.refresh(vouch)

    logger.info(
        f"Vouch redeemed: {user.name} spent {cost} credits on {vouch_type}. "
        f"Balance: {user.current_trust_score:.0f}. Expires: {expires_at}"
    )

    return {
        "success": True,
        "vouch_id": str(vouch.id),
        "vouch_type": vouch_type,
        "credits_spent": cost,
        "remaining_balance": user.current_trust_score,
        "expires_at": expires_at.isoformat(),
    }

async def expire_vouches(db: AsyncSession) -> int:
    """Expire vouches past their 48-hour window."""
    now = datetime.utcnow()
    result = await db.execute(
        select(Vouch).where(and_(
            Vouch.status == "active",
            Vouch.expires_at < now,
        ))
    )
    expired = result.scalars().all()

    for v in expired:
        v.status = "expired"

    await db.flush()

    if expired:
        logger.info(f"Expired {len(expired)} vouches")

    return len(expired)

# ------------------------------------------------------------------
# SCORE HISTORY
# ------------------------------------------------------------------

async def get_score_history(
    user_id: UUID,
    db: AsyncSession,
    days: int = 30,
) -> list[dict]:
    """Get trust score history for charts/dashboard."""
    result = await db.execute(
        select(TrustScore)
        .where(TrustScore.user_id == user_id)
        .order_by(TrustScore.score_date.desc())
        .limit(days)
    )
    scores = result.scalars().all()

    return [
        {
            "date": str(s.score_date),
            "total": s.total_score,
            "consistency": s.consistency_c,
            "weight": s.weight_w,
            "honesty": s.honesty_bonus_h,
            "regulation": s.regulation_bonus_r,
            "mentor": s.mentor_vouch_m,
            "penalty": s.penalty_p,
        }
        for s in reversed(scores)
    ]
