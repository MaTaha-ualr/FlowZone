"""
Vouch Model
=============
The gamification economy: users spend trust credits to generate
data-backed vouches (curfew extensions, reduced monitoring, etc.)
Vouches expire in 48 hours to keep users in the investment loop.
"""

import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Float, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Vouch(Base):
    __tablename__ = "vouches"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )

    vouch_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # "curfew_extension", "social_pass", "reduced_monitoring"
    credits_spent: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active")
    # "active", "expired", "redeemed", "revoked"

    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    redeemed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
