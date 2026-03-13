"""
User Model
===========
Represents a youth user in the FlowZone system.

Stores:
  - Profile basics (name, age, type)
  - Intake answers and computed baseline score
  - Current character assignment (can change dynamically)
  - Google Drive OAuth tokens (encrypted in production)
  - Safe Harbor floor level
"""

import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Float, Boolean, DateTime, Enum as SAEnum, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.core.constants import Character, SafeHarborLevel, TrustTier


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # ---- Profile ----
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    date_of_birth: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    school_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # ---- User Type ----
    # "juvenile_justice" or "at_risk"
    user_type: Mapped[str] = mapped_column(String(30), nullable=False, default="at_risk")
    has_probation: Mapped[bool] = mapped_column(Boolean, default=False)
    has_case_worker: Mapped[bool] = mapped_column(Boolean, default=False)

    # ---- Intake Data ----
    intake_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    intake_answers: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Stores: {q1: "check_box"|"win_freedom", q2: 1-10, q3: "friends"|..., q4: "...", q5: "yes"|"well_see"}

    baseline_trust_score: Mapped[float] = mapped_column(Float, default=0.0)
    heat_level: Mapped[int] = mapped_column(Integer, default=5)  # From Q2: 1-10
    weight_multiplier: Mapped[float] = mapped_column(Float, default=1.0)

    # ---- Character Assignment ----
    current_character: Mapped[str] = mapped_column(
        SAEnum(Character, name="character_enum", create_constraint=False),
        default=Character.NAVIGATOR  # Safe default until intake
    )

    # ---- Trust & Gamification ----
    current_trust_score: Mapped[float] = mapped_column(Float, default=0.0)
    current_tier: Mapped[str] = mapped_column(
        SAEnum(TrustTier, name="trust_tier_enum", create_constraint=False),
        default=TrustTier.THE_WATCH
    )
    check_in_streak: Mapped[int] = mapped_column(Integer, default=0)
    last_check_in: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # ---- Safe Harbor ----
    safe_harbor_floor: Mapped[str] = mapped_column(
        SAEnum(SafeHarborLevel, name="safe_harbor_enum", create_constraint=False),
        default=SafeHarborLevel.GREEN
    )
    has_trauma_history: Mapped[bool] = mapped_column(Boolean, default=False)
    has_crisis_history: Mapped[bool] = mapped_column(Boolean, default=False)

    # ---- Google Drive OAuth ----
    google_refresh_token: Mapped[str | None] = mapped_column(String(500), nullable=True)
    google_drive_connected: Mapped[bool] = mapped_column(Boolean, default=False)

    # ---- Metadata ----
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # ---- Relationships ----
    sessions = relationship("Session", back_populates="user", lazy="selectin")
    trust_scores = relationship("TrustScore", back_populates="user", lazy="selectin")
    mentor_notes = relationship("MentorNote", back_populates="user", lazy="selectin")
    document_refs = relationship("DocumentRef", back_populates="user", lazy="selectin")

    def __repr__(self):
        return f"<User {self.name} ({self.user_type}, {self.current_character})>"
