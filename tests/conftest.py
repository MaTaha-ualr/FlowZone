"""
Test Fixtures
===============
Async SQLite database (no Postgres needed), FastAPI test client,
mocked LLM providers, and sample data factories.
"""

import pytest
import asyncio
from datetime import datetime, date, timezone
from uuid import uuid4
from unittest.mock import AsyncMock, patch

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from httpx import AsyncClient, ASGITransport

from app.database import Base, get_db
from app.main import app
from app.models import (
    User, Session, Message, TrustScore, MentorNote,
    SchoolData, DocumentRef, ApiUsage, Vouch, Pattern,
)
from app.core.constants import Character, Vibe, SafeHarborLevel, TrustTier
from app.services.model_router.base_provider import LLMResponse


# ============================================================
# DATABASE
# ============================================================

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine):
    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def client(db_engine):
    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# ============================================================
# MOCKS — prevent real LLM API calls in tests
# ============================================================

@pytest.fixture
def mock_model_router():
    mock_response = LLMResponse(
        content="Test response from mock router.",
        model="mock-model", provider="mock",
        tokens_in=50, tokens_out=30,
        finish_reason="stop", response_time_ms=100,
    )
    with patch("app.api.routes.chat.model_router") as mock:
        mock.route = AsyncMock(return_value=mock_response)
        mock.route_analytical = AsyncMock(return_value=mock_response)
        mock.route_utility = AsyncMock(return_value=mock_response)
        yield mock


@pytest.fixture
def mock_mask_detection():
    with patch("app.api.routes.chat.detect_mask") as mock:
        mock.return_value = {
            "detected_vibe": "solid", "confidence": 0.3,
            "mask_detected": False, "reasoning": "no mask in test",
            "sentiment_score": 0.1, "key_indicators": [],
        }
        yield mock


@pytest.fixture
def mock_extract_session_data():
    with patch("app.api.routes.chat.extract_session_data") as mock:
        mock.return_value = {
            "traps": ["peer_pressure"], "moves": ["attended_school"],
            "goals": ["get_grades_up"], "emotional_state": "tired",
            "urgency_level": "low", "topics": ["school"],
        }
        yield mock


@pytest.fixture
def mock_trust_calculator():
    with patch("app.api.routes.chat.recalculate_after_session") as mock:
        mock.return_value = {
            "previous_score": 95.0, "new_score": 99.8, "delta": 4.8,
            "components": {}, "tier_change": False,
            "old_tier": TrustTier.THE_WATCH, "new_tier": TrustTier.THE_WATCH,
        }
        yield mock


# ============================================================
# DATA FACTORIES
# ============================================================

@pytest.fixture
async def sample_user(db_session):
    user = User(
        id=uuid4(), name="Marcus Cole", age=15,
        date_of_birth=datetime(2010, 6, 14),
        school_name="Westwood High School",
        city="Memphis", state="Tennessee",
        user_type="juvenile_justice", has_probation=True,
        intake_completed=False,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def completed_intake_user(db_session):
    user = User(
        id=uuid4(), name="Aaliyah Jenkins", age=16,
        user_type="juvenile_justice", has_probation=True,
        intake_completed=True,
        intake_answers={
            "q1_intent": "check_box", "q2_heat_level": 9,
            "q3_trap": "temper", "q4_autonomy_prize": "fewer_meetings",
            "q5_collaboration": "well_see",
        },
        baseline_trust_score=95.0, current_trust_score=95.0,
        heat_level=9, weight_multiplier=1.5,
        current_character=Character.CHALLENGER,
        current_tier=TrustTier.THE_WATCH,
        check_in_streak=3,
        last_check_in=datetime.now(timezone.utc),
        safe_harbor_floor=SafeHarborLevel.YELLOW,
        has_trauma_history=True,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def sample_session(db_session, completed_intake_user):
    session = Session(
        id=uuid4(), user_id=completed_intake_user.id,
        session_type="flowquest",
        character_active=Character.CHALLENGER,
        safe_harbor_level=SafeHarborLevel.YELLOW,
        is_active=True,
    )
    db_session.add(session)
    await db_session.flush()
    await db_session.refresh(session)
    return session
