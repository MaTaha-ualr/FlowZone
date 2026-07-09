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
from sqlalchemy import select, func, desc
from app.database import get_db
from app.models.user import User
from app.models.document_ref import DocumentRef
from app.models.mentor_note import MentorNote
from app.models.safety_event import SafetyEvent
from app.models.session import Session
from app.models.trust_score import TrustScore
from app.schemas.api import (
    UserCreate, UserResponse, UserListResponse,
    IntakeAnswers, IntakeResponse, ActivityItemResponse,
)
from app.core.constants import (
    Character, CHARACTER_ASSIGNMENT_RULES, Vibe,
    INTAKE_SCORING, SafeHarborLevel
)
from app.core.config import settings
from app.core.security import get_current_user, get_current_user_optional

router = APIRouter(prefix="/api/v1/users", tags=["Users"])


def _is_staff(user: User) -> bool:
    return (user.role or "").lower() in {"mentor", "admin"}


def _enum_value(value) -> str | None:
    if value is None:
        return None
    return value.value if hasattr(value, "value") else str(value)

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


@router.get("/{user_id}/activity", response_model=list[ActivityItemResponse])
async def get_user_activity(
    user_id: uuid.UUID,
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return a real, typed activity feed for dashboard timelines."""
    if str(user_id) != str(current_user.id) and not _is_staff(current_user):
        raise HTTPException(status_code=403, detail="Not authorized")

    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=404, detail="User not found")

    events: list[dict] = []

    session_result = await db.execute(
        select(Session)
        .where(Session.user_id == user_id)
        .order_by(desc(Session.started_at))
        .limit(limit)
    )
    for session in session_result.scalars().all():
        if session.vibe_selected:
            vibe = _enum_value(session.vibe_selected)
            events.append({
                "id": f"vibe:{session.id}",
                "type": "vibe_check",
                "title": "Vibe check saved",
                "description": f"{vibe.title()} vibe recorded.",
                "timestamp": session.started_at,
                "source_id": str(session.id),
            })
        events.append({
            "id": f"session:{session.id}",
            "type": "flowquest",
            "title": "FlowQuest session started",
            "description": "A conversation session was opened.",
            "timestamp": session.started_at,
            "delta": float(session.trust_score_delta or 0.0),
            "source_id": str(session.id),
        })

    document_result = await db.execute(
        select(DocumentRef)
        .where(DocumentRef.user_id == user_id)
        .order_by(desc(DocumentRef.created_at))
        .limit(limit)
    )
    for doc in document_result.scalars().all():
        events.append({
            "id": f"document:{doc.id}",
            "type": "document",
            "title": "Document uploaded",
            "description": f"{doc.filename} is {doc.processing_status}.",
            "timestamp": doc.created_at,
            "source_id": str(doc.id),
        })

    note_result = await db.execute(
        select(MentorNote)
        .where(MentorNote.user_id == user_id)
        .order_by(desc(MentorNote.created_at))
        .limit(limit)
    )
    for note in note_result.scalars().all():
        if note.note_type == "vouch":
            title = "Mentor vouch added"
            event_type = "vouch"
            delta = float(note.vouch_points or 0)
        elif note.note_type == "risk_flag":
            title = "Mentor risk flag added"
            event_type = "mask"
            delta = None
        else:
            title = "Mentor note added"
            event_type = "tactical_action"
            delta = None
        events.append({
            "id": f"mentor_note:{note.id}",
            "type": event_type,
            "title": title,
            "description": note.sanitized_content or "A mentor note was saved.",
            "timestamp": note.created_at,
            "delta": delta,
            "source_id": str(note.id),
        })

    trust_result = await db.execute(
        select(TrustScore)
        .where(TrustScore.user_id == user_id)
        .order_by(desc(TrustScore.score_date))
        .limit(limit)
    )
    for snapshot in trust_result.scalars().all():
        events.append({
            "id": f"trust:{snapshot.id}",
            "type": "tier_change",
            "title": "Trust score snapshot updated",
            "description": f"Score moved to {round(float(snapshot.total_score or 0.0), 1)}.",
            "timestamp": snapshot.calculated_at,
            "delta": float(snapshot.total_score or 0.0),
            "source_id": str(snapshot.id),
        })

    safety_result = await db.execute(
        select(SafetyEvent)
        .where(SafetyEvent.user_id == user_id)
        .order_by(desc(SafetyEvent.created_at))
        .limit(limit)
    )
    for event in safety_result.scalars().all():
        events.append({
            "id": f"safety:{event.id}",
            "type": "mask",
            "title": f"Safety event opened: {event.severity}",
            "description": event.description or event.trigger,
            "timestamp": event.created_at,
            "source_id": str(event.id),
        })

    events.sort(key=lambda item: item["timestamp"], reverse=True)
    return events[:limit]

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
