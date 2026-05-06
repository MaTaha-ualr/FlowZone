"""
Mentor Routes
==============
Auth model:
  - Mentors (role='mentor') can view any youth's roster, dashboard, and notes.
  - Youth (role='youth') can only view their own dashboard and notes.
  - Anyone authenticated can submit mentor notes (in practice the frontend
    only exposes the form to mentors).
"""

import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func

from app.database import get_db
from app.models.user import User
from app.models.session import Session as SessionModel
from app.models.mentor_note import MentorNote
from app.models.trust_score import TrustScore
from app.models.school_data import SchoolData
from app.schemas.api import MentorNoteCreate, MentorNoteResponse
from app.services.trust_engine.sanitization import sanitize_mentor_note
from app.core.constants import CHARACTER_DISPLAY_NAMES, Character
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/mentors", tags=["Mentors"])


def _is_mentor(user: User) -> bool:
    return (user.role or "").lower() == "mentor"


def _can_view_youth(viewer: User, youth_id: uuid.UUID) -> bool:
    """Mentors can view any youth; youth can only view themselves."""
    if _is_mentor(viewer):
        return True
    return str(viewer.id) == str(youth_id)


def _character_display_name(character_value: str | None) -> str:
    if not character_value:
        return "Yogi"
    try:
        return CHARACTER_DISPLAY_NAMES.get(Character(character_value), character_value)
    except ValueError:
        return character_value

