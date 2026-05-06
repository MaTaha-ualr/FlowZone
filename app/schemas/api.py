"""
API Schemas (Pydantic Models)
==============================
Request and response validation for all API endpoints.
Separated from SQLAlchemy models to keep DB concerns out of the API layer.

Architecture Note:
    Every endpoint has explicit request/response schemas.
    This gives us:
    1. Automatic OpenAPI docs (Swagger UI)
    2. Input validation before hitting the DB
    3. Controlled output (never accidentally leak raw_content, etc.)
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID
from enum import Enum


# ============================================================
# ENUMS (mirrored from constants for API layer)
# ============================================================

class VibeEnum(str, Enum):
    solid = "solid"
    angry = "angry"
    guarded = "guarded"
    storm = "storm"


class CharacterEnum(str, Enum):
    challenger = "challenger"
    navigator = "navigator"
    straight_shooter = "straight_shooter"
    strategist = "strategist"


class SafeHarborEnum(str, Enum):
    green = "green"
    yellow = "yellow"
    red = "red"


class RoleEnum(str, Enum):
    youth = "youth"
    mentor = "mentor"


# ============================================================
# HEALTH CHECK
# ============================================================

class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    database: str
    timestamp: datetime

    model_config = {"json_schema_extra": {
        "example": {
            "status": "healthy",
            "version": "0.1.0",
            "environment": "development",
            "database": "connected",
            "timestamp": "2025-03-13T12:00:00Z"
        }
    }}


class SystemStatusResponse(BaseModel):
    """Extended health check with subsystem status."""
    status: str
    version: str
    environment: str
    database: str
    model_router: dict  # Which models are available/reachable
    budget: dict        # Current spend vs daily cap
    active_sessions: int
    timestamp: datetime


# ============================================================
# USER SCHEMAS
# ============================================================

class UserCreate(BaseModel):
    """Create a new youth user."""
    name: str = Field(..., min_length=1, max_length=100)
    age: int = Field(..., ge=12, le=18)
    date_of_birth: Optional[datetime] = None
    school_name: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    user_type: str = Field(default="at_risk", pattern="^(juvenile_justice|at_risk)$")
    has_probation: bool = False
    has_case_worker: bool = False


class UserResponse(BaseModel):
    """User data returned by the API. Excludes sensitive fields."""
    id: UUID
    name: str
    age: int
    user_type: str
    intake_completed: bool
    current_character: CharacterEnum
    current_trust_score: float
    current_tier: str
    check_in_streak: int
    safe_harbor_floor: SafeHarborEnum
    google_drive_connected: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    users: list[UserResponse]
    total: int


# ============================================================
# AUTH / PROFILE SCHEMAS
# ============================================================

class AuthRegisterRequest(BaseModel):
    """Create an account for the wireframe login/signup flow."""
    name: str = Field(..., min_length=1, max_length=100)
    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        pattern=r"^[A-Za-z0-9_.-]+$",
    )
    password: str = Field(..., min_length=8, max_length=72)
    email: Optional[str] = Field(default=None, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=30)
    age: int = Field(..., ge=12, le=99)
    role: RoleEnum = RoleEnum.youth
    school_name: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    user_type: str = Field(default="at_risk", pattern="^(juvenile_justice|at_risk)$")
    has_probation: bool = False
    has_case_worker: bool = False


class AuthLoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1, max_length=128)


class AuthUserResponse(BaseModel):
    id: UUID
    name: str
    username: Optional[str]
    email: Optional[str] = None
    phone: Optional[str] = None
    role: RoleEnum
    current_character: CharacterEnum
    current_character_name: str
    current_tier: str
    check_in_streak: int
    current_trust_score: float
    display_score: float
    intake_completed: bool
    safe_harbor_floor: SafeHarborEnum


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthUserResponse


class UserProfileResponse(AuthUserResponse):
    age: int
    school_name: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    user_type: str
    has_probation: bool
    has_case_worker: bool
    created_at: datetime


class RainbowTierResponse(BaseModel):
    key: str
    name: str
    threshold: float
    color: str
    emoji: str
    unlocked: bool


class RainbowCircleResponse(BaseModel):
    current_tier: str
    current_tier_name: str
    current_tier_color: str
    current_tier_emoji: str
    score: float
    display_score: float
    min_score_in_tier: float
    max_score_in_tier: Optional[float]
    progress_percent: float
    total_tiers: int
    tier_index: int
    all_tiers: list[RainbowTierResponse]
    recent_deltas: list[dict]


class RewardItemResponse(BaseModel):
    key: str
    name: str
    icon: str
    cost: float
    can_afford: bool
    locked: bool


class RewardsResponse(BaseModel):
    current_score: float
    available_vouches: list[RewardItemResponse]
    redeemed_vouches: list[dict]
    can_redeem: bool
    next_unlock_tier: Optional[str] = None
    next_unlock_score: Optional[float] = None


class VibeCheckRequest(BaseModel):
    session_id: UUID
    vibe: VibeEnum
    notes: Optional[str] = Field(default=None, max_length=1000)


class VibeCheckResponse(BaseModel):
    session_id: UUID
    vibe: VibeEnum
    vibe_emoji: str
    character_assigned: CharacterEnum
    character_name: str
    message: str
    safe_harbor_level: SafeHarborEnum


# ============================================================
# INTAKE SCHEMAS
# ============================================================

class IntakeAnswers(BaseModel):
    """The 5-question Strategic Intake."""
    q1_intent: str = Field(..., pattern="^(check_box|win_freedom)$")
    q2_heat_level: int = Field(..., ge=1, le=10)
    q3_trap: str = Field(..., pattern="^(friends|temper|home|boredom|dont_know)$")
    q4_autonomy_prize: str = Field(
        ..., pattern="^(curfew|less_testing|fewer_meetings|trust_to_walk)$"
    )
    q5_collaboration: str = Field(..., pattern="^(yes|well_see)$")


class IntakeResponse(BaseModel):
    user_id: UUID
    baseline_trust_score: float
    assigned_character: CharacterEnum
    heat_level: int
    weight_multiplier: float
    message: str  # The first character message


# ============================================================
# SESSION SCHEMAS
# ============================================================

class SessionResponse(BaseModel):
    id: UUID
    user_id: UUID
    session_type: str
    character_active: CharacterEnum
    vibe_selected: Optional[VibeEnum] = None
    mask_detected: bool
    safe_harbor_level: SafeHarborEnum
    started_at: datetime
    is_active: bool
    trust_score_delta: float

    model_config = {"from_attributes": True}


# ============================================================
# CHAT / MESSAGE SCHEMAS
# ============================================================

class ChatRequest(BaseModel):
    """Send a message in a session."""
    content: str = Field(..., min_length=1, max_length=5000)
    input_type: str = Field(default="text", pattern="^(text|voice|image|document)$")
    vibe: Optional[VibeEnum] = None  # Set once per session at first message


class ChatResponse(BaseModel):
    """Response from the AI character."""
    message_id: UUID
    content: str
    character: CharacterEnum
    model_used: str
    mask_detected: bool
    safe_harbor_level: SafeHarborEnum
    trust_score_delta: float
    action_item: Optional[str] = None
    timestamp: datetime


class ChatHistoryResponse(BaseModel):
    """Conversation history for a session."""
    session_id: UUID
    messages: list[dict]  # Simplified message objects
    summary: Optional[str] = None
    total_messages: int


# ============================================================
# VOICE SCHEMAS
# ============================================================

class TranscriptionResponse(BaseModel):
    """Result of speech-to-text processing."""
    text: str
    confidence: Optional[float] = None
    duration_seconds: Optional[float] = None
    provider: str  # Which STT provider was used


class TTSRequest(BaseModel):
    """Request text-to-speech generation."""
    text: str = Field(..., min_length=1, max_length=2000)
    character: CharacterEnum  # Determines voice selection


# ============================================================
# MENTOR SCHEMAS
# ============================================================

class MentorNoteCreate(BaseModel):
    """Mentor submits an observation, vouch, or risk flag."""
    user_id: UUID
    mentor_id: str
    mentor_name: str
    note_type: str = Field(
        default="observation",
        pattern="^(observation|vouch|risk_flag|goal_update)$"
    )
    content: str = Field(..., min_length=1, max_length=5000)
    vouch_points: int = Field(default=0, ge=0, le=50)
    risk_flag_level: Optional[str] = Field(
        default=None, pattern="^(yellow|red)$"
    )


class MentorNoteResponse(BaseModel):
    id: UUID
    user_id: UUID
    mentor_name: str
    note_type: str
    sanitized_content: Optional[str]
    vouch_points: int
    risk_flag_level: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ============================================================
# TRUST SCORE SCHEMAS
# ============================================================

class TrustScoreResponse(BaseModel):
    user_id: UUID
    score_date: str
    consistency_c: int
    weight_w: float
    honesty_bonus_h: float
    regulation_bonus_r: float
    mentor_vouch_m: float
    penalty_p: float
    time_t: int
    total_score: float

    model_config = {"from_attributes": True}


# ============================================================
# BUDGET / ADMIN SCHEMAS
# ============================================================

class BudgetStatusResponse(BaseModel):
    daily_cap_usd: float
    spent_today_usd: float
    remaining_usd: float
    budget_tier: str  # "green", "yellow", "red"
    calls_today: int
    cost_by_provider: dict


# ============================================================
# DOCUMENT SCHEMAS
# ============================================================

class DocumentRefResponse(BaseModel):
    id: UUID
    filename: str
    document_type: str
    processing_status: str
    chunk_count: Optional[int] = None
    mime_type: Optional[str] = None
    extracted_metadata: Optional[dict] = None
    created_at: datetime

    model_config = {"from_attributes": True}
