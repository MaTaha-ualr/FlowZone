"""
Session Routes (FIXED)
=======================
Changes:
  - Pagination on list_sessions
  - Auth required
  - User can only access their own sessions
"""

import uuid
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, delete
from app.database import get_db
from app.models.user import User
from app.models.session import Session
from app.models.message import Message
from app.schemas.api import SessionResponse
from app.core.config import settings
from app.core.safe_harbor import determine_floor
from app.middleware.rate_limit import concurrency_guard
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/sessions", tags=["Sessions"])

@router.post("/{user_id}", response_model=SessionResponse, status_code=201)
async def start_or_resume_session(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Start or resume a session. Users can only start their own."""
    if str(user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")

    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.intake_completed:
        raise HTTPException(
            status_code=400,
            detail="Complete the Strategic Intake first"
        )

    # Concurrency Check
    allowed = await concurrency_guard.check_in(str(user_id))
    if not allowed:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "System at capacity",
                "message": f"FlowZone supports {settings.max_concurrent_users} concurrent users.",
                "active_users": concurrency_guard.active_count,
            }
        )

    # Check existing active session
    now = datetime.utcnow()
    timeout_threshold = now - timedelta(hours=settings.session_timeout_hours)

    result = await db.execute(
        select(Session).where(
            and_(
                Session.user_id == user_id,
                Session.is_active == True,
                Session.started_at >= timeout_threshold,
            )
        ).order_by(Session.started_at.desc()).limit(1)
    )
    existing_session = result.scalar_one_or_none()
    if existing_session:
        return existing_session

    # Close stale sessions
    stale_result = await db.execute(
        select(Session).where(
            and_(Session.user_id == user_id, Session.is_active == True)
        )
    )
    for stale in stale_result.scalars().all():
        stale.is_active = False
        stale.ended_at = now

    # Create new session
    safe_harbor_floor = determine_floor(
        has_trauma_history=user.has_trauma_history,
        has_crisis_history=user.has_crisis_history,
    )
    session = Session(
        user_id=user_id,
        session_type="flowquest",
        character_active=user.current_character,
        safe_harbor_level=safe_harbor_floor,
    )
    db.add(session)
    await db.flush()
    await db.refresh(session)
    await db.commit()
    return session

@router.get("/{user_id}", response_model=list[SessionResponse])
async def list_sessions(
    user_id: uuid.UUID,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List a user's recent sessions with pagination."""
    if str(user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")

    result = await db.execute(
        select(Session)
        .where(Session.user_id == user_id)
        .order_by(Session.started_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return result.scalars().all()

@router.get("/{user_id}/current", response_model=SessionResponse)
async def get_current_session(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the user's currently active session."""
    if str(user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")

    result = await db.execute(
        select(Session).where(
            and_(Session.user_id == user_id, Session.is_active == True)
        ).order_by(Session.started_at.desc()).limit(1)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="No active session")
    return session

@router.put("/{session_id}/end", response_model=SessionResponse)
async def end_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """End an active session."""
    session = await db.get(Session, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if str(session.user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")
    if not session.is_active:
        raise HTTPException(status_code=400, detail="Session already ended")

    now = datetime.utcnow()
    session.is_active = False
    session.ended_at = now
    if session.started_at:
        delta = now - session.started_at
        session.duration_minutes = int(delta.total_seconds() / 60)

    await concurrency_guard.release(str(session.user_id))
    await db.flush()
    await db.commit()
    return session


@router.delete("/{session_id}", status_code=204)
async def delete_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Permanently delete a session and all its messages.
    Trust score history (daily snapshots) is NOT deleted — those are durable
    audit data. The conversation transcript is.
    Owner-only.
    """
    session = await db.get(Session, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if str(session.user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")

    # Delete all messages in this session first (no FK CASCADE configured).
    await db.execute(delete(Message).where(Message.session_id == session_id))
    # Then the session row itself.
    await db.delete(session)

    if session.is_active:
        await concurrency_guard.release(str(session.user_id))

    await db.flush()
    await db.commit()
    return None


@router.post("/{user_id}/new", response_model=SessionResponse, status_code=201)
async def force_new_session(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Force-end any active session for this user and create a fresh one.
    Use when the user explicitly hits "Start new conversation" — distinct
    from POST /{user_id} which resumes an active session if one exists.
    Owner-only.
    """
    if str(user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")

    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.intake_completed:
        raise HTTPException(status_code=400, detail="Complete the Strategic Intake first")

    # End all active sessions for this user.
    now = datetime.utcnow()
    active_result = await db.execute(
        select(Session).where(
            and_(Session.user_id == user_id, Session.is_active == True)
        )
    )
    for prior in active_result.scalars().all():
        prior.is_active = False
        prior.ended_at = now
        if prior.started_at:
            delta = now - prior.started_at
            prior.duration_minutes = int(delta.total_seconds() / 60)

    await concurrency_guard.release(str(user_id))

    # Re-acquire concurrency slot for the new session.
    allowed = await concurrency_guard.check_in(str(user_id))
    if not allowed:
        await db.commit()
        raise HTTPException(
            status_code=503,
            detail={
                "error": "System at capacity",
                "message": f"FlowZone supports {settings.max_concurrent_users} concurrent users.",
                "active_users": concurrency_guard.active_count,
            },
        )

    floor = determine_floor(user)
    new_session = Session(
        user_id=user_id,
        character_active=user.current_character,
        safe_harbor_level=floor,
        started_at=now,
        is_active=True,
    )
    db.add(new_session)
    await db.flush()
    await db.commit()
    await db.refresh(new_session)
    return new_session
