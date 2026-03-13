"""
Document Processor
====================
Handles the full pipeline from raw document → embedded chunks in ChromaDB.

Pipeline:
    1. Extract text (PDF via pymupdf, DOCX via python-docx, plain text)
    2. Semantic chunking (split on natural boundaries, 200-500 tokens)
    3. Metadata extraction via LLM (structured facts, anonymized)
    4. Embed chunks via sentence-transformers
    5. Store in ChromaDB with metadata for filtered retrieval
    6. Discard raw text (governance: only embeddings + metadata persist)

For user documents:
    - Raw text is NEVER stored on our server
    - Only embeddings + extracted metadata + document reference persist
    - At query time, we re-fetch from Google Drive if we need the actual text

For knowledge base documents:
    - Text chunks ARE stored (we own this content)
    - No governance restriction on our own reference material
"""

import re
import io
import uuid
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.rag import embedding_service, chroma_store
from app.services.model_router import model_router, LLMMessage

logger = logging.getLogger(__name__)


# ============================================================
# TEXT EXTRACTION
# ============================================================

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract text from a PDF file."""
    try:
        import fitz  # pymupdf
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text() + "\n"
        doc.close()
        return text.strip()
    except ImportError:
        logger.warning("pymupdf not installed. Falling back to basic extraction.")
        return "[PDF extraction unavailable — install pymupdf]"


def extract_text_from_docx(docx_bytes: bytes) -> str:
    """Extract text from a Word document."""
    try:
        from docx import Document
        doc = Document(io.BytesIO(docx_bytes))
        text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
        return text.strip()
    except ImportError:
        logger.warning("python-docx not installed.")
        return "[DOCX extraction unavailable — install python-docx]"


def extract_text(file_bytes: bytes, filename: str) -> str:
    """Route to the right extractor based on file extension."""
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return extract_text_from_pdf(file_bytes)
    elif lower.endswith(".docx"):
        return extract_text_from_docx(file_bytes)
    elif lower.endswith((".txt", ".md", ".csv")):
        return file_bytes.decode("utf-8", errors="replace")
    else:
        # Try as plain text
        try:
            return file_bytes.decode("utf-8", errors="replace")
        except Exception:
            return "[Unsupported file format]"


# ============================================================
# SEMANTIC CHUNKING
# ============================================================

def chunk_text(
    text: str,
    max_chunk_tokens: int = 400,
    overlap_tokens: int = 50,
) -> list[dict]:
    """
    Split text into semantic chunks.

    Strategy:
        1. Split on double newlines (paragraph boundaries)
        2. If a paragraph is too long, split on sentences
        3. Merge small adjacent paragraphs up to max_chunk_tokens
        4. Add overlap between chunks for context continuity

    Returns:
        List of {"text": str, "index": int, "char_start": int, "char_end": int}
    """
    if not text or not text.strip():
        return []

    # Rough token estimate: 1 token ≈ 4 characters
    max_chars = max_chunk_tokens * 4
    overlap_chars = overlap_tokens * 4

    # Split on paragraph boundaries
    paragraphs = re.split(r'\n\s*\n', text)
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    chunks = []
    current_chunk = ""
    current_start = 0
    char_pos = 0

    for para in paragraphs:
        # If adding this paragraph would exceed max, finalize current chunk
        if current_chunk and len(current_chunk) + len(para) + 1 > max_chars:
            chunks.append({
                "text": current_chunk.strip(),
                "index": len(chunks),
                "char_start": current_start,
                "char_end": current_start + len(current_chunk),
            })
            # Overlap: keep the last overlap_chars of the current chunk
            if len(current_chunk) > overlap_chars:
                overlap_text = current_chunk[-overlap_chars:]
                current_chunk = overlap_text + "\n\n" + para
            else:
                current_chunk = para
            current_start = char_pos
        else:
            if current_chunk:
                current_chunk += "\n\n" + para
            else:
                current_chunk = para
                current_start = char_pos

        char_pos += len(para) + 2  # +2 for the \n\n separator

    # Don't forget the last chunk
    if current_chunk.strip():
        chunks.append({
            "text": current_chunk.strip(),
            "index": len(chunks),
            "char_start": current_start,
            "char_end": current_start + len(current_chunk),
        })

    # Handle oversized paragraphs (split on sentences)
    final_chunks = []
    for chunk in chunks:
        if len(chunk["text"]) > max_chars * 1.5:
            # Split on sentence boundaries
            sub_chunks = _split_on_sentences(chunk["text"], max_chars, overlap_chars)
            for i, sc in enumerate(sub_chunks):
                final_chunks.append({
                    "text": sc,
                    "index": len(final_chunks),
                    "char_start": chunk["char_start"],
                    "char_end": chunk["char_end"],
                })
        else:
            chunk["index"] = len(final_chunks)
            final_chunks.append(chunk)

    return final_chunks


def _split_on_sentences(text: str, max_chars: int, overlap_chars: int) -> list[str]:
    """Split text on sentence boundaries when paragraphs are too long."""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current = ""

    for sent in sentences:
        if len(current) + len(sent) + 1 > max_chars and current:
            chunks.append(current.strip())
            # Overlap
            if len(current) > overlap_chars:
                current = current[-overlap_chars:] + " " + sent
            else:
                current = sent
        else:
            current = (current + " " + sent).strip() if current else sent

    if current.strip():
        chunks.append(current.strip())

    return chunks


# ============================================================
# METADATA EXTRACTION (via LLM)
# ============================================================

METADATA_EXTRACTION_PROMPT = """You are a document analysis system. Extract structured metadata from this document.

