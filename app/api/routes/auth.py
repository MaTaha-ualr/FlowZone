"""Username/password authentication routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Environment, settings
from app.core.constants import Character, SafeHarborLevel, TrustTier
from app.core.security import create_access_token, get_password_hash, verify_password
from app.database import get_db
from app.models.user import User
from app.schemas.api import (
    AuthLoginRequest,
    AuthRegisterRequest,
    AuthResponse,
)
from app.services.profile_projection import auth_user_payload

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


def _normalize_username(username: str) -> str:
    return username.strip().lower()


def _normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _token_for(user: User) -> str:
    return create_access_token({"sub": str(user.id), "role": user.role or "youth"})


@router.post("/register", response_model=AuthResponse, status_code=201)
async def register(
    data: AuthRegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create an account and return a bearer token for the frontend app."""
    if data.role.value == "admin" and settings.app_env != Environment.DEVELOPMENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin accounts cannot be self-registered.",
        )

    username = _normalize_username(data.username)
    email = _normalize_optional(data.email)
    phone = _normalize_optional(data.phone)

    existing_username = await db.execute(
        select(User.id).where(User.username == username).limit(1)
    )
    if existing_username.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username is already taken.",
        )

    if email:
        existing_email = await db.execute(
            select(User.id).where(User.email == email.lower()).limit(1)
        )
        if existing_email.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email is already registered.",
            )
        email = email.lower()

    try:
        password_hash = get_password_hash(data.password)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    user = User(
        name=data.name.strip(),
        age=data.age,
        school_name=_normalize_optional(data.school_name),
        city=_normalize_optional(data.city),
        state=_normalize_optional(data.state),
        username=username,
        password_hash=password_hash,
        email=email,
        phone=phone,
        role=data.role.value,
        user_type=data.user_type,
        has_probation=data.has_probation,
        has_case_worker=data.has_case_worker,
        intake_completed=True,
        intake_answers={"source": "auth_register_v0_2_1"},
        current_character=Character.NAVIGATOR,
        current_tier=TrustTier.THE_WATCH,
        safe_harbor_floor=SafeHarborLevel.GREEN,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    await db.commit()

    return AuthResponse(access_token=_token_for(user), user=auth_user_payload(user))


@router.post("/login", response_model=AuthResponse)
async def login(
    data: AuthLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate by username and password."""
    username = _normalize_username(data.username)
    result = await db.execute(select(User).where(User.username == username).limit(1))
    user = result.scalar_one_or_none()

    if (
        not user
        or not user.is_active
        or not user.password_hash
        or not verify_password(data.password, user.password_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return AuthResponse(access_token=_token_for(user), user=auth_user_payload(user))
