"""
School Data Model
==================
Stores academic data pulled from school SIS APIs or entered manually.
Used by the Truth Engine for discrepancy detection.
"""

import uuid
from datetime import datetime
from sqlalchemy import String, Float, Integer, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class SchoolData(Base):
    __tablename__ = "school_data"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )

    # ---- Academic Data ----
    school_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    gpa: Mapped[float | None] = mapped_column(Float, nullable=True)
    attendance_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    tardiness_count: Mapped[int] = mapped_column(Integer, default=0)
    classes_failing: Mapped[list | None] = mapped_column(JSON, nullable=True)
    classes_excelling: Mapped[list | None] = mapped_column(JSON, nullable=True)
    disciplinary_incidents: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # ---- IEP / Special Education ----
    has_iep: Mapped[bool] = mapped_column(Boolean, default=False)
    iep_accommodations: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # ---- Athletic Eligibility ----
    athletic_eligible: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # ---- Source ----
    source: Mapped[str] = mapped_column(String(20), default="manual")  # "manual" | "api"
    academic_period: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # ---- Sync Metadata ----
    last_synced: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
