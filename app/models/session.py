"""
Session Model
==============
Represents a single FlowQuest session or interaction period.

Sessions are:
  - Continuous within a day (user can leave and come back)
  - Start fresh after SESSION_TIMEOUT_HOURS of inactivity or a new calendar day
  - Store the rolling conversation summary (for token-efficient prompting)
  - Track the active character, vibe, and Safe Harbor level
"""

import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy import Enum as SAEnum, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.core.constants import Character, Vibe, SafeHarborLevel


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )

    # ---- Session Type ----
    # "intake" (first time), "flowquest" (daily), "freeform" (open chat)
    session_type: Mapped[str] = mapped_column(String(20), default="flowquest")

    # ---- Timing ----
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # ---- Character & Vibe State ----
    character_active: Mapped[str] = mapped_column(
        SAEnum(Character, name="session_character_enum", create_constraint=False),
        nullable=False
    )
    vibe_selected: Mapped[str | None] = mapped_column(
        SAEnum(Vibe, name="session_vibe_enum", create_constraint=False),
        nullable=True
    )
    vibe_detected_by_sentiment: Mapped[str | None] = mapped_column(
        SAEnum(Vibe, name="session_vibe_detected_enum", create_constraint=False),
        nullable=True
    )
    mask_detected: Mapped[bool] = mapped_column(Boolean, default=False)

    # ---- Safe Harbor ----
    safe_harbor_level: Mapped[str] = mapped_column(
        SAEnum(SafeHarborLevel, name="session_sh_enum", create_constraint=False),
        default=SafeHarborLevel.GREEN
    )

    # ---- Conversation Summary ----
    # Rolling summary of older messages (for token-efficient context)
    # Updated every ~10 messages via a utility model call
    summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_last_updated_at_msg: Mapped[int] = mapped_column(Integer, default=0)

    # ---- Extracted Data ----
    traps_mentioned: Mapped[list | None] = mapped_column(JSON, nullable=True)
    interventions_offered: Mapped[list | None] = mapped_column(JSON, nullable=True)
    interventions_completed: Mapped[list | None] = mapped_column(JSON, nullable=True)
    honesty_disclosures: Mapped[int] = mapped_column(Integer, default=0)
    action_item: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ---- Trust Score Impact ----
    trust_score_delta: Mapped[float] = mapped_column(Float, default=0.0)

    # ---- Relationships ----
    user = relationship("User", back_populates="sessions")
    messages = relationship("Message", back_populates="session", lazy="selectin",
                            order_by="Message.created_at")

    def __repr__(self):
        return f"<Session {self.id} ({self.session_type}, {self.character_active})>"
