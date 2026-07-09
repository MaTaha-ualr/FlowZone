"""Safety event routes."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.database import get_db
from app.models.safety_event import SafetyEvent
from app.models.session import Session
from app.models.user import User
from app.schemas.api import SafetyEventCreate, SafetyEventResponse

router = APIRouter(prefix="/api/v1/safety", tags=["Safety"])


def _is_staff(user: User) -> bool:
    return (user.role or "").lower() in {"mentor", "admin"}


def _can_access_event(user: User, event: SafetyEvent) -> bool:
    return _is_staff(user) or str(event.user_id) == str(user.id)


async def create_safety_event(
    *,
    db: AsyncSession,
    user_id: uuid.UUID,
    session_id: uuid.UUID | None,
    source: str,
    severity: str,
    trigger: str,
    description: str | None = None,
) -> SafetyEvent:
    event = SafetyEvent(
        user_id=user_id,
        session_id=session_id,
        source=source,
        severity=severity,
        trigger=trigger,
        description=description,
        status="open",
    )
    db.add(event)
    await db.flush()
    await db.refresh(event)
    return event


@router.post("/events", response_model=SafetyEventResponse, status_code=status.HTTP_201_CREATED)
async def submit_safety_event(
    data: SafetyEventCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a safety event from crisis UI, Safe Harbor state, or manual reporting."""
    target_user_id = data.user_id or current_user.id
    if str(target_user_id) != str(current_user.id) and not _is_staff(current_user):
        raise HTTPException(status_code=403, detail="Not authorized")

    user = await db.get(User, target_user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=404, detail="User not found")

    if data.session_id:
        session = await db.get(Session, data.session_id)
        if not session or str(session.user_id) != str(target_user_id):
            raise HTTPException(status_code=404, detail="Session not found")

    event = await create_safety_event(
        db=db,
        user_id=target_user_id,
        session_id=data.session_id,
        source=data.source,
        severity=data.severity.value,
        trigger=data.trigger,
        description=data.description,
    )
    await db.commit()
    return event


@router.get("/events/{event_id}", response_model=SafetyEventResponse)
async def get_safety_event(
    event_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    event = await db.get(SafetyEvent, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Safety event not found")
    if not _can_access_event(current_user, event):
        raise HTTPException(status_code=403, detail="Not authorized")
    return event


@router.get("/events", response_model=list[SafetyEventResponse])
async def list_my_safety_events(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SafetyEvent)
        .where(SafetyEvent.user_id == current_user.id)
        .order_by(desc(SafetyEvent.created_at))
        .limit(limit)
    )
    return result.scalars().all()
