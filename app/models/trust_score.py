"""
Trust Score Model
==================
Daily trust score snapshot per user.
Implements the Shield Formula: Trust Score = ((C × W) + H + R + M - P) / T

One row per user per day. Recalculated after each session.
"""

import uuid
from datetime import datetime, date
from sqlalchemy import Float, Integer, Date, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class TrustScore(Base):
    __tablename__ = "trust_scores"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    score_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # ---- Shield Formula Components ----
    consistency_c: Mapped[int] = mapped_column(Integer, default=0)       # Consecutive check-in days
    weight_w: Mapped[float] = mapped_column(Float, default=1.0)         # Hard day multiplier
    honesty_bonus_h: Mapped[float] = mapped_column(Float, default=0.0)  # Proactive disclosures
    regulation_bonus_r: Mapped[float] = mapped_column(Float, default=0.0)  # Completed resets
    mentor_vouch_m: Mapped[float] = mapped_column(Float, default=0.0)   # Manual mentor points
    penalty_p: Mapped[float] = mapped_column(Float, default=0.0)        # Mask/lie deductions
    time_t: Mapped[int] = mapped_column(Integer, default=1)             # Days since first check-in

    # ---- Computed Total ----
    total_score: Mapped[float] = mapped_column(Float, default=0.0)

    # ---- Metadata ----
    calculated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # ---- Relationships ----
    user = relationship("User", back_populates="trust_scores")

    def calculate(self):
        """Apply the Shield Formula."""
        numerator = (self.consistency_c * self.weight_w) + \
                    self.honesty_bonus_h + \
                    self.regulation_bonus_r + \
                    self.mentor_vouch_m - \
                    self.penalty_p
        self.total_score = numerator / max(self.time_t, 1)  # Prevent division by zero
        return self.total_score
