"""
Document Reference Model
=========================
Stores references to documents in users' Google Drive.
Contains extracted metadata and ChromaDB collection pointers.
RAW TEXT IS NEVER STORED — only embeddings + structured metadata.
"""

import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class DocumentRef(Base):
    __tablename__ = "document_refs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )

    # ---- Google Drive Reference ----
    google_drive_file_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    filename: Mapped[str] = mapped_column(String(300), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # ---- Document Classification ----
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # "court_legal", "school_record", "caseworker_report", "parent_communication", "medical_mental_health"

    # ---- Extracted Metadata (structured, anonymized) ----
    extracted_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Contains the structured fields defined in the framework document

    # ---- ChromaDB Reference ----
    chroma_collection: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Points to the user-specific collection: "user_{user_id}_documents"
    chunk_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ---- Processing Status ----
    processing_status: Mapped[str] = mapped_column(String(20), default="pending")
    # "pending", "processing", "completed", "failed"
    last_processed: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # ---- Metadata ----
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # ---- Relationships ----
    user = relationship("User", back_populates="document_refs")
