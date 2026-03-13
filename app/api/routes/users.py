"""
User Routes
=============
POST   /api/v1/users              — Create a new youth user
GET    /api/v1/users              — List all users
GET    /api/v1/users/{user_id}    — Get user details
POST   /api/v1/users/{user_id}/intake  — Submit Strategic Intake answers
DELETE /api/v1/users/{user_id}    — Deactivate user
"""

import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
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

router = APIRouter(prefix="/api/v1/users", tags=["Users"])


@router.post("", response_model=UserResponse, status_code=201)
async def create_user(data: UserCreate, db: AsyncSession = Depends(get_db)):
    """Register a new youth user in the system."""
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
    return user


@router.get("", response_model=UserListResponse)
async def list_users(db: AsyncSession = Depends(get_db)):
    """List all active users."""
    result = await db.execute(
        select(User).where(User.is_active == True).order_by(User.created_at.desc())
    )
    users = result.scalars().all()
    return UserListResponse(users=users, total=len(users))


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Get a single user's details."""
    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/{user_id}/intake", response_model=IntakeResponse)
async def submit_intake(
    user_id: uuid.UUID,
    answers: IntakeAnswers,
    db: AsyncSession = Depends(get_db)
):
    """
    Submit the 5-question Strategic Intake.
    Calculates baseline trust score and assigns initial character.
    """
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.intake_completed:
        raise HTTPException(status_code=400, detail="Intake already completed")

    # ---- Score Calculation ----
    score = 0.0

    # Q1: Intent Check
    if answers.q1_intent == "check_box":
        score += INTAKE_SCORING["q1_check_box"]  # +50 honesty bonus
    else:
        score += INTAKE_SCORING["q1_win_freedom"]  # +10

    # Q2: Heat Level → Weight Multiplier
    heat = answers.q2_heat_level
    if heat >= INTAKE_SCORING["q2_high_heat_threshold"]:
        weight = INTAKE_SCORING["q2_high_heat_multiplier"]
    elif heat >= INTAKE_SCORING["q2_mid_heat_threshold"]:
        weight = INTAKE_SCORING["q2_mid_heat_multiplier"]
    else:
        weight = 1.0

    # Q3: Trap
    if answers.q3_trap != "dont_know":
        score += INTAKE_SCORING["q3_specific_trap"]  # +25
    else:
        score += INTAKE_SCORING["q3_dont_know"]  # +5

    # Q4: Autonomy Prize
    score += INTAKE_SCORING["q4_any_answer"]  # +10

    # ---- Character Assignment ----
    heat_category = "high" if heat >= 7 else "low"

    # Determine dominant vibe from intake signals
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
        Character.NAVIGATOR  # Safe fallback
    )

    # ---- Update User ----
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

    # Start streak if Q5 = "yes"
    if answers.q5_collaboration == "yes":
        user.check_in_streak = 1

    await db.flush()

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
async def deactivate_user(user_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Soft-delete a user (deactivate, don't remove data)."""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = False
    await db.flush()
