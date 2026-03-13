"""
Document & RAG Utility Routes
===============================

Endpoints:
    POST /api/v1/documents/upload             — Upload and ingest a document
    GET  /api/v1/documents/{user_id}          — List user's documents
    POST /api/v1/documents/google-drive/connect   — Start OAuth flow
    GET  /api/v1/documents/google-drive/callback  — OAuth callback
    POST /api/v1/documents/google-drive/sync      — Sync documents from Drive
    GET  /api/v1/rag/stats                    — Collection statistics (MVP: stub)
    GET  /api/v1/rag/search                   — Direct RAG search (for testing)
"""

import uuid
from typing import Any, Dict

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.document_ref import DocumentRef
from app.schemas.api import DocumentRefResponse
from app.services.rag.document_processor import ingest_user_document
from app.services.rag import chroma_store
from app.services.rag.embedding_service import embed_text
from app.services.rag.retriever import _search_knowledge_base  # internal helper
from app.services.rag.google_drive import (
    get_oauth_authorization_url,
    exchange_code_for_tokens,
    GoogleDriveNotConfigured,
)
from app.core.constants import Character


router = APIRouter(prefix="/api/v1", tags=["Documents", "RAG"])


@router.post("/documents/upload", response_model=DocumentRefResponse, status_code=201)
async def upload_document(
    user_id: uuid.UUID = Query(...),
    document_type: str = Query(..., description="High-level type, e.g. court_legal, school_record"),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload a document for a user and run the ingestion pipeline."""
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Empty file")

    result = await ingest_user_document(
        db=db,
        user_id=user_id,
        file_bytes=contents,
        filename=file.filename or "document",
        mime_type=file.content_type,
        document_type=document_type,
    )
    await db.flush()

    doc = await db.get(DocumentRef, uuid.UUID(result["document_id"]))
    if not doc:
        raise HTTPException(status_code=500, detail="Document reference not found after ingest")

    return doc


@router.get("/documents/{user_id}", response_model=list[DocumentRefResponse])
async def list_user_documents(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """List a user's document references and processing status."""
    result = await db.execute(
        select(DocumentRef)
        .where(DocumentRef.user_id == user_id)
        .order_by(DocumentRef.created_at.desc())
    )
    return result.scalars().all()


@router.post("/documents/google-drive/connect")
async def google_drive_connect():
    """
    Start the Google Drive OAuth flow.
    For MVP this returns a placeholder URL if Drive is not fully configured.
    """
    try:
        url = get_oauth_authorization_url(state="flowzone_state")
        return {"authorization_url": url}
    except GoogleDriveNotConfigured as e:
        raise HTTPException(status_code=501, detail=str(e))


@router.get("/documents/google-drive/callback")
async def google_drive_callback(code: str):
    """
    OAuth callback endpoint.
    In production, this would persist refresh tokens linked to the user.
    """
    try:
        tokens = exchange_code_for_tokens(code)
        # In a real implementation, associate tokens with the authenticated user.
        return {"status": "ok", "tokens_stored": bool(tokens)}
    except GoogleDriveNotConfigured as e:
        raise HTTPException(status_code=501, detail=str(e))


@router.post("/documents/google-drive/sync")
async def google_drive_sync():
    """
    Placeholder for syncing selected Drive documents.
    Implementation depends on how mentor/user auth is wired.
    """
    raise HTTPException(
        status_code=501,
        detail="Google Drive sync is not fully implemented in this environment.",
    )


@router.get("/rag/stats")
async def rag_stats():
    """
    Basic RAG stats.
    For now, returns the names of known collections; deeper stats can be added later.
    """
    collections = chroma_store.list_collections()
    return {"collections": collections}


@router.get("/rag/search")
async def rag_search(
    q: str,
    topic: str = Query("therapeutic"),
    character: str = Query("challenger"),
):
    """
    Direct RAG search primarily for development/testing.
    Searches the global KB collections using the shared retriever logic.
    """
    try:
        char_enum = Character(character)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown character: {character}")

    # Embed the query and use the internal knowledge-base search helper
    query_embedding = embed_text(q)

    # Optionally use topic as a metadata filter hint
    metadata_filter = {"topic": topic} if topic else None
    texts = _search_knowledge_base(
        query_embedding=query_embedding,
        character=char_enum,
        metadata_filter=metadata_filter,
    )

    return {
        "query": q,
        "topic": topic,
        "results": [
            {
                "text": t,
                "metadata": {},
            }
            for t in texts
        ],
    }

