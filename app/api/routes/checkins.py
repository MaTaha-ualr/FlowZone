"""Daily check-in status and history routes."""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.database import get_db
from app.models.session import Session
from app.models.user import User
from app.schemas.api import CheckInItemResponse, CheckInTodayResponse
from app.services.profile_projection import enum_value

router = APIRouter(prefix="/api/v1/checkins", tags=["Check-ins"])


def _checkin_from_session(session: Session) -> CheckInItemResponse:
    return CheckInItemResponse(
        id=session.id,
        session_id=session.id,
        user_id=session.user_id,
        vibe=enum_value(session.vibe_selected),
        notes=None,
        safe_harbor_level=enum_value(session.safe_harbor_level),
        checked_in_at=session.started_at,
    )


@router.get("/today", response_model=CheckInTodayResponse)
async def get_today_checkin(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Session)
        .where(Session.user_id == current_user.id)
        .where(Session.vibe_selected.isnot(None))
        .where(func.date(Session.started_at) == date.today())
        .order_by(desc(Session.started_at))
        .limit(1)
    )
    session = result.scalar_one_or_none()
    return CheckInTodayResponse(
        checked_in=session is not None,
        check_in=_checkin_from_session(session) if session else None,
    )


@router.get("/history", response_model=list[CheckInItemResponse])
async def get_checkin_history(
    limit: int = Query(30, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Session)
        .where(Session.user_id == current_user.id)
        .where(Session.vibe_selected.isnot(None))
        .order_by(desc(Session.started_at))
        .limit(limit)
    )
    return [_checkin_from_session(session) for session in result.scalars().all()]
