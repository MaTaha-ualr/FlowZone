"""Frontend-facing profile projection helpers."""

from enum import Enum
from typing import TypeVar

from app.core.constants import (
    Character,
    CHARACTER_DISPLAY_NAMES,
    SafeHarborLevel,
    TrustTier,
)
from app.models.user import User

EnumT = TypeVar("EnumT", bound=Enum)


def enum_value(value: Enum | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.value
    return str(value)


def coerce_enum(enum_cls: type[EnumT], value: EnumT | str | None, default: EnumT) -> EnumT:
    if isinstance(value, enum_cls):
        return value
    try:
        return enum_cls(value)
    except (TypeError, ValueError):
        return default


def user_character(user: User) -> Character:
    return coerce_enum(Character, user.current_character, Character.NAVIGATOR)


def user_tier(user: User) -> TrustTier:
    return coerce_enum(TrustTier, user.current_tier, TrustTier.THE_WATCH)


def user_safe_harbor(user: User) -> SafeHarborLevel:
    return coerce_enum(SafeHarborLevel, user.safe_harbor_floor, SafeHarborLevel.GREEN)


def calculate_display_score(user: User) -> float:
    """Return the cosmetic 0-100 dashboard score without changing trust math."""
    score = float(user.current_trust_score or 0.0)
    return round(max(0.0, min(100.0, score)), 1)


def auth_user_payload(user: User) -> dict:
    character = user_character(user)
    return {
        "id": user.id,
        "name": user.name,
        "username": user.username,
        "email": user.email,
        "phone": user.phone,
        "role": user.role or "youth",
        "current_character": character.value,
        "current_character_name": CHARACTER_DISPLAY_NAMES.get(character, character.value),
        "current_tier": enum_value(user.current_tier) or TrustTier.THE_WATCH.value,
        "check_in_streak": user.check_in_streak or 0,
        "current_trust_score": float(user.current_trust_score or 0.0),
        "display_score": calculate_display_score(user),
        "intake_completed": bool(user.intake_completed),
        "safe_harbor_floor": enum_value(user.safe_harbor_floor) or SafeHarborLevel.GREEN.value,
    }
