"""
Mentor Note Model
==================
Stores mentor observations, vouch awards, and risk flags.
Raw content is sanitized by AI before characters see it.

Row Level Security Note:
    Youth-facing queries must ONLY access sanitized_content.
    Raw content is for mentor dashboard and admin only.
    RLS policies in Postgres enforce this at the DB level.
"""

import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class MentorNote(Base):
    __tablename__ = "mentor_notes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    mentor_id: Mapped[str] = mapped_column(String(100), nullable=False)
    mentor_name: Mapped[str] = mapped_column(String(100), nullable=False)

    # ---- Content (dual storage for RLS) ----
    raw_content: Mapped[str] = mapped_column(Text, nullable=False)
    sanitized_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_sanitized: Mapped[bool] = mapped_column(Boolean, default=False)

    # ---- Type ----
    note_type: Mapped[str] = mapped_column(String(30), default="observation")
    # "observation", "vouch", "risk_flag", "goal_update"

    vouch_points: Mapped[int] = mapped_column(Integer, default=0)
    risk_flag_level: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # ---- Metadata ----
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # ---- Relationships ----
    user = relationship("User", back_populates="mentor_notes")
