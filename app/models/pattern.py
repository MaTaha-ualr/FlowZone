"""
Pattern Library Model
======================
RAG System 3: Anonymized cross-user patterns.
Stores what interventions worked for which user profiles.
NO identifying information — just structured pattern data.
"""

import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Float, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Pattern(Base):
    __tablename__ = "pattern_library"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # ---- Anonymized Profile ----
    trap_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    user_profile: Mapped[dict] = mapped_column(JSON, nullable=False)
    # {"heat_level": "high", "vibe": "guarded", "character": "challenger", "user_type": "juvenile_justice"}

    # ---- Intervention & Outcome ----
    intervention_used: Mapped[str] = mapped_column(String(100), nullable=False)
    outcome: Mapped[str] = mapped_column(String(20), nullable=False)
    # "positive", "neutral", "negative"
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    # 0.0-1.0 — starts low, increases with more matching data points

    # ---- Context Tags ----
    context_tags: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # ["evening", "weekend", "first_month", "post_violation"]

    # ---- Source ----
    source: Mapped[str] = mapped_column(String(20), default="observed")
    # "observed" (from real sessions) or "literature" (pre-seeded from clinical research)

    # ---- Metadata ----
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    observation_count: Mapped[int] = mapped_column(default=1)
    # How many times this pattern has been observed