@router.post("/notes", response_model=MentorNoteResponse, status_code=201)
async def submit_mentor_note(
    data: MentorNoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit a mentor note."""
    user = await db.get(User, data.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    note = MentorNote(
        user_id=data.user_id,
        mentor_id=data.mentor_id,
        mentor_name=data.mentor_name,
        note_type=data.note_type,
        raw_content=data.content,
        vouch_points=data.vouch_points,
        risk_flag_level=data.risk_flag_level,
    )

    try:
        note.sanitized_content = await sanitize_mentor_note(
            raw_content=data.content,
            db=db,
            user_id=data.user_id,
        )
        note.is_sanitized = True
    except Exception as e:
        note.sanitized_content = f"[Pending sanitization] {data.content[:200]}..."
        note.is_sanitized = False

    db.add(note)

    if data.note_type == "vouch" and data.vouch_points > 0:
        user.current_trust_score += data.vouch_points

    if data.risk_flag_level == "red":
        from app.core.constants import SafeHarborLevel
        user.safe_harbor_floor = SafeHarborLevel.RED

    await db.flush()
    await db.commit()
    return note

@router.get("/notes/{user_id}", response_model=list[MentorNoteResponse])
async def get_mentor_notes(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get mentor notes for a user. Mentors can view any youth; youth only their own."""
    if not _can_view_youth(current_user, user_id):
        raise HTTPException(status_code=403, detail="Not authorized")

    result = await db.execute(
        select(MentorNote)
        .where(MentorNote.user_id == user_id)
        .order_by(desc(MentorNote.created_at))
    )
    return result.scalars().all()


@router.get("/roster")
async def mentor_roster(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Return every youth in the system as roster cards for the mentor dashboard.
    Mentor-only. Each card carries enough state to render the roster grid
    without follow-up calls.
    """
    if not _is_mentor(current_user):
        raise HTTPException(status_code=403, detail="Mentor role required")

    # Pull every youth user.
    youth_result = await db.execute(
        select(User)
        .where(User.role == "youth")
        .where(User.is_active.is_(True))
        .order_by(User.name.asc())
    )
    youths = list(youth_result.scalars().all())
    if not youths:
        return {
            "total_youth": 0,
            "active_sessions": 0,
            "alerts": 0,
            "avg_trust": 0,
            "youth": [],
        }

    youth_ids = [u.id for u in youths]

    # Pull most-recent session timestamp per youth in one query.
    last_session_q = await db.execute(
        select(
            SessionModel.user_id,
            func.max(SessionModel.started_at).label("last_started"),
            func.bool_or(SessionModel.is_active).label("any_active"),
        )
        .where(SessionModel.user_id.in_(youth_ids))
        .group_by(SessionModel.user_id)
    )
    last_session_map: dict[uuid.UUID, tuple[datetime | None, bool]] = {
        row.user_id: (row.last_started, bool(row.any_active))
        for row in last_session_q.all()
    }

    # Most-recent school snapshot per youth.
    school_q = await db.execute(
        select(SchoolData)
        .where(SchoolData.user_id.in_(youth_ids))
        .order_by(SchoolData.user_id, desc(SchoolData.last_synced))
    )
    school_map: dict[uuid.UUID, SchoolData] = {}
    for s in school_q.scalars().all():
        school_map.setdefault(s.user_id, s)

    cards: list[dict] = []
    alerts = 0
    active_sessions = 0
    trust_total = 0.0
    for u in youths:
        last_started, any_active = last_session_map.get(u.id, (None, False))
        if any_active:
            active_sessions += 1

        # Alert = anything that warrants the mentor's attention.
        has_alert = (u.safe_harbor_floor or "").lower() != "green"

        school = school_map.get(u.id)
        char_name = _character_display_name(
            u.current_character.value if hasattr(u.current_character, "value") else u.current_character
        )
        char_value = (
            u.current_character.value if hasattr(u.current_character, "value") else u.current_character
        )
        tier_value = (
            u.current_tier.value if hasattr(u.current_tier, "value") else u.current_tier
        )
        sh_value = (
            u.safe_harbor_floor.value if hasattr(u.safe_harbor_floor, "value") else u.safe_harbor_floor
        )

        score = float(u.current_trust_score or 0.0)
        trust_total += score

        cards.append({
            "id": str(u.id),
            "name": u.name,
            "age": u.age,
            "city": u.city,
            "state": u.state,
            "school_name": u.school_name or (school.school_name if school else None),
            "user_type": u.user_type,
            "current_trust_score": score,
            "display_score": round(score, 1),
            "current_tier": tier_value,
            "safe_harbor_floor": sh_value,
            "current_character": char_value,
            "current_character_name": char_name,
            "check_in_streak": u.check_in_streak,
            "last_session_at": last_started.isoformat() if last_started else None,
            "has_alert": has_alert,
        })

        if has_alert:
            alerts += 1

    return {
        "total_youth": len(cards),
        "active_sessions": active_sessions,
        "alerts": alerts,
        "avg_trust": round(trust_total / len(cards), 1) if cards else 0,
        "youth": cards,
    }

@router.get("/dashboard/{user_id}")
async def mentor_dashboard(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Mentor dashboard view of a single youth.
    Mentors can view any youth; youth can only view themselves.
    """
    if not _can_view_youth(current_user, user_id):
        raise HTTPException(status_code=403, detail="Not authorized")

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    school_result = await db.execute(
        select(SchoolData).where(SchoolData.user_id == user_id)
        .order_by(desc(SchoolData.last_synced)).limit(1)
    )
    school = school_result.scalar_one_or_none()

    score_result = await db.execute(
        select(TrustScore).where(TrustScore.user_id == user_id)
        .order_by(desc(TrustScore.score_date)).limit(7)
    )
    scores = list(score_result.scalars().all())

    note_result = await db.execute(
        select(MentorNote).where(MentorNote.user_id == user_id)
        .order_by(desc(MentorNote.created_at)).limit(5)
    )
    notes = list(note_result.scalars().all())

    char_value = (
        user.current_character.value
        if hasattr(user.current_character, "value")
        else user.current_character
    )
    tier_value = (
        user.current_tier.value if hasattr(user.current_tier, "value") else user.current_tier
    )
    sh_value = (
        user.safe_harbor_floor.value
        if hasattr(user.safe_harbor_floor, "value")
        else user.safe_harbor_floor
    )

    return {
        "user": {
            "id": str(user.id),
            "name": user.name,
            "age": user.age,
            "city": user.city,
            "state": user.state,
            "school_name": user.school_name,
            "user_type": user.user_type,
            "current_character": char_value,
            "current_character_name": _character_display_name(char_value),
            "current_trust_score": float(user.current_trust_score or 0.0),
            "display_score": round(float(user.current_trust_score or 0.0), 1),
            "current_tier": tier_value,
            "check_in_streak": user.check_in_streak,
            "safe_harbor_floor": sh_value,
        },
        "school": {
            "gpa": school.gpa if school else None,
            "attendance_rate": school.attendance_rate if school else None,
            "classes_failing": school.classes_failing if school else [],
            "has_iep": school.has_iep if school else False,
        } if school else None,
        "trust_score_trend": [
            {"date": str(s.score_date), "score": float(s.total_score)}
            for s in reversed(scores)
        ],
        "recent_notes": [
            {
                "id": str(n.id),
                "mentor": n.mentor_name,
                "type": n.note_type,
                "content": n.sanitized_content,
                "vouch_points": n.vouch_points,
                "risk_flag_level": n.risk_flag_level,
                "date": n.created_at.isoformat() if n.created_at else None,
            }
            for n in notes
        ],
    }
