"""
FlowZone Security — JWT Authentication & Demo Mode
=====================================================
Provides:
  - JWT token creation/validation
  - get_current_user dependency (for protected routes)
  - Demo mode bypass for pilot testing

Dependencies already in requirements.txt:
  python-jose[cryptography], passlib[bcrypt]
"""

import uuid
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Union

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.database import get_db
from app.models.user import User

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Config
# ------------------------------------------------------------------
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30  # Youth apps: long-lived tokens (device stays logged in)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)  # auto_error=False lets demo mode work

# ------------------------------------------------------------------
# Password helpers (for mentor auth later)
# ------------------------------------------------------------------
def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def get_password_hash(plain: str) -> str:
    return pwd_context.hash(plain)

# ------------------------------------------------------------------
# JWT helpers
# ------------------------------------------------------------------
def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    )
    to_encode.update({"exp": expire})
    encoded = jwt.encode(to_encode, settings.app_secret_key, algorithm=ALGORITHM)
    return encoded

def decode_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT. Returns payload or None."""
    try:
        payload = jwt.decode(token, settings.app_secret_key, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        logger.debug(f"JWT decode failed: {e}")
        return None

# ------------------------------------------------------------------
# User resolution
# ------------------------------------------------------------------
async def _get_user_from_token(
    token: str,
    db: AsyncSession,
) -> Optional[User]:
    """Resolve a JWT to a User object."""
    payload = decode_token(token)
    if not payload:
        return None
    user_id_str = payload.get("sub")
    if not user_id_str:
        return None
    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        return None
    return await db.get(User, user_id)

async def _get_demo_user(
    request: Request,
    db: AsyncSession,
) -> Optional[User]:
    """
    DEMO MODE: if APP_DEMO_MODE=true, accept X-User-ID header
    and resolve it directly (NO password, NO token).
    """
    if not settings.app_demo_mode:
        return None
    user_id_str = request.headers.get("X-User-ID")
    if not user_id_str:
        return None
    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        return None
    user = await db.get(User, user_id)
    if user:
        logger.debug(f"Demo mode: resolved user {user.name} from X-User-ID header")
    return user

# ------------------------------------------------------------------
# FastAPI Dependencies
# ------------------------------------------------------------------
async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Dependency for protected routes.

    Priority:
      1. Bearer token in Authorization header
      2. Demo mode: X-User-ID header (if APP_DEMO_MODE=true)
      3. Reject
    """
    # 1. Try JWT
    if credentials and credentials.credentials:
        user = await _get_user_from_token(credentials.credentials, db)
        if user and user.is_active:
            return user

    # 2. Try demo mode
    user = await _get_demo_user(request, db)
    if user and user.is_active:
        return user

    # 3. Reject
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing authentication. Provide a Bearer token or enable demo mode.",
        headers={"WWW-Authenticate": "Bearer"},
    )

async def get_current_user_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """
    Optional auth — returns user if available, None otherwise.
    Useful for public health checks or mixed endpoints.
    """
    if credentials and credentials.credentials:
        user = await _get_user_from_token(credentials.credentials, db)
        if user and user.is_active:
            return user
    user = await _get_demo_user(request, db)
    if user and user.is_active:
        return user
    return None

async def require_admin(
    user: User = Depends(get_current_user),
) -> User:
    """
    Placeholder for admin authorization.
    In production, check user.role == 'admin' or similar.
    """
    # For now, any authenticated user can access admin endpoints in demo
    # TODO: add role-based checks when User model has roles
    return user
