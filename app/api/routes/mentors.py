"""
Mentor Routes (FIXED)
======================
Changes:
  - Auth required
  - Users can only view their own notes
"""

import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database import get_db
from app.models.user import User
from app.models.mentor_note import MentorNote
from app.models.trust_score import TrustScore
from app.models.school_data import SchoolData
from app.schemas.api import MentorNoteCreate, MentorNoteResponse
from app.services.trust_engine.sanitization import sanitize_mentor_note
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/mentors", tags=["Mentors"])

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
    """Get mentor notes for a user. Users can only view their own."""
    if str(user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")

    result = await db.execute(
        select(MentorNote)
        .where(MentorNote.user_id == user_id)
        .order_by(desc(MentorNote.created_at))
    )
    return result.scalars().all()

@router.get("/dashboard/{user_id}")
async def mentor_dashboard(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mentor dashboard view. Users can only view their own."""
    if str(user_id) != str(current_user.id):
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
    scores = score_result.scalars().all()

    note_result = await db.execute(
        select(MentorNote).where(MentorNote.user_id == user_id)
        .order_by(desc(MentorNote.created_at)).limit(5)
    )
    notes = note_result.scalars().all()

    return {
        "user": {
            "name": user.name,
            "age": user.age,
            "user_type": user.user_type,
            "current_character": user.current_character,
            "trust_score": user.current_trust_score,
            "trust_tier": user.current_tier,
            "check_in_streak": user.check_in_streak,
            "safe_harbor_floor": user.safe_harbor_floor,
        },
        "school": {
            "gpa": school.gpa if school else None,
            "attendance_rate": school.attendance_rate if school else None,
            "classes_failing": school.classes_failing if school else [],
            "has_iep": school.has_iep if school else False,
        } if school else None,
        "trust_score_trend": [
            {"date": str(s.score_date), "score": s.total_score}
            for s in scores
        ],
        "recent_notes": [
            {
                "mentor": n.mentor_name,
                "type": n.note_type,
                "content": n.sanitized_content,
                "vouch_points": n.vouch_points,
                "date": n.created_at.isoformat() if n.created_at else None,
            }
            for n in notes
        ],
    }
