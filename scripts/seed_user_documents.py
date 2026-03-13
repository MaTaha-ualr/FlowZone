"""
Seed sample per-user documents (System 2) for development.

This script is intentionally minimal and expects that a test user (e.g.
Marcus Cole) already exists in the database and that sample documents
are accessible from the container filesystem.

Usage (inside Docker, once you have a user_id and sample files mounted):
    docker compose exec app python -m scripts.seed_user_documents
"""

import asyncio
import uuid
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.services.rag.document_processor import ingest_user_document


SAMPLE_USER_ID = None  # Fill with a UUID string for local testing, or wire via env
SAMPLE_DOC_DIR = Path("/app/sample_docs")  # Mount sample docs here if desired


async def _seed_for_user(session: AsyncSession, user_id: uuid.UUID) -> None:
    if not SAMPLE_DOC_DIR.exists():
        print(f"Sample doc dir {SAMPLE_DOC_DIR} does not exist; skipping.")
        return

    for path in SAMPLE_DOC_DIR.glob("*.pdf"):
        print(f"Ingesting {path.name} for user {user_id}...")
        data = path.read_bytes()
        await ingest_user_document(
            db=session,
            user_id=user_id,
            file_bytes=data,
            filename=path.name,
            mime_type="application/pdf",
            document_type="court_legal",
        )
    await session.commit()


async def main() -> None:
    if not SAMPLE_USER_ID:
        print("SAMPLE_USER_ID is not set; skipping user document seeding.")
        return

    async with AsyncSessionLocal() as session:
        await _seed_for_user(session, uuid.UUID(SAMPLE_USER_ID))
        print("User documents seeding completed.")


if __name__ == "__main__":
    asyncio.run(main())

