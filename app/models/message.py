"""
Message Model
==============
Every single message exchanged in every session.
Tracks which model generated it (for credit accounting)
and what input modality was used.
"""

import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False, index=True
    )

    # ---- Content ----
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    # "user", "assistant", "system" (for context injections logged for debugging)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # ---- Input Modality ----
    input_type: Mapped[str] = mapped_column(String(20), default="text")
    # "text", "voice", "image", "document"

    # ---- Model Tracking (for credit management) ----
    model_provider: Mapped[str | None] = mapped_column(String(30), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    response_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ---- Metadata ----
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # ---- Relationships ----
    session = relationship("Session", back_populates="messages")

    def __repr__(self):
        preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"<Message {self.role}: {preview}>"
