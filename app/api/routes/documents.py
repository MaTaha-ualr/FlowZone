"""
Document & RAG Routes (FIXED)
================================
Changes:
  - Auth required
  - Users can only access their own documents
"""

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.document_ref import DocumentRef
from app.schemas.api import DocumentRefResponse
from app.services.rag.document_processor import ingest_user_document
from app.services.rag import chroma_store
from app.services.rag.embedding_service import embed_text
from app.services.rag.retriever import _search_knowledge_base
from app.services.rag.google_drive import (
    get_oauth_authorization_url,
    exchange_code_for_tokens,
    GoogleDriveNotConfigured,
)
from app.core.config import settings
from app.core.constants import Character
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1", tags=["Documents", "RAG"])

ALLOWED_DOCUMENT_EXTENSIONS = {".pdf", ".txt", ".doc", ".docx", ".png", ".jpg", ".jpeg", ".webp"}


async def _read_validated_upload(file: UploadFile) -> bytes:
    filename = file.filename or "document"
    ext = Path(filename).suffix.lower()
    mime_type = (file.content_type or "").split(";", 1)[0].strip().lower()

    if ext not in ALLOWED_DOCUMENT_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported document extension.",
        )
    if mime_type and mime_type not in settings.document_allowed_mime_types_set:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported document MIME type.",
        )

    contents = await file.read(settings.document_max_upload_bytes + 1)
    if not contents:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(contents) > settings.document_max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Document file too large (max {settings.document_max_upload_bytes // (1024 * 1024)}MB).",
        )
    return contents

@router.post("/documents/upload", response_model=DocumentRefResponse, status_code=201)
async def upload_document(
    user_id: uuid.UUID = Query(...),
    document_type: str = Query(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Upload a document. Users can only upload for themselves."""
    if str(user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")

    contents = await _read_validated_upload(file)

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
        raise HTTPException(status_code=500, detail="Document reference not found")
    await db.commit()
    return doc

@router.get("/documents/{user_id}", response_model=list[DocumentRefResponse])
async def list_user_documents(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """List documents. Users can only view their own."""
    if str(user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")

    result = await db.execute(
        select(DocumentRef)
        .where(DocumentRef.user_id == user_id)
        .order_by(DocumentRef.created_at.desc())
    )
    return result.scalars().all()

@router.post("/documents/google-drive/connect")
async def google_drive_connect(
    current_user = Depends(get_current_user),
):
    """Start Google Drive OAuth."""
    try:
        url = get_oauth_authorization_url(state="flowzone_state")
        return {"authorization_url": url}
    except GoogleDriveNotConfigured as e:
        raise HTTPException(status_code=501, detail=str(e))

@router.get("/documents/google-drive/callback")
async def google_drive_callback(code: str):
    """OAuth callback."""
    try:
        tokens = exchange_code_for_tokens(code)
        return {"status": "ok", "tokens_stored": bool(tokens)}
    except GoogleDriveNotConfigured as e:
        raise HTTPException(status_code=501, detail=str(e))

@router.post("/documents/google-drive/sync")
async def google_drive_sync():
    """Placeholder."""
    raise HTTPException(status_code=501, detail="Google Drive sync not fully implemented")

@router.get("/rag/stats")
async def rag_stats(
    current_user = Depends(get_current_user),
):
    """RAG stats."""
    collections = chroma_store.list_collections()
    return {"collections": collections}

@router.get("/rag/search")
async def rag_search(
    q: str,
    topic: str = Query("therapeutic"),
    character: str = Query("challenger"),
    current_user = Depends(get_current_user),
):
    """Direct RAG search for testing."""
    try:
        char_enum = Character(character)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown character: {character}")

    query_embedding = embed_text(q)
    metadata_filter = {"topic": topic} if topic else None
    texts = _search_knowledge_base(
        query_embedding=query_embedding,
        character=char_enum,
        metadata_filter=metadata_filter,
    )
    return {
        "query": q,
        "topic": topic,
        "results": [{"text": t, "metadata": {}} for t in texts],
    }