Respond ONLY with valid JSON:
{
    "document_type": "court_legal|school_record|caseworker_report|parent_communication|medical_mental_health|therapeutic_guide|legal_reference|resource_directory|intervention_playbook|general",
    "key_dates": ["YYYY-MM-DD"],
    "key_people": [{"role": "judge|teacher|officer|guardian|therapist|counselor", "description": "brief role description"}],
    "conditions_or_requirements": ["list of conditions"],
    "risk_factors": ["list of concerns"],
    "strengths": ["list of positives"],
    "summary": "2-3 sentence summary of the document's key information",
    "tags": ["relevant", "topic", "tags"]
}

Only include fields that are present in the document. Leave arrays empty if not applicable.
"""


async def extract_metadata(
    text: str,
    db: AsyncSession,
    user_id=None,
) -> dict:
    """
    Extract structured metadata from document text using an LLM.
    Uses the utility model (free) for cost efficiency.
    """
    # Truncate to ~2000 tokens to stay within limits
    truncated = text[:8000]

    messages = [
        LLMMessage(role="system", content=METADATA_EXTRACTION_PROMPT),
        LLMMessage(role="user", content=f"Document text:\n\"\"\"\n{truncated}\n\"\"\""),
    ]

    try:
        response = await model_router.route_utility(
            messages=messages,
            db=db,
            user_id=user_id,
            max_tokens=512,
            temperature=0.1,
        )

        # Parse JSON response
        import json
        cleaned = response.content.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            cleaned = "\n".join(lines[1:-1])

        start = cleaned.find("{")
        end = cleaned.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(cleaned[start:end])

        return {"document_type": "general", "summary": "Metadata extraction incomplete", "tags": []}

    except Exception as e:
        logger.warning(f"Metadata extraction failed: {e}")
        return {"document_type": "general", "summary": f"Error: {str(e)[:100]}", "tags": []}


# ============================================================
# FULL INGESTION PIPELINE
# ============================================================

async def ingest_document(
    file_bytes: bytes,
    filename: str,
    collection_name: str,
    document_id: str,
    document_type: str,
    db: AsyncSession,
    user_id: Optional[str] = None,
    extra_metadata: Optional[dict] = None,
    store_text: bool = False,
) -> dict:
    """
    Full ingestion pipeline: extract → chunk → embed → store.

    Args:
        file_bytes: Raw file content
        filename: Original filename
        collection_name: Target ChromaDB collection
        document_id: Unique document identifier
        document_type: Classification (court_legal, school_record, etc.)
        db: Database session (for LLM calls during metadata extraction)
        user_id: Optional user ID for per-user documents
        extra_metadata: Additional metadata to attach to every chunk
        store_text: If True, store chunk text in ChromaDB (for knowledge base).
                    If False, store only embeddings + metadata (for user docs).

    Returns:
        {"chunks": int, "document_id": str, "metadata": dict}
    """
    logger.info(f"Ingesting document: {filename} → {collection_name}")

    # 1. Extract text
    text = extract_text(file_bytes, filename)
    if not text or text.startswith("["):
        return {"chunks": 0, "document_id": document_id, "error": "Text extraction failed"}

    # 2. Extract metadata
    metadata = await extract_metadata(text, db, user_id)
    if extra_metadata:
        metadata.update(extra_metadata)
    metadata["source_filename"] = filename
    metadata["document_type"] = document_type

    # 3. Chunk
    chunks = chunk_text(text)
    if not chunks:
        return {"chunks": 0, "document_id": document_id, "error": "No chunks produced"}

    # 4. Embed
    chunk_texts = [c["text"] for c in chunks]
    embeddings = embedding_service.embed_texts(chunk_texts)

    # 5. Build IDs and metadata for each chunk
    chunk_ids = [f"{document_id}_chunk_{i}" for i in range(len(chunks))]
    chunk_metadatas = []
    for i, chunk in enumerate(chunks):
        chunk_meta = {
            "document_id": document_id,
            "document_type": document_type,
            "chunk_index": i,
            "total_chunks": len(chunks),
            "source_filename": filename,
        }
        # Add document-level metadata to each chunk
        if metadata.get("tags"):
            chunk_meta["tags"] = ",".join(metadata["tags"][:5])
        if metadata.get("summary"):
            chunk_meta["summary"] = metadata["summary"][:200]
        if extra_metadata:
            for k, v in extra_metadata.items():
                if isinstance(v, (str, int, float, bool)):
                    chunk_meta[k] = v
        chunk_metadatas.append(chunk_meta)

    # 6. Store in ChromaDB
    # For user docs, store empty strings as documents (governance: no raw text)
    # For knowledge base, store actual text
    stored_texts = chunk_texts if store_text else ["" for _ in chunks]

    chroma_store.add_documents(
        collection_name=collection_name,
        ids=chunk_ids,
        texts=stored_texts,
        embeddings=embeddings,
        metadatas=chunk_metadatas,
    )

    logger.info(f"Ingested {len(chunks)} chunks from {filename} into {collection_name}")

    return {
        "chunks": len(chunks),
        "document_id": document_id,
        "metadata": metadata,
        "collection": collection_name,
    }


async def ingest_text_directly(
    text: str,
    collection_name: str,
    document_id: str,
    document_type: str,
    metadata: dict,
    store_text: bool = True,
) -> dict:
    """
    Ingest raw text directly (no file extraction needed).
    Used for knowledge base entries that are defined as text, not files.
    """
    chunks = chunk_text(text)
    if not chunks:
        return {"chunks": 0, "document_id": document_id}

    chunk_texts = [c["text"] for c in chunks]
    embeddings = embedding_service.embed_texts(chunk_texts)

    chunk_ids = [f"{document_id}_chunk_{i}" for i in range(len(chunks))]
    chunk_metadatas = []
    for i in range(len(chunks)):
        chunk_meta = {
            "document_id": document_id,
            "document_type": document_type,
            "chunk_index": i,
            "total_chunks": len(chunks),
        }
        for k, v in metadata.items():
            if isinstance(v, (str, int, float, bool)):
                chunk_meta[k] = v
        chunk_metadatas.append(chunk_meta)

    stored_texts = chunk_texts if store_text else ["" for _ in chunks]

    chroma_store.add_documents(
        collection_name=collection_name,
        ids=chunk_ids,
        texts=stored_texts,
        embeddings=embeddings,
        metadatas=chunk_metadatas,
    )

    return {"chunks": len(chunks), "document_id": document_id, "collection": collection_name}

