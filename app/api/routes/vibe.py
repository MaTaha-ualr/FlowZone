"""Vibe check routes."""

from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    CHARACTER_DISPLAY_NAMES,
    VIBE_CHARACTER_MAP,
    VIBE_EMOJI_MAP,
    VIBE_MESSAGE_TEMPLATES,
    Character,
    SafeHarborLevel,
    Vibe,
)
from app.core.security import get_current_user
from app.database import get_db
from app.models.session import Session
from app.models.user import User
from app.schemas.api import VibeCheckRequest, VibeCheckResponse
from app.api.routes.safety import create_safety_event
from app.services.profile_projection import coerce_enum, user_character

router = APIRouter(prefix="/api/v1/vibe", tags=["Vibe"])

SAFE_HARBOR_RANK = {
    SafeHarborLevel.GREEN: 0,
    SafeHarborLevel.YELLOW: 1,
    SafeHarborLevel.RED: 2,
}


def _safe_harbor_for_vibe(vibe: Vibe) -> SafeHarborLevel:
    if vibe == Vibe.STORM:
        return SafeHarborLevel.RED
    if vibe in {Vibe.ANGRY, Vibe.GUARDED}:
        return SafeHarborLevel.YELLOW
    return SafeHarborLevel.GREEN


def _max_safe_harbor(*levels: SafeHarborLevel) -> SafeHarborLevel:
    return max(levels, key=lambda level: SAFE_HARBOR_RANK[level])


def _record_check_in(user: User) -> None:
    today = date.today()
    last = user.last_check_in.date() if user.last_check_in else None
    if last is None:
        user.check_in_streak = 1
    elif last == today:
        user.check_in_streak = user.check_in_streak or 1
    elif (today - last).days == 1:
        user.check_in_streak = (user.check_in_streak or 0) + 1
    else:
        user.check_in_streak = 1
    user.last_check_in = datetime.utcnow()


@router.post("/check", response_model=VibeCheckResponse)
async def check_vibe(
    data: VibeCheckRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Set the session vibe and return the character state for the frontend."""
    session = await db.get(Session, data.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if str(session.user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")
    if not session.is_active:
        raise HTTPException(status_code=400, detail="Session is not active")

    vibe = Vibe(data.vibe.value)
    character = (
        user_character(current_user)
        if vibe == Vibe.SOLID
        else VIBE_CHARACTER_MAP.get(vibe, Character.NAVIGATOR)
    )
    current_level = coerce_enum(
        SafeHarborLevel,
        session.safe_harbor_level,
        SafeHarborLevel.GREEN,
    )
    floor_level = coerce_enum(
        SafeHarborLevel,
        current_user.safe_harbor_floor,
        SafeHarborLevel.GREEN,
    )
    safe_harbor_level = _max_safe_harbor(
        current_level,
        floor_level,
        _safe_harbor_for_vibe(vibe),
    )

    session.vibe_selected = vibe
    session.character_active = character
    session.safe_harbor_level = safe_harbor_level
    current_user.current_character = character
    current_user.safe_harbor_floor = _max_safe_harbor(floor_level, safe_harbor_level)
    _record_check_in(current_user)

    if safe_harbor_level != SafeHarborLevel.GREEN:
        await create_safety_event(
            db=db,
            user_id=current_user.id,
            session_id=session.id,
            source="vibe_check",
            severity=safe_harbor_level.value,
            trigger=vibe.value,
            description=data.notes,
        )

    await db.flush()
    await db.refresh(session)
    await db.commit()

    character_name = CHARACTER_DISPLAY_NAMES.get(character, character.value)
    message_template = VIBE_MESSAGE_TEMPLATES.get(vibe, "{character_name} is here.")
    return VibeCheckResponse(
        session_id=session.id,
        vibe=vibe.value,
        vibe_emoji=VIBE_EMOJI_MAP[vibe],
        character_assigned=character.value,
        character_name=character_name,
        message=message_template.format(character_name=character_name),
        safe_harbor_level=safe_harbor_level.value,
    )
