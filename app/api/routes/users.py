"""
User Routes (FIXED)
====================
Changes:
  - Pagination on list_users
  - Auth required for all routes
  - Demo mode support via X-User-ID
"""

import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models.user import User
from app.schemas.api import (
    UserCreate, UserResponse, UserListResponse,
    IntakeAnswers, IntakeResponse
)
from app.core.constants import (
    Character, CHARACTER_ASSIGNMENT_RULES, Vibe,
    INTAKE_SCORING, SafeHarborLevel
)
from app.core.config import settings
from app.core.security import get_current_user, get_current_user_optional

router = APIRouter(prefix="/api/v1/users", tags=["Users"])

@router.post("", response_model=UserResponse, status_code=201)
async def create_user(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    """Register a youth user.

    Bootstrap and pilot demo mode can create a user without an existing token.
    Once users exist in non-demo mode, this endpoint requires authentication.
    """
    if current_user is None and not settings.app_demo_mode:
        existing_users_result = await db.execute(
            select(func.count()).select_from(User).where(User.is_active == True)
        )
        if (existing_users_result.scalar() or 0) > 0:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required to create additional users.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    user = User(
        name=data.name,
        age=data.age,
        date_of_birth=data.date_of_birth,
        school_name=data.school_name,
        city=data.city,
        state=data.state,
        user_type=data.user_type,
        has_probation=data.has_probation,
        has_case_worker=data.has_case_worker,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    await db.commit()
    return user

@router.get("", response_model=UserListResponse)
async def list_users(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List active users with pagination."""
    result = await db.execute(
        select(User)
        .where(User.is_active == True)
        .order_by(User.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    users = result.scalars().all()

    # Total count for pagination metadata
    count_result = await db.execute(
        select(func.count()).select_from(User).where(User.is_active == True)
    )
    total = count_result.scalar()

    return UserListResponse(users=users, total=total)

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single user's details."""
    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.post("/{user_id}/intake", response_model=IntakeResponse)
async def submit_intake(
    user_id: uuid.UUID,
    answers: IntakeAnswers,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit the 5-question Strategic Intake."""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.intake_completed:
        raise HTTPException(status_code=400, detail="Intake already completed")

    # Score Calculation
    score = 0.0
    if answers.q1_intent == "check_box":
        score += INTAKE_SCORING["q1_check_box"]
    else:
        score += INTAKE_SCORING["q1_win_freedom"]

    heat = answers.q2_heat_level
    if heat >= INTAKE_SCORING["q2_high_heat_threshold"]:
        weight = INTAKE_SCORING["q2_high_heat_multiplier"]
    elif heat >= INTAKE_SCORING["q2_mid_heat_threshold"]:
        weight = INTAKE_SCORING["q2_mid_heat_multiplier"]
    else:
        weight = 1.0

    if answers.q3_trap != "dont_know":
        score += INTAKE_SCORING["q3_specific_trap"]
    else:
        score += INTAKE_SCORING["q3_dont_know"]

    score += INTAKE_SCORING["q4_any_answer"]

    # Character Assignment
    heat_category = "high" if heat >= 7 else "low"
    if answers.q1_intent == "check_box" and heat >= 7:
        dominant_vibe = Vibe.GUARDED
    elif heat >= 8:
        dominant_vibe = Vibe.STORM if answers.q3_trap == "home" else Vibe.ANGRY
    elif answers.q1_intent == "win_freedom":
        dominant_vibe = Vibe.SOLID
    else:
        dominant_vibe = Vibe.GUARDED

    character = CHARACTER_ASSIGNMENT_RULES.get(
        (heat_category, dominant_vibe),
        Character.NAVIGATOR
    )

    # Update User
    user.intake_completed = True
    user.intake_answers = {
        "q1_intent": answers.q1_intent,
        "q2_heat_level": answers.q2_heat_level,
        "q3_trap": answers.q3_trap,
        "q4_autonomy_prize": answers.q4_autonomy_prize,
        "q5_collaboration": answers.q5_collaboration,
    }
    user.baseline_trust_score = score
    user.current_trust_score = score
    user.heat_level = heat
    user.weight_multiplier = weight
    user.current_character = character

    if answers.q5_collaboration == "yes":
        user.check_in_streak = 1

    await db.flush()
    await db.commit()

    return IntakeResponse(
        user_id=user.id,
        baseline_trust_score=score,
        assigned_character=character,
        heat_level=heat,
        weight_multiplier=weight,
        message=f"Character assigned: {character.value}. Baseline score: {score}. "
        f"{'Streak started.' if answers.q5_collaboration == 'yes' else 'No streak yet — trust must be earned.'}"
    )

@router.delete("/{user_id}", status_code=204)
async def deactivate_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Soft-delete a user."""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = False
    await db.flush()
    await db.commit()
